// Package library indexes the on-disk music collection under MUSIC_DIR.
//
// It walks the directory tree for audio files, extracts artist/title/album tags
// via ffprobe (falling back to "Artist - Title" filename parsing), deduplicates
// by normalized artist+title, and persists a JSON index at DB_DIR/library.json.
//
// The index is the menu the scheduler plays from. All methods are safe for
// concurrent use; nothing here panics — a malformed file is simply skipped.
package library

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/golden-shower-radio/station/internal/store"
)

const indexFile = "library.json"

var audioExts = map[string]bool{
	".mp3": true, ".flac": true, ".m4a": true, ".ogg": true,
	".opus": true, ".wav": true, ".aac": true, ".aiff": true,
}

// Track is one indexed audio file.
type Track struct {
	Path       string    `json:"path"`
	Artist     string    `json:"artist"`
	Title      string    `json:"title"`
	Album      string    `json:"album"`
	Source     string    `json:"source"` // "slskd", "yt-dlp", "scan"
	AddedAt    time.Time `json:"addedAt"`
	LastPlayed time.Time `json:"lastPlayed,omitempty"`
}

func (t Track) key() string { return normKey(t.Artist, t.Title) }

// Display renders a track as "Artist - Title".
func (t Track) Display() string {
	a, ti := strings.TrimSpace(t.Artist), strings.TrimSpace(t.Title)
	switch {
	case a != "" && ti != "":
		return a + " - " + ti
	case ti != "":
		return ti
	default:
		return filepath.Base(t.Path)
	}
}

// Library is the in-memory, persisted music index.
type Library struct {
	dir   string
	store *store.Store

	mu     sync.RWMutex
	byKey  map[string]*Track
	byPath map[string]*Track
}

// New creates a Library rooted at musicDir, persisting to st.
func New(musicDir string, st *store.Store) *Library {
	return &Library{
		dir:    musicDir,
		store:  st,
		byKey:  make(map[string]*Track),
		byPath: make(map[string]*Track),
	}
}

// Load reads any persisted index from disk. Missing/corrupt index is non-fatal.
func (l *Library) Load() {
	var tracks []Track
	if err := l.store.Load(indexFile, &tracks); err != nil {
		if !os.IsNotExist(err) {
			slog.Warn("library: load index failed, starting empty", "err", err)
		}
		return
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	for i := range tracks {
		t := tracks[i]
		if _, err := os.Stat(t.Path); err != nil {
			continue // file gone since last run
		}
		l.insertLocked(&t)
	}
	slog.Info("library: loaded index", "tracks", len(l.byKey))
}

// Scan walks MUSIC_DIR and indexes any new audio files, then persists.
// It is safe to call repeatedly (e.g. after downloads complete).
func (l *Library) Scan(ctx context.Context) {
	added := 0
	_ = filepath.WalkDir(l.dir, func(p string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // skip unreadable entries, keep walking
		}
		if ctx.Err() != nil {
			return ctx.Err()
		}
		if d.IsDir() || !audioExts[strings.ToLower(filepath.Ext(p))] {
			return nil
		}
		l.mu.RLock()
		_, known := l.byPath[p]
		l.mu.RUnlock()
		if known {
			return nil
		}
		t := l.indexFileTrack(ctx, p)
		l.mu.Lock()
		if l.insertLocked(t) {
			added++
		}
		l.mu.Unlock()
		return nil
	})
	if added > 0 {
		l.persist()
	}
	slog.Info("library: scan complete", "added", added, "total", l.Count())
}

// indexFileTrack builds a Track for path p using ffprobe with filename fallback.
func (l *Library) indexFileTrack(ctx context.Context, p string) *Track {
	artist, title, album := probeTags(ctx, p)
	if artist == "" && title == "" {
		artist, title = parseFilename(p)
	}
	if title == "" {
		title = strings.TrimSuffix(filepath.Base(p), filepath.Ext(p))
	}
	return &Track{
		Path:    p,
		Artist:  artist,
		Title:   title,
		Album:   album,
		Source:  "scan",
		AddedAt: time.Now().UTC(),
	}
}

// insertLocked adds t if its normalized key is new. Caller holds l.mu.
func (l *Library) insertLocked(t *Track) bool {
	if _, ok := l.byPath[t.Path]; ok {
		return false
	}
	k := t.key()
	if _, ok := l.byKey[k]; ok {
		// Duplicate artist+title; still track the path so we don't re-probe it.
		l.byPath[t.Path] = t
		return false
	}
	l.byKey[k] = t
	l.byPath[t.Path] = t
	return true
}

// Add inserts a track discovered out-of-band (e.g. a fresh yt-dlp download) and
// persists. source records provenance ("yt-dlp", "slskd").
func (l *Library) Add(ctx context.Context, path, source string) {
	artist, title, album := probeTags(ctx, path)
	if artist == "" && title == "" {
		artist, title = parseFilename(path)
	}
	if title == "" {
		title = strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
	}
	t := &Track{
		Path: path, Artist: artist, Title: title, Album: album,
		Source: source, AddedAt: time.Now().UTC(),
	}
	l.mu.Lock()
	changed := l.insertLocked(t)
	l.mu.Unlock()
	if changed {
		l.persist()
	}
}

// Contains reports whether a track with this artist+title is already indexed.
//
// @MX:ANCHOR: [AUTO] Dedup gate consulted by the director before queuing acquisitions.
// @MX:REASON: fan_in >= 3 (director, acquire, scheduler); normalization here defines the station-wide identity of a track.
func (l *Library) Contains(artist, title string) bool {
	l.mu.RLock()
	defer l.mu.RUnlock()
	_, ok := l.byKey[normKey(artist, title)]
	return ok
}

// Count returns the number of unique indexed tracks.
func (l *Library) Count() int {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return len(l.byKey)
}

// List returns a snapshot copy of all indexed tracks.
func (l *Library) List() []Track {
	l.mu.RLock()
	defer l.mu.RUnlock()
	out := make([]Track, 0, len(l.byKey))
	for _, t := range l.byKey {
		out = append(out, *t)
	}
	return out
}

// PickEligible chooses the least-recently-played track, preferring tracks not
// in the avoid set (recently queued display strings). Returns ok=false if the
// library is empty.
func (l *Library) PickEligible(avoid map[string]bool) (Track, bool) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if len(l.byKey) == 0 {
		return Track{}, false
	}
	var chosen *Track
	for _, t := range l.byKey {
		if avoid[t.Display()] {
			continue
		}
		if chosen == nil || t.LastPlayed.Before(chosen.LastPlayed) {
			chosen = t
		}
	}
	if chosen == nil {
		// Everything is in the avoid set; fall back to least-recently-played overall.
		for _, t := range l.byKey {
			if chosen == nil || t.LastPlayed.Before(chosen.LastPlayed) {
				chosen = t
			}
		}
	}
	if chosen == nil {
		return Track{}, false
	}
	chosen.LastPlayed = time.Now().UTC()
	return *chosen, true
}

func (l *Library) persist() {
	tracks := l.List()
	if err := l.store.Save(indexFile, tracks); err != nil {
		slog.Warn("library: persist failed", "err", err)
	}
}

// --- tag extraction ----------------------------------------------------------

// probeTags runs ffprobe to read artist/title/album. Returns empties on any
// failure (ffprobe missing, unreadable file, no tags) so callers can fall back.
func probeTags(ctx context.Context, p string) (artist, title, album string) {
	pctx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(pctx, "ffprobe", "-v", "quiet",
		"-print_format", "json", "-show_format", "-show_streams", p)
	out, err := cmd.Output()
	if err != nil {
		return "", "", ""
	}
	var probe struct {
		Format struct {
			Tags map[string]string `json:"tags"`
		} `json:"format"`
		Streams []struct {
			Tags map[string]string `json:"tags"`
		} `json:"streams"`
	}
	if err := json.Unmarshal(out, &probe); err != nil {
		return "", "", ""
	}
	tag := func(tags map[string]string, keys ...string) string {
		for k, v := range tags {
			lk := strings.ToLower(k)
			for _, want := range keys {
				if lk == want {
					return strings.TrimSpace(v)
				}
			}
		}
		return ""
	}
	artist = tag(probe.Format.Tags, "artist", "album_artist", "albumartist")
	title = tag(probe.Format.Tags, "title")
	album = tag(probe.Format.Tags, "album")
	for _, s := range probe.Streams {
		if artist == "" {
			artist = tag(s.Tags, "artist", "album_artist")
		}
		if title == "" {
			title = tag(s.Tags, "title")
		}
		if album == "" {
			album = tag(s.Tags, "album")
		}
	}
	return artist, title, album
}

// parseFilename extracts "Artist - Title" from a file's base name.
func parseFilename(p string) (artist, title string) {
	base := strings.TrimSuffix(filepath.Base(p), filepath.Ext(p))
	// Strip common leading track numbers like "01 - " or "01. ".
	base = strings.TrimSpace(base)
	if i := strings.Index(base, " - "); i > 0 {
		artist = strings.TrimSpace(base[:i])
		title = strings.TrimSpace(base[i+3:])
		// Drop a numeric-only "artist" that is really a track number.
		if isAllDigits(artist) {
			artist, title = "", strings.TrimSpace(base[i+3:])
		}
		return artist, title
	}
	return "", base
}

func isAllDigits(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

// normKey produces the dedup key for an artist+title pair.
func normKey(artist, title string) string {
	return normalize(artist) + "\x00" + normalize(title)
}

func normalize(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	var b strings.Builder
	prevSpace := false
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= '0' && r <= '9':
			b.WriteRune(r)
			prevSpace = false
		case r == ' ' || r == '_' || r == '-':
			if !prevSpace {
				b.WriteRune(' ')
				prevSpace = true
			}
		default:
			// drop punctuation / accents-as-bytes
		}
	}
	return strings.TrimSpace(b.String())
}
