// Package config loads the radiod runtime configuration from environment
// variables. All values have sensible defaults so the daemon can boot even
// with a sparse environment; secrets (API keys) default to empty.
package config

import "os"

// Config is the fully-resolved runtime configuration.
type Config struct {
	SlskdURL       string
	SlskdAPIKey    string
	LiquidsoapHost string
	LiquidsoapPort string
	MusicDir       string
	DBDir          string
	AnthropicKey   string
	AnthropicModel string
	StationName    string

	// Optional OAuth seed-enrichment credentials (currently unused stubs).
	SpotifyClientID     string
	SpotifyClientSecret string
	SpotifyUsername     string
	GoogleClientID      string
	GoogleClientSecret  string
	YouTubeHandle       string
}

func get(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

// Load reads configuration from the process environment.
func Load() Config {
	return Config{
		SlskdURL:       get("SLSKD_URL", "http://slskd:5030"),
		SlskdAPIKey:    os.Getenv("SLSKD_API_KEY"),
		LiquidsoapHost: get("LIQUIDSOAP_HOST", "liquidsoap"),
		LiquidsoapPort: get("LIQUIDSOAP_TELNET_PORT", "1234"),
		MusicDir:       get("MUSIC_DIR", "/music"),
		DBDir:          get("DB_DIR", "/db"),
		AnthropicKey:   os.Getenv("ANTHROPIC_API_KEY"),
		AnthropicModel: get("ANTHROPIC_MODEL", "claude-opus-4-8"),
		StationName:    get("STATION_NAME", "Golden Shower Radio"),

		SpotifyClientID:     os.Getenv("SPOTIFY_CLIENT_ID"),
		SpotifyClientSecret: os.Getenv("SPOTIFY_CLIENT_SECRET"),
		SpotifyUsername:     os.Getenv("SPOTIFY_USERNAME"),
		GoogleClientID:      os.Getenv("GOOGLE_CLIENT_ID"),
		GoogleClientSecret:  os.Getenv("GOOGLE_CLIENT_SECRET"),
		YouTubeHandle:       os.Getenv("YOUTUBE_HANDLE"),
	}
}

// BrainMode returns a human-readable description of the active director mode.
func (c Config) BrainMode() string {
	if c.AnthropicKey != "" {
		return "llm:" + c.AnthropicModel
	}
	return "seed (no ANTHROPIC_API_KEY)"
}
