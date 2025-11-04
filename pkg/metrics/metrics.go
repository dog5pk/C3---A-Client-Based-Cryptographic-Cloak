package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"net/http"
)

var (
	ActiveConnections = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "dbridge_active_connections",
		Help: "Number of active TCP connections.",
	})

	BytesForwarded = promauto.NewCounter(prometheus.CounterOpts{
		Name: "dbridge_bytes_forwarded_total",
		Help: "Total bytes forwarded through the relay.",
	})

	ConnectionLatency = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "dbridge_connection_latency_seconds",
		Help:    "Histogram of connection lifetimes.",
		Buckets: prometheus.LinearBuckets(0.05, 0.05, 20),
	})
)

// Handler returns the Prometheus metrics handler.
func Handler() http.Handler {
	return promhttp.Handler()
}
