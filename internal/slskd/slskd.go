// Package slskd is a defensive REST client for slskd (Soulseek daemon).
//
// All requests go to <baseURL>/api/v0/... with the X-API-Key header. slskd's
// JSON response shapes vary across versions, so every struct uses pointers /
// flexible types and tolerates missing fields. Nothing in this package panics:
// callers (the acquisition workers) treat every error as "skip and move on".
package slskd

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"path"
	"strings"
	"time"
)

// MinLossyKbps is the hard bitrate floor for lossy formats. Files below this
// are never downloaded. Lossless formats are exempt (see acceptable).
const MinLossyKbps = 192

// Client talks to a single slskd instance.
type Client struct {
	baseURL string
	apiKey  string
	http    *http.Client
}

// New constructs a Client. baseURL is e.g. "http://slskd:5030".
func New(baseURL, apiKey string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		apiKey:  apiKey,
		http:    &http.Client{Timeout: 30 * time.Second},
	}
}

// File is one downloadable file inside a search response. Fields are decoded
// defensively; any may be zero if slskd omits them.
type File struct {
	Filename  string `json:"filename"`
	Size      int64  `json:"size"`
	BitRate   int    `json:"bitRate"`
	Length    int    `json:"length"` // seconds
	Extension string `json:"extension"`
	IsLocked  bool   `json:"isLocked"`
	Code      int    `json:"code"`
}

// Response is one user's set of results for a search.
type Response struct {
	Username          string `json:"username"`
	HasFreeUploadSlot bool   `json:"hasFreeUploadSlot"`
	UploadSpeed       int64  `json:"uploadSpeed"`
	QueueLength       int    `json:"queueLength"`
	LockedFileCount   int    `json:"lockedFileCount"`
	FileCount         int    `json:"fileCount"`
	Files             []File `json:"files"`

	// Some slskd versions expose privacy/lock flags at the response level.
	IsPrivate bool `json:"isPrivate"`
	IsLocked  bool `json:"locked"`
}

// Candidate is a chosen file plus the user to download it from.
type Candidate struct {
	Username string
	File     File
}

func (c *Client) do(ctx context.Context, method, p string, body io.Reader, out any) error {
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+p, body)
	if err != nil {
		return fmt.Errorf("slskd: build request: %w", err)
	}
	req.Header.Set("X-API-Key", c.apiKey)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Accept", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("slskd: %s %s: %w", method, p, err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("slskd: %s %s: status %d: %s", method, p, resp.StatusCode, snippet(data))
	}
	if out == nil || len(data) == 0 {
		return nil
	}
	if err := json.Unmarshal(data, out); err != nil {
		return fmt.Errorf("slskd: decode %s: %w", p, err)
	}
	return nil
}

func snippet(b []byte) string {
	s := strings.TrimSpace(string(b))
	if len(s) > 200 {
		s = s[:200]
	}
	return s
}

// Search starts a search for the given text and returns the search id.
func (c *Client) Search(ctx context.Context, text string) (string, error) {
	body, _ := json.Marshal(map[string]string{"searchText": text})
	var out struct {
		ID string `json:"id"`
	}
	if err := c.do(ctx, http.MethodPost, "/api/v0/searches", bytes.NewReader(body), &out); err != nil {
		return "", err
	}
	if out.ID == "" {
		return "", fmt.Errorf("slskd: search returned empty id for %q", text)
	}
	return out.ID, nil
}

// searchStatus is the minimal completion view of a search.
type searchStatus struct {
	State         string `json:"state"`
	IsComplete    *bool  `json:"isComplete"`
	ResponseCount int    `json:"responseCount"`
}

func (c *Client) searchComplete(ctx context.Context, id string) (bool, error) {
	var st searchStatus
	if err := c.do(ctx, http.MethodGet, "/api/v0/searches/"+id, nil, &st); err != nil {
		return false, err
	}
	if st.IsComplete != nil {
		return *st.IsComplete, nil
	}
	// slskd reports state as a comma-joined flags string, e.g.
	// "Completed, Succeeded" or "InProgress". Treat any "Completed" / "Cancelled" as done.
	low := strings.ToLower(st.State)
	return strings.Contains(low, "completed") || strings.Contains(low, "cancelled"), nil
}

// responses fetches the responses for a search, tolerating both a bare array
// and a {"responses":[...]} envelope.
func (c *Client) responses(ctx context.Context, id string) ([]Response, error) {
	var arr []Response
	if err := c.do(ctx, http.MethodGet, "/api/v0/searches/"+id+"/responses", nil, &arr); err == nil && arr != nil {
		return arr, nil
	}
	var env struct {
		Responses []Response `json:"responses"`
	}
	if err := c.do(ctx, http.MethodGet, "/api/v0/searches/"+id+"/responses", nil, &env); err != nil {
		return nil, err
	}
	return env.Responses, nil
}

// SearchAndPick runs a search, polls until complete (bounded by ctx), and
// returns the single best acceptable candidate, or ok=false if none qualify.
//
// @MX:ANCHOR: [AUTO] Primary acquisition entry point used by the acquisition workers.
// @MX:REASON: fan_in >= 3 expected (acquire workers + director-driven retries); selection rules (privacy + bitrate floor) are a station-wide invariant.
func (c *Client) SearchAndPick(ctx context.Context, text string) (Candidate, bool, error) {
	id, err := c.Search(ctx, text)
	if err != nil {
		return Candidate{}, false, err
	}
	// Poll for completion. Give slskd time to gather peer responses.
	deadline := time.Now().Add(25 * time.Second)
	for {
		done, err := c.searchComplete(ctx, id)
		if err != nil {
			return Candidate{}, false, err
		}
		if done || time.Now().After(deadline) {
			break
		}
		select {
		case <-ctx.Done():
			return Candidate{}, false, ctx.Err()
		case <-time.After(1500 * time.Millisecond):
		}
	}
	resps, err := c.responses(ctx, id)
	if err != nil {
		return Candidate{}, false, err
	}
	cand, ok := pickBest(resps)
	return cand, ok, nil
}

// Download requests a download of files from a user. files carries the remote
// filename + size as slskd expects.
func (c *Client) Download(ctx context.Context, username string, files []File) error {
	type item struct {
		Filename string `json:"filename"`
		Size     int64  `json:"size"`
	}
	items := make([]item, 0, len(files))
	for _, f := range files {
		items = append(items, item{Filename: f.Filename, Size: f.Size})
	}
	body, _ := json.Marshal(items)
	return c.do(ctx, http.MethodPost, "/api/v0/transfers/downloads/"+pathEscape(username), bytes.NewReader(body), nil)
}

// Transfer is one entry in a user's download list (defensive subset).
type Transfer struct {
	Filename         string  `json:"filename"`
	State            string  `json:"state"`
	Size             int64   `json:"size"`
	BytesTransferred int64   `json:"bytesTransferred"`
	PercentComplete  float64 `json:"percentComplete"`
}

// DownloadStatus returns the raw transfer entries for a user. The shape varies
// across slskd versions (sometimes grouped by directory), so this best-effort
// flattens common layouts and never errors on shape mismatch alone.
func (c *Client) DownloadStatus(ctx context.Context, username string) ([]Transfer, error) {
	// Try the flat array form first.
	var flat []Transfer
	if err := c.do(ctx, http.MethodGet, "/api/v0/transfers/downloads/"+pathEscape(username), nil, &flat); err == nil && flat != nil {
		return flat, nil
	}
	// Grouped form: [{ "directories": [{ "files": [Transfer...] }] }] or
	// { "directories": [...] }. Decode into a generic structure.
	var grouped []struct {
		Directories []struct {
			Files []Transfer `json:"files"`
		} `json:"directories"`
	}
	if err := c.do(ctx, http.MethodGet, "/api/v0/transfers/downloads/"+pathEscape(username), nil, &grouped); err != nil {
		return nil, err
	}
	var out []Transfer
	for _, g := range grouped {
		for _, d := range g.Directories {
			out = append(out, d.Files...)
		}
	}
	return out, nil
}

// pathEscape escapes a username for use in a URL path segment without turning
// "/" handling into a surprise. slskd usernames are simple; we replace spaces.
func pathEscape(s string) string {
	return strings.ReplaceAll(s, " ", "%20")
}

// --- selection logic ---------------------------------------------------------

// pickBest applies the privacy/lock skip rules and the bitrate floor, then
// chooses the highest-quality acceptable file across all responses.
func pickBest(resps []Response) (Candidate, bool) {
	var best Candidate
	var bestScore int
	found := false
	for _, r := range resps {
		if skipUser(r) {
			continue
		}
		for _, f := range r.Files {
			if !acceptable(f) {
				continue
			}
			s := score(r, f)
			if !found || s > bestScore {
				best = Candidate{Username: r.Username, File: f}
				bestScore = s
				found = true
			}
		}
	}
	return best, found
}

// skipUser implements the [PRIVATE]/locked-user skip rule.
func skipUser(r Response) bool {
	if strings.Contains(strings.ToLower(r.Username), "[private]") {
		return true
	}
	if r.IsPrivate || r.IsLocked {
		return true
	}
	// Whole response is locked content.
	if r.FileCount > 0 && r.LockedFileCount >= r.FileCount {
		return true
	}
	return false
}

// acceptable is the single reusable predicate enforcing:
//   - skip locked files
//   - only audio extensions we want (mp3/flac/m4a/ogg/opus/wav)
//   - lossless (flac/wav) is always acceptable (top quality, no kbps floor)
//   - lossy must be >= MinLossyKbps; if bitRate is missing, estimate from
//     size*8/length/1000; if neither is available, skip (conservative).
//
// @MX:ANCHOR: [AUTO] Quality gate for every acquired track (slskd + estimation).
// @MX:REASON: invariant — no lossy file below 192 kbps may ever enter the library; changing this silently degrades the whole station.
func acceptable(f File) bool {
	if f.IsLocked || f.Filename == "" {
		return false
	}
	ext := fileExt(f)
	switch ext {
	case "flac", "wav", "aiff", "alac":
		return true // lossless: always top quality
	case "mp3", "m4a", "ogg", "opus", "aac":
		// lossy: enforce the kbps floor.
		if f.BitRate >= MinLossyKbps {
			return true
		}
		if f.BitRate == 0 && f.Length > 0 && f.Size > 0 {
			est := estimateKbps(f.Size, f.Length)
			return est >= MinLossyKbps
		}
		return false // no bitrate and no way to estimate → skip
	default:
		return false // unknown / non-audio extension
	}
}

// estimateKbps estimates the average bitrate in kbps from byte size and
// duration in seconds.
func estimateKbps(sizeBytes int64, lengthSeconds int) int {
	if lengthSeconds <= 0 {
		return 0
	}
	return int((sizeBytes * 8) / int64(lengthSeconds) / 1000)
}

func fileExt(f File) string {
	if f.Extension != "" {
		return strings.ToLower(strings.TrimPrefix(f.Extension, "."))
	}
	base := f.Filename
	// slskd filenames use backslashes (Windows Soulseek share paths).
	base = strings.ReplaceAll(base, "\\", "/")
	return strings.ToLower(strings.TrimPrefix(path.Ext(base), "."))
}

// score ranks an acceptable file. Higher is better: lossless beats lossy,
// higher bitrate beats lower, free upload slot is a strong bonus, then speed.
func score(r Response, f File) int {
	s := 0
	switch fileExt(f) {
	case "flac", "wav", "aiff", "alac":
		s += 100000
	default:
		s += f.BitRate
		if f.BitRate == 0 && f.Length > 0 {
			s += estimateKbps(f.Size, f.Length)
		}
	}
	if r.HasFreeUploadSlot {
		s += 50000
	}
	if r.UploadSpeed > 0 {
		s += int(r.UploadSpeed / 1000)
	}
	s -= r.QueueLength * 10
	return s
}
