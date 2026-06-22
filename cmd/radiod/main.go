// Command radiod is the brain of Golden Shower Radio: it acquires music via
// slskd (with a yt-dlp fallback), curates it with an LLM program-director,
// indexes it, and feeds a continuous queue to Liquidsoap (which streams to
// Icecast). It also serves the public station website on :8080.
//
// Design rule: continuous operation is the identity. No subsystem failure
// (slskd down, LLM error, telnet hiccup) is allowed to crash the daemon — every
// loop is guarded and every external call tolerates failure.
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/golden-shower-radio/station/internal/acquire"
	"github.com/golden-shower-radio/station/internal/config"
	"github.com/golden-shower-radio/station/internal/director"
	"github.com/golden-shower-radio/station/internal/library"
	"github.com/golden-shower-radio/station/internal/slskd"
	"github.com/golden-shower-radio/station/internal/state"
	"github.com/golden-shower-radio/station/internal/store"
	"github.com/golden-shower-radio/station/internal/web"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	slog.SetDefault(logger)

	cfg := config.Load()
	startedAt := time.Now().UTC().Format(time.RFC3339)
	st := state.New(cfg.StationName, startedAt)
	st.SetBrainMode(cfg.BrainMode())
	st.SetState("running")

	banner(cfg)

	// Persistence (JSON file store under DB_DIR). Non-fatal if it cannot init.
	stStore, err := store.New(cfg.DBDir)
	if err != nil {
		slog.Error("store init failed; persistence disabled", "err", err)
		stStore, _ = store.New(os.TempDir()) // best-effort fallback
	}

	// Library: load existing index, then scan MUSIC_DIR.
	lib := library.New(cfg.MusicDir, stStore)
	lib.Load()
	st.SetLibraryCount(lib.Count())

	// Subsystem clients.
	slskdClient := slskd.New(cfg.SlskdURL, cfg.SlskdAPIKey)

	// Acquisition: bounded worker pool consuming a query channel.
	queries := make(chan acquire.Query, 64)
	acq := acquire.New(slskdClient, lib, st, stStore, cfg.MusicDir)

	// Director: the creative brain producing the wishlist.
	dir := director.New(cfg.AnthropicKey, cfg.AnthropicModel, lib, st, acq, queries)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// Initial library scan (foreground-ish, but in a goroutine so HTTP comes up fast).
	go func() {
		defer guard("initial-scan")
		lib.Scan(ctx)
		st.SetLibraryCount(lib.Count())
	}()

	// Start the subsystems. Each runs in its own guarded goroutine.
	// Playout is now HTTP PULL: Liquidsoap polls GET /api/next (served by the
	// web server below) for the next track. There is no telnet-push scheduler.
	go runGuarded(ctx, "acquire", func(c context.Context) { acq.Run(c, queries) })
	go runGuarded(ctx, "director", dir.Run)

	// Web + status + playout PULL server on :8080.
	srv := web.NewHTTPServer(web.New(st, lib), ":8080")
	go func() {
		defer guard("http-server")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("http server failed", "err", err)
		}
	}()
	slog.Info("station server listening", "addr", ":8080")

	<-ctx.Done()
	slog.Info("shutdown signal received")
	shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutCtx)
	slog.Info("radiod stopped")
}

// runGuarded runs fn(ctx) and recovers from any panic so a single subsystem
// failure never takes down the daemon.
func runGuarded(ctx context.Context, name string, fn func(context.Context)) {
	defer guard(name)
	fn(ctx)
}

func guard(name string) {
	if r := recover(); r != nil {
		slog.Error("subsystem panic recovered", "subsystem", name, "panic", r)
	}
}

func banner(cfg config.Config) {
	slog.Info("==================================================")
	slog.Info("  GOLDEN SHOWER RADIO — autonomous station online")
	slog.Info("==================================================")
	slog.Info("radiod starting",
		"station", cfg.StationName,
		"slskd", cfg.SlskdURL,
		"liquidsoap", cfg.LiquidsoapHost+":"+cfg.LiquidsoapPort,
		"music_dir", cfg.MusicDir,
		"db_dir", cfg.DBDir,
		"brain_mode", cfg.BrainMode(),
	)
}
