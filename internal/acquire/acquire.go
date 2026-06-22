// Package acquire turns "Artist - Title" wishlist entries into local audio
// files. It runs a bounded pool of workers that:
//
//  1. search slskd, pick the best file passing the quality predicate, download it;
//  2. if slskd yields no acceptable result or the download fails/stalls, fall
//     back to yt-dlp (extract best-quality mp3 via ffmpeg);
//  3. rescan / register the new file into the library;
//  4. record the per-track outcome in attempts.json so failed tracks are not
//     re-hammered every cycle.
//
// Nothing here panics: every external call (slskd, yt-dlp, ffprobe) is wrapped
// and its failure is logged and recorded as an attempt outcome.
package acquire

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/golden-shower-radio/station/internal/library"
	"github.com/golden-shower-radio/station/internal/slskd"
	"github.com/golden-shower-radio/station/internal/state"
	"github.com/golden-shower-radio/station/internal/store"
)

const (
	attemptsFile   = "attempts.json"
	maxConcurrent  = 3 // gentle: <= 3 concurrent downloads
	downloadWindow = 90 * time.Second
	ytdlpTimeout   = 120 * time.Second
)

// Query is one acquisition request.
type Query struct {
	Artist string
	Title  string
}

// Display renders the query as "Artist - Title".
func (q Query) Display() string {
	a, t := strings.TrimSpace(q.Artist), strings.TrimSpace(q.Title)
	if a != "" && t != "" {
		return a + " - " + t
	}
	if t != "" {
		return t
	}
	return a
}

func (q Query) searchText() string {
	return strings.TrimSpace(q.Artist + " " + q.Title)
}

// attempt records the outcome of trying to acquire a track.
type attempt struct {
	Query   string    `json:"query"`
	Outcome string    `json:"outcome"` // slskd-ok | ytdlp-ok | failed
	At      time.Time `json:"at"`
}

// Acquirer is the worker-pool acquisition engine.
type Acquirer struct {
	slskd    *slskd.Client
	lib      *library.Library
	st       *state.State
	store    *store.Store
	musicDir string

	sem chan struct{}

	mu       sync.Mutex
	attempts map[string]attempt
}

// New constructs an Acquirer. musicDir is where downloaded files land
// (slskd writes to /downloads which shares the /music volume).
func New(sc *slskd.Client, lib *library.Library, st *state.State, store *store.Store, musicDir string) *Acquirer {
	a := &Acquirer{
		slskd:    sc,
		lib:      lib,
		st:       st,
		store:    store,
		musicDir: musicDir,
		sem:      make(chan struct{}, maxConcurrent),
		attempts: make(map[string]attempt),
	}
	a.loadAttempts()
	return a
}

// Attempted reports whether this track was already tried (any outcome). The
// director uses this to avoid re-queuing tracks it has already chased.
func (a *Acquirer) Attempted(q Query) bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	_, ok := a.attempts[normQuery(q)]
	return ok
}

// Run consumes queries until ctx is cancelled, dispatching each to a bounded
// worker goroutine.
//
// @MX:WARN: [AUTO] Spawns one goroutine per query, bounded by a semaphore (maxConcurrent).
// @MX:REASON: unbounded fan-out would hammer slskd peers and yt-dlp; the sem cap and recover guard are load-bearing for resilience.
func (a *Acquirer) Run(ctx context.Context, queries <-chan Query) {
	var wg sync.WaitGroup
	for {
		select {
		case <-ctx.Done():
			wg.Wait()
			return
		case q, ok := <-queries:
			if !ok {
				wg.Wait()
				return
			}
			select {
			case a.sem <- struct{}{}:
			case <-ctx.Done():
				wg.Wait()
				return
			}
			wg.Add(1)
			go func(q Query) {
				defer wg.Done()
				defer func() { <-a.sem }()
				defer func() {
					if r := recover(); r != nil {
						slog.Error("acquire: worker panic recovered", "query", q.Display(), "panic", r)
					}
				}()
				a.handle(ctx, q)
			}(q)
		}
	}
}

// handle acquires a single track, slskd-first then yt-dlp fallback.
func (a *Acquirer) handle(ctx context.Context, q Query) {
	disp := q.Display()
	if disp == "" {
		return
	}
	if a.lib.Contains(q.Artist, q.Title) {
		return
	}
	a.st.AddDownloading(disp)
	defer a.st.RemoveDownloading(disp)

	if a.trySlskd(ctx, q) {
		a.record(q, "slskd-ok")
		slog.Info("acquire: slskd success", "track", disp)
		return
	}

	slog.Info("acquire: slskd miss, trying yt-dlp", "track", disp)
	if a.tryYtdlp(ctx, q) {
		a.record(q, "ytdlp-ok")
		slog.Info("acquire: yt-dlp success", "track", disp)
		return
	}

	a.record(q, "failed")
	slog.Warn("acquire: all sources failed", "track", disp)
}

// trySlskd searches slskd, downloads the best acceptable candidate, and waits
// (bounded) for the transfer to complete. Returns true if a file landed.
func (a *Acquirer) trySlskd(ctx context.Context, q Query) bool {
	sctx, cancel := context.WithTimeout(ctx, 40*time.Second)
	defer cancel()

	cand, ok, err := a.slskd.SearchAndPick(sctx, q.searchText())
	if err != nil {
		slog.Warn("acquire: slskd search failed", "track", q.Display(), "err", err)
		return false
	}
	if !ok {
		return false
	}
	before := a.lib.Count()
	if err := a.slskd.Download(sctx, cand.Username, []slskd.File{cand.File}); err != nil {
		slog.Warn("acquire: slskd download request failed", "track", q.Display(), "user", cand.Username, "err", err)
		return false
	}

	// Poll for the file to appear in MUSIC_DIR (slskd writes asynchronously).
	deadline := time.Now().Add(downloadWindow)
	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return false
		case <-time.After(3 * time.Second):
		}
		a.lib.Scan(ctx)
		if a.lib.Count() > before || a.lib.Contains(q.Artist, q.Title) {
			return true
		}
		// Stall detection: if slskd reports the transfer errored/cancelled, bail early.
		if a.transferDead(sctx, cand.Username) {
			slog.Info("acquire: slskd transfer reported dead", "track", q.Display())
			return false
		}
	}
	return a.lib.Contains(q.Artist, q.Title)
}

// transferDead returns true if every transfer for the user is in a terminal
// failed/cancelled state (so we can fall back without waiting the full window).
func (a *Acquirer) transferDead(ctx context.Context, username string) bool {
	ts, err := a.slskd.DownloadStatus(ctx, username)
	if err != nil || len(ts) == 0 {
		return false
	}
	for _, t := range ts {
		low := strings.ToLower(t.State)
		if !strings.Contains(low, "errored") && !strings.Contains(low, "cancelled") &&
			!strings.Contains(low, "failed") && !strings.Contains(low, "rejected") {
			return false // at least one still alive
		}
	}
	return true
}

// tryYtdlp downloads via yt-dlp (best-quality mp3) and registers the result.
//
// @MX:WARN: [AUTO] Executes the external yt-dlp binary with a network search.
// @MX:REASON: external process + network I/O; a hang or crash here must never take down the daemon — bounded by ytdlpTimeout and recover in Run.
func (a *Acquirer) tryYtdlp(ctx context.Context, q Query) bool {
	if _, err := exec.LookPath("yt-dlp"); err != nil {
		slog.Warn("acquire: yt-dlp not installed, skipping fallback", "track", q.Display())
		return false
	}
	yctx, cancel := context.WithTimeout(ctx, ytdlpTimeout)
	defer cancel()

	query := sanitizeSearch(q.searchText())
	if query == "" {
		return false
	}
	outTmpl := filepath.Join(a.musicDir, "%(title)s.%(ext)s")
	args := []string{
		"-x", "--audio-format", "mp3", "--audio-quality", "0",
		"--no-playlist", "--no-progress",
		"-o", outTmpl,
		"ytsearch1:" + query + " audio",
	}
	cmd := exec.CommandContext(yctx, "yt-dlp", args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		slog.Warn("acquire: yt-dlp failed", "track", q.Display(), "err", err, "out", tail(out))
		return false
	}

	// Locate the freshest mp3 in MUSIC_DIR as the produced file.
	if path := a.newestMP3(yctx); path != "" {
		a.lib.Add(yctx, path, "yt-dlp")
		return true
	}
	// Fall back to a full rescan in case the file was placed in a subdir.
	a.lib.Scan(yctx)
	return a.lib.Contains(q.Artist, q.Title)
}

// newestMP3 returns the most recently modified .mp3 directly under musicDir.
func (a *Acquirer) newestMP3(ctx context.Context) string {
	entries, err := os.ReadDir(a.musicDir)
	if err != nil {
		return ""
	}
	var newest string
	var newestMod time.Time
	cutoff := time.Now().Add(-ytdlpTimeout - time.Minute)
	for _, e := range entries {
		if e.IsDir() || strings.ToLower(filepath.Ext(e.Name())) != ".mp3" {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			continue
		}
		if newest == "" || info.ModTime().After(newestMod) {
			newest = filepath.Join(a.musicDir, e.Name())
			newestMod = info.ModTime()
		}
	}
	return newest
}

// --- attempts persistence ----------------------------------------------------

func (a *Acquirer) loadAttempts() {
	var list []attempt
	if err := a.store.Load(attemptsFile, &list); err != nil {
		if !os.IsNotExist(err) {
			slog.Warn("acquire: load attempts failed", "err", err)
		}
		return
	}
	for _, at := range list {
		a.attempts[strings.ToLower(at.Query)] = at
	}
	slog.Info("acquire: loaded attempts", "count", len(a.attempts))
}

func (a *Acquirer) record(q Query, outcome string) {
	a.mu.Lock()
	a.attempts[normQuery(q)] = attempt{Query: q.Display(), Outcome: outcome, At: time.Now().UTC()}
	list := make([]attempt, 0, len(a.attempts))
	for _, at := range a.attempts {
		list = append(list, at)
	}
	a.mu.Unlock()
	if err := a.store.Save(attemptsFile, list); err != nil {
		slog.Warn("acquire: persist attempts failed", "err", err)
	}
}

func normQuery(q Query) string { return strings.ToLower(q.Display()) }

// sanitizeSearch strips characters that would confuse the yt-dlp search string.
func sanitizeSearch(s string) string {
	repl := strings.NewReplacer("\"", " ", "'", " ", "\n", " ", "\t", " ", ":", " ")
	s = repl.Replace(s)
	return strings.Join(strings.Fields(s), " ")
}

func tail(b []byte) string {
	s := strings.TrimSpace(string(b))
	if len(s) > 300 {
		s = s[len(s)-300:]
	}
	return fmt.Sprintf("...%s", s)
}
