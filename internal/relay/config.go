package relay

import "time"

// Config defines runtime settings for one relay hop.
type Config struct {
	ListenAddr        string
	DestAddr          string
	NextHops          []string
	MaxConnections    int
	MaxPerIP          int
	MaxBytesPerSecond uint64
	HealthPort        string
	MetricsPort       string
	AEADMode          string // <--- Added: defines encryption mode (none|xchacha|aesgcm)
	ShutdownGrace     time.Duration
	DialTimeout       time.Duration
	IdleTimeout       time.Duration
}
