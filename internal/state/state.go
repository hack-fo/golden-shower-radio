// Package state holds the live, in-memory station state shared between the
// scheduler (what is playing), the acquisition workers (what is downloading),
// the director (brain mode) and the web server (which renders it).
//
// It is the single source of truth that the web layer reads via Snapshot().
// Keeping it in its own leaf package avoids import cycles: every subsystem may
// depend on state, but state depends on nothing.
package state

import "sync"

const recentCap = 15

// Snapshot is an immutable, JSON-serializable view of the station at a moment.
// The web server returns this directly from /status and /api/nowplaying.
type Snapshot struct {
	Station       string   `json:"station"`
	State         string   `json:"state"`
	BrainMode     string   `json:"brain_mode"`
	NowPlaying    string   `json:"now_playing"`
	QueueDepth    int      `json:"queue_depth"`
	LibraryTracks int      `json:"library_tracks"`
	Recent        []string `json:"recent"`
	Downloading   []string `json:"downloading"`
	StartedAt     string   `json:"started_at"`
}

// State is the concurrency-safe station state. The zero value is not usable;
// construct with New.
type State struct {
	mu sync.RWMutex

	station     string
	startedAt   string
	state       string
	brainMode   string
	nowPlaying  string
	queueDepth  int
	libraryN    int
	recent      []string
	downloading map[string]struct{}
}

// New returns an initialized State.
func New(station, startedAt string) *State {
	return &State{
		station:     station,
		startedAt:   startedAt,
		state:       "starting",
		brainMode:   "unknown",
		recent:      make([]string, 0, recentCap),
		downloading: make(map[string]struct{}),
	}
}

// SetState records a high-level lifecycle label (starting/running/etc.).
func (s *State) SetState(v string) { s.set(func() { s.state = v }) }

// SetBrainMode records whether the LLM director or the seed fallback is active.
func (s *State) SetBrainMode(v string) { s.set(func() { s.brainMode = v }) }

// SetQueueDepth records the current Liquidsoap queue length.
func (s *State) SetQueueDepth(n int) { s.set(func() { s.queueDepth = n }) }

// SetLibraryCount records the number of indexed tracks.
func (s *State) SetLibraryCount(n int) { s.set(func() { s.libraryN = n }) }

// SetNowPlaying records the currently playing track and pushes the previous
// track onto the recent ring buffer.
func (s *State) SetNowPlaying(v string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.nowPlaying != "" && s.nowPlaying != v {
		s.pushRecentLocked(s.nowPlaying)
	}
	s.nowPlaying = v
}

func (s *State) pushRecentLocked(v string) {
	s.recent = append(s.recent, v)
	if len(s.recent) > recentCap {
		s.recent = s.recent[len(s.recent)-recentCap:]
	}
}

// AddDownloading marks a track ("Artist - Title") as actively downloading.
func (s *State) AddDownloading(v string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.downloading[v] = struct{}{}
}

// RemoveDownloading clears the downloading flag for a track.
func (s *State) RemoveDownloading(v string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.downloading, v)
}

// Snapshot returns a deep copy of the current state for safe serialization.
//
// @MX:ANCHOR: [AUTO] Read path for the entire web surface (/status, /api/nowplaying, banner).
// @MX:REASON: fan_in >= 3 (web handlers + status loop); returned slices must be copies to avoid data races with writers.
func (s *State) Snapshot() Snapshot {
	s.mu.RLock()
	defer s.mu.RUnlock()
	recent := make([]string, len(s.recent))
	copy(recent, s.recent)
	// Present most-recent first for display.
	for i, j := 0, len(recent)-1; i < j; i, j = i+1, j-1 {
		recent[i], recent[j] = recent[j], recent[i]
	}
	dl := make([]string, 0, len(s.downloading))
	for k := range s.downloading {
		dl = append(dl, k)
	}
	return Snapshot{
		Station:       s.station,
		State:         s.state,
		BrainMode:     s.brainMode,
		NowPlaying:    s.nowPlaying,
		QueueDepth:    s.queueDepth,
		LibraryTracks: s.libraryN,
		Recent:        recent,
		Downloading:   dl,
		StartedAt:     s.startedAt,
	}
}

func (s *State) set(fn func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	fn()
}
