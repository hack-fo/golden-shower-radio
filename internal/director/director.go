// Package director is the creative brain of the station. On an interval (and
// whenever the library is running low) it produces a rolling wishlist of
// concrete "Artist - Title" tracks and feeds them to the acquisition workers.
//
// With an Anthropic API key it asks Claude (a tasteful, eclectic late-night
// curator with full creative freedom) for fresh picks. Without a key it falls
// back to a built-in diverse seed list so the station still acquires and plays.
//
// The director never crashes the daemon: LLM/network failures fall back to the
// seed list and are logged.
package director

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"math/rand"
	"net/http"
	"strings"
	"time"

	"github.com/golden-shower-radio/station/internal/acquire"
	"github.com/golden-shower-radio/station/internal/library"
	"github.com/golden-shower-radio/station/internal/state"
)

const (
	cycle          = 5 * time.Minute
	lowLibraryMark = 20 // proactively curate while the library is small
	batchSize      = 15
	apiURL         = "https://api.anthropic.com/v1/messages"
	apiVersion     = "2023-06-01"
)

const persona = `You are the program director of an autonomous late-night internet radio station.
You have COMPLETE creative freedom over what to play. You are a tasteful, human, eclectic
curator with deep crate-digging knowledge spanning rock, soul, funk, electronic, hip-hop,
reggae, dub, jazz, afrobeat, post-punk, ambient, and pop. You are NOT a corporate or
engagement-chasing entity. There are no ads, no algorithms to please, no charts to chase —
only great music chosen with care for a curious listener in the small hours.`

// Acquirer is the subset of the acquisition engine the director needs.
type Acquirer interface {
	Attempted(q acquire.Query) bool
}

// Director generates the wishlist.
type Director struct {
	apiKey   string
	model    string
	lib      *library.Library
	st       *state.State
	acq      Acquirer
	queries  chan<- acquire.Query
	http     *http.Client
	rng      *rand.Rand
	seedFrom int
}

// New constructs a Director. apiKey may be empty (seed-only mode). queries is
// the channel consumed by the acquisition workers.
func New(apiKey, model string, lib *library.Library, st *state.State, acq Acquirer, queries chan<- acquire.Query) *Director {
	return &Director{
		apiKey:  apiKey,
		model:   model,
		lib:     lib,
		st:      st,
		acq:     acq,
		queries: queries,
		http:    &http.Client{Timeout: 60 * time.Second},
		rng:     rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// Run loops until ctx is cancelled, curating on each cycle and immediately when
// the library is low.
//
// @MX:WARN: [AUTO] Long-lived goroutine performing network LLM calls each cycle.
// @MX:REASON: LLM/network failure must degrade to the seed list, never panic; recover guard plus seed fallback keep the station autonomous.
func (d *Director) Run(ctx context.Context) {
	t := time.NewTicker(cycle)
	defer t.Stop()
	d.curate(ctx) // curate immediately on boot
	for {
		// Fast path: if the library is low, curate sooner.
		wait := cycle
		if d.lib.Count() < lowLibraryMark {
			wait = 45 * time.Second
		}
		st := time.NewTimer(wait)
		select {
		case <-ctx.Done():
			st.Stop()
			return
		case <-st.C:
		case <-t.C:
			st.Stop()
		}
		func() {
			defer func() {
				if r := recover(); r != nil {
					slog.Error("director: curate panic recovered", "panic", r)
				}
			}()
			d.curate(ctx)
		}()
	}
}

func (d *Director) curate(ctx context.Context) {
	var picks []acquire.Query
	mode := "seed"
	if d.apiKey != "" {
		llmPicks, err := d.askClaude(ctx)
		if err != nil {
			slog.Warn("director: LLM curation failed, using seed list", "err", err)
		} else if len(llmPicks) > 0 {
			picks = llmPicks
			mode = "llm:" + d.model
		}
	}
	if len(picks) == 0 {
		picks = d.seedBatch()
	}
	d.st.SetBrainMode(mode)

	queued := 0
	for _, q := range picks {
		if q.Title == "" {
			continue
		}
		if d.lib.Contains(q.Artist, q.Title) || d.acq.Attempted(q) {
			continue
		}
		select {
		case d.queries <- q:
			queued++
		case <-ctx.Done():
			return
		default:
			// Acquisition channel full; stop pushing this cycle.
			slog.Debug("director: acquisition channel full, deferring", "remaining", len(picks)-queued)
			return
		}
	}
	slog.Info("director: curation cycle", "mode", mode, "candidates", len(picks), "queued", queued, "library", d.lib.Count())
}

// --- Anthropic Messages API --------------------------------------------------

func (d *Director) askClaude(ctx context.Context) ([]acquire.Query, error) {
	recent := d.recentSample(40)
	userPrompt := fmt.Sprintf(`Give me %d concrete tracks to spin next on the station, spanning
genres and eras you find interesting right now. Avoid obvious overplayed radio staples and
avoid anything in this already-played/owned list:
%s

Return ONLY a JSON array, no prose, in exactly this shape:
[{"artist":"...","title":"..."}, ...]`, batchSize, strings.Join(recent, "\n"))

	reqBody := map[string]any{
		"model":      d.model,
		"max_tokens": 1024,
		"system":     persona,
		"messages": []map[string]string{
			{"role": "user", "content": userPrompt},
		},
	}
	b, _ := json.Marshal(reqBody)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, apiURL, bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	req.Header.Set("x-api-key", d.apiKey)
	req.Header.Set("anthropic-version", apiVersion)
	req.Header.Set("content-type", "application/json")

	resp, err := d.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("director: anthropic request: %w", err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("director: anthropic status %d: %s", resp.StatusCode, truncate(string(data), 200))
	}
	var out struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	if err := json.Unmarshal(data, &out); err != nil {
		return nil, fmt.Errorf("director: decode anthropic response: %w", err)
	}
	var text strings.Builder
	for _, c := range out.Content {
		if c.Type == "text" {
			text.WriteString(c.Text)
		}
	}
	return parsePicks(text.String()), nil
}

// parsePicks robustly extracts a JSON array of {artist,title} from arbitrary
// model text (which may wrap the JSON in prose or code fences).
func parsePicks(text string) []acquire.Query {
	start := strings.Index(text, "[")
	end := strings.LastIndex(text, "]")
	if start < 0 || end <= start {
		return nil
	}
	var raw []struct {
		Artist string `json:"artist"`
		Title  string `json:"title"`
	}
	if err := json.Unmarshal([]byte(text[start:end+1]), &raw); err != nil {
		return nil
	}
	out := make([]acquire.Query, 0, len(raw))
	for _, r := range raw {
		t := strings.TrimSpace(r.Title)
		if t == "" {
			continue
		}
		out = append(out, acquire.Query{Artist: strings.TrimSpace(r.Artist), Title: t})
	}
	return out
}

func (d *Director) recentSample(n int) []string {
	tracks := d.lib.List()
	out := make([]string, 0, n)
	for _, t := range tracks {
		out = append(out, t.Display())
		if len(out) >= n {
			break
		}
	}
	return out
}

// --- seed fallback -----------------------------------------------------------

// seedBatch returns the next rotating slice of the built-in seed list, shuffled
// so successive cycles vary.
func (d *Director) seedBatch() []acquire.Query {
	picks := make([]acquire.Query, 0, batchSize)
	d.rng.Shuffle(len(seedTracks), func(i, j int) {
		seedTracks[i], seedTracks[j] = seedTracks[j], seedTracks[i]
	})
	for _, q := range seedTracks {
		picks = append(picks, q)
		if len(picks) >= batchSize {
			break
		}
	}
	return picks
}

func truncate(s string, n int) string {
	if len(s) > n {
		return s[:n]
	}
	return s
}
