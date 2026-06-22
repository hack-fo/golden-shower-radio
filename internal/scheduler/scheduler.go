// Package scheduler keeps audio flowing: it watches the Liquidsoap queue depth
// and tops it up from the library whenever it drops below a threshold, avoiding
// recently played/queued tracks. It also publishes "now playing" and queue
// depth into the shared station state for the web UI.
package scheduler

import (
	"context"
	"log/slog"
	"time"

	"github.com/golden-shower-radio/station/internal/library"
	"github.com/golden-shower-radio/station/internal/playout"
	"github.com/golden-shower-radio/station/internal/state"
)

const (
	queueLowMark = 3 // top up when fewer than this many requests are pending
	queueTarget  = 5 // fill up to this many
	tick         = 10 * time.Second
	recentWindow = 12 // avoid replaying the last N queued tracks
)

// Scheduler drives the playout queue from the library.
type Scheduler struct {
	lib    *library.Library
	play   *playout.Client
	st     *state.State
	recent []string
}

// New constructs a Scheduler.
func New(lib *library.Library, play *playout.Client, st *state.State) *Scheduler {
	return &Scheduler{lib: lib, play: play, st: st}
}

// Run loops until ctx is cancelled, keeping the queue topped up.
//
// @MX:WARN: [AUTO] Long-lived goroutine that is the sole writer of now-playing/queue state.
// @MX:REASON: this loop is the heartbeat that makes audio flow; a panic must never kill it, hence the recover guard and error-tolerant playout calls.
func (s *Scheduler) Run(ctx context.Context) {
	t := time.NewTicker(tick)
	defer t.Stop()
	s.fill(ctx) // prime immediately
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			func() {
				defer func() {
					if r := recover(); r != nil {
						slog.Error("scheduler: tick panic recovered", "panic", r)
					}
				}()
				s.fill(ctx)
			}()
		}
	}
}

func (s *Scheduler) fill(ctx context.Context) {
	depth := s.play.QueueLen()
	s.st.SetQueueDepth(depth)
	s.st.SetLibraryCount(s.lib.Count())

	if depth >= queueLowMark {
		return
	}
	avoid := make(map[string]bool, len(s.recent))
	for _, r := range s.recent {
		avoid[r] = true
	}
	for depth < queueTarget {
		if ctx.Err() != nil {
			return
		}
		track, ok := s.lib.PickEligible(avoid)
		if !ok {
			slog.Debug("scheduler: library empty, nothing to enqueue")
			return
		}
		if err := s.play.Push(track.Path); err != nil {
			slog.Warn("scheduler: push failed", "path", track.Path, "err", err)
			return // Liquidsoap likely down; try again next tick
		}
		disp := track.Display()
		s.st.SetNowPlaying(disp) // best-effort; reflects most recently queued
		s.pushRecent(disp)
		avoid[disp] = true
		depth++
		slog.Info("scheduler: enqueued", "track", disp, "queue_depth", depth)
	}
	s.st.SetQueueDepth(depth)
}

func (s *Scheduler) pushRecent(disp string) {
	s.recent = append(s.recent, disp)
	if len(s.recent) > recentWindow {
		s.recent = s.recent[len(s.recent)-recentWindow:]
	}
}
