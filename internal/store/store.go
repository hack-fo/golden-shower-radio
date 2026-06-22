// Package store provides a tiny, dependency-free JSON file persistence layer.
//
// It is deliberately minimal: the station persists small index/state files
// (library.json, attempts.json) under DB_DIR. There is no external database —
// per the build constraints we use the stdlib only and CGO is disabled.
//
// Writes are atomic (write to a temp file in the same directory, then rename)
// so a crash mid-write can never corrupt an existing file.
package store

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

// Store is a directory-scoped JSON file store. Methods are safe for concurrent
// use across goroutines.
//
// @MX:ANCHOR: [AUTO] Single persistence primitive for all subsystems (library, director).
// @MX:REASON: fan_in >= 3 (library, director, scheduler) rely on atomic JSON read/write here; corruption would break startup recovery.
type Store struct {
	dir string
	mu  sync.Mutex
}

// New returns a Store rooted at dir, creating the directory if needed.
// A failure to create the directory is returned but is non-fatal to callers:
// the daemon must keep running even if persistence is unavailable.
func New(dir string) (*Store, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("store: mkdir %q: %w", dir, err)
	}
	return &Store{dir: dir}, nil
}

// Dir returns the store root directory.
func (s *Store) Dir() string { return s.dir }

// Load reads name (relative to the store dir) and unmarshals it into v.
// If the file does not exist, it returns os.ErrNotExist (callers treat this as
// "empty, start fresh"). Decode errors are returned so callers can decide to
// reset rather than crash.
func (s *Store) Load(name string, v any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, err := os.ReadFile(filepath.Join(s.dir, name))
	if err != nil {
		return err
	}
	if len(b) == 0 {
		return nil
	}
	if err := json.Unmarshal(b, v); err != nil {
		return fmt.Errorf("store: decode %q: %w", name, err)
	}
	return nil
}

// Save marshals v and atomically writes it to name (relative to the store dir).
func (s *Store) Save(name string, v any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("store: encode %q: %w", name, err)
	}
	tmp, err := os.CreateTemp(s.dir, "."+name+".tmp-*")
	if err != nil {
		return fmt.Errorf("store: temp %q: %w", name, err)
	}
	tmpName := tmp.Name()
	if _, err := tmp.Write(b); err != nil {
		_ = tmp.Close()
		_ = os.Remove(tmpName)
		return fmt.Errorf("store: write %q: %w", name, err)
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpName)
		return fmt.Errorf("store: close %q: %w", name, err)
	}
	if err := os.Rename(tmpName, filepath.Join(s.dir, name)); err != nil {
		_ = os.Remove(tmpName)
		return fmt.Errorf("store: rename %q: %w", name, err)
	}
	return nil
}
