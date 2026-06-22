// Package web serves the public station website and JSON status endpoints on
// :8080. The index page is held in a swappable, mutex-guarded string so it can
// be regenerated and atomically replaced at runtime (the self-redesign stretch
// goal). A solid static page is shipped by default.
package web

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/golden-shower-radio/station/internal/library"
	"github.com/golden-shower-radio/station/internal/state"
)

// recentWindow is how many recently served tracks to avoid replaying when
// selecting the next track for Liquidsoap.
const recentWindow = 12

// Server renders the station UI and exposes status/nowplaying APIs. It also
// serves the playout PULL endpoint (GET /api/next) that Liquidsoap polls for
// the next track to stream.
type Server struct {
	st  *state.State
	lib *library.Library

	mu    sync.RWMutex
	index string

	// nextMu serializes /api/next so concurrent polls cannot double-advance or
	// race the recent-avoid window. It also guards recent.
	nextMu sync.Mutex
	recent []string // display strings of recently served tracks (avoid set)
}

// New constructs a Server backed by the shared station state and music library.
// The library is the menu /api/next selects from.
func New(st *state.State, lib *library.Library) *Server {
	return &Server{st: st, lib: lib, index: defaultIndex}
}

// SetIndexHTML atomically replaces the served index page. This is the seam the
// runtime self-redesign feature will use; for now the default page is shipped.
func (s *Server) SetIndexHTML(html string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.index = html
}

// Handler returns the configured HTTP mux.
//
// @MX:ANCHOR: [AUTO] Public HTTP surface for the station (UI + status + nowplaying).
// @MX:REASON: fan_in >= 3 routes share the Server; the state.Snapshot read path here must stay race-free and never block the audio path.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})

	mux.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		s.writeJSON(w, s.st.Snapshot())
	})

	mux.HandleFunc("/api/next", s.handleNext)

	mux.HandleFunc("/api/nowplaying", func(w http.ResponseWriter, r *http.Request) {
		snap := s.st.Snapshot()
		s.writeJSON(w, map[string]any{
			"now_playing": snap.NowPlaying,
			"recent":      snap.Recent,
			"downloading": snap.Downloading,
			"queue_depth": snap.QueueDepth,
			"library":     snap.LibraryTracks,
		})
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		s.mu.RLock()
		page := s.index
		s.mu.RUnlock()
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte(page))
	})

	return mux
}

// handleNext serves the next track to Liquidsoap's HTTP PULL playout.
//
// It selects the least-recently-played eligible track (avoiding the last few
// served tracks), commits the choice into station state (now-playing + recent),
// and returns the track's absolute container path as text/plain. Liquidsoap
// mounts the same files at MUSIC_DIR (/music), so Track.Path is returned
// verbatim. An empty library yields HTTP 200 with an empty body, which
// Liquidsoap treats as "nothing yet" and retries.
//
// @MX:ANCHOR: [AUTO] Sole playout source — Liquidsoap polls this once per track to advance the stream.
// @MX:REASON: this is the heartbeat that makes audio flow; it must respond fast (<1s), never block on acquisition, and must select-and-commit atomically so successive polls advance.
func (s *Server) handleNext(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")

	// Serialize selection so concurrent polls cannot double-advance the avoid
	// window. PickEligible itself is library-locked; this guard keeps the
	// recent slice and the now-playing commit consistent per request.
	s.nextMu.Lock()
	defer s.nextMu.Unlock()

	avoid := make(map[string]bool, len(s.recent))
	for _, d := range s.recent {
		avoid[d] = true
	}

	track, ok := s.lib.PickEligible(avoid)
	if !ok {
		// Empty library: 200 with empty body. Liquidsoap retries.
		w.WriteHeader(http.StatusOK)
		return
	}

	disp := track.Display()
	s.st.SetNowPlaying(disp)
	s.st.SetLibraryCount(s.lib.Count())
	s.pushRecent(disp)

	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(track.Path))
}

// pushRecent appends a served track to the avoid window, capping its length.
// Caller holds s.nextMu.
func (s *Server) pushRecent(disp string) {
	s.recent = append(s.recent, disp)
	if len(s.recent) > recentWindow {
		s.recent = s.recent[len(s.recent)-recentWindow:]
	}
}

func (s *Server) writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_ = json.NewEncoder(w).Encode(v)
}

// NewHTTPServer wraps the handler in a configured *http.Server.
func NewHTTPServer(s *Server, addr string) *http.Server {
	return &http.Server{
		Addr:              addr,
		Handler:           s.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
	}
}
