// Package playout controls Liquidsoap over its telnet interface.
//
// Liquidsoap exposes a line-oriented server: each command is newline-terminated
// and the reply is terminated by a line containing exactly "END". We use a
// fresh connection per command (cheap at our cadence) with a short mutex to
// serialize access, and reconnect automatically on any failure.
package playout

import (
	"bufio"
	"fmt"
	"log/slog"
	"net"
	"strings"
	"sync"
	"time"
)

// Client controls a single Liquidsoap instance.
type Client struct {
	addr string
	mu   sync.Mutex
}

// New constructs a Client targeting host:port.
func New(host, port string) *Client {
	return &Client{addr: net.JoinHostPort(host, port)}
}

// command dials, sends cmd, reads until the "END" terminator, and returns the
// reply lines (excluding the terminator).
func (c *Client) command(cmd string) ([]string, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	conn, err := net.DialTimeout("tcp", c.addr, 5*time.Second)
	if err != nil {
		return nil, fmt.Errorf("playout: dial %s: %w", c.addr, err)
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(8 * time.Second))

	if _, err := fmt.Fprintf(conn, "%s\n", cmd); err != nil {
		return nil, fmt.Errorf("playout: write %q: %w", cmd, err)
	}

	var lines []string
	sc := bufio.NewScanner(conn)
	sc.Buffer(make([]byte, 0, 64*1024), 1<<20)
	for sc.Scan() {
		line := strings.TrimRight(sc.Text(), "\r")
		if line == "END" {
			break
		}
		lines = append(lines, line)
	}
	if err := sc.Err(); err != nil {
		return lines, fmt.Errorf("playout: read %q: %w", cmd, err)
	}
	return lines, nil
}

// Push enqueues a track path (e.g. "/music/foo.mp3") into the Liquidsoap queue.
func (c *Client) Push(path string) error {
	// Liquidsoap accepts the raw path after queue.push. Paths with spaces are
	// handled by Liquidsoap's request resolver; we pass the path verbatim.
	lines, err := c.command("queue.push " + path)
	if err != nil {
		return err
	}
	slog.Debug("playout: pushed", "path", path, "reply", strings.Join(lines, " "))
	return nil
}

// QueueLen returns the number of requests currently waiting in the queue.
// Liquidsoap's "queue.queue" returns the pending request ids separated by
// whitespace; we count the tokens. On error it returns 0 so the queue filler
// errs toward topping up rather than starving the stream.
func (c *Client) QueueLen() int {
	lines, err := c.command("queue.queue")
	if err != nil {
		slog.Warn("playout: queue length query failed", "err", err)
		return 0
	}
	count := 0
	for _, l := range lines {
		for _, tok := range strings.Fields(l) {
			if tok != "" {
				count++
			}
		}
	}
	return count
}
