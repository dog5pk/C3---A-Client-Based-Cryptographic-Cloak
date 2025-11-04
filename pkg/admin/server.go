package admin

import (
	"fmt"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/example/dbridge/pkg/metrics"
	dlog "github.com/example/dbridge/pkg/log"
)

var (
	isDraining atomic.Bool
)

// Start launches the admin HTTP server with health and metrics endpoints.
func Start(port string) {
	if port == "" {
		dlog.Warn("admin server disabled (no port configured)")
		return
	}
	mux := http.NewServeMux()
	mux.Handle("/metrics", metrics.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})
	mux.HandleFunc("/ready", func(w http.ResponseWriter, _ *http.Request) {
		if isDraining.Load() {
			http.Error(w, "draining", http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ready"))
	})
	mux.HandleFunc("/admin/drain", func(w http.ResponseWriter, _ *http.Request) {
		isDraining.Store(true)
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("draining"))
	})
	mux.HandleFunc("/admin/stats", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "timestamp=%s\n", time.Now().UTC().Format(time.RFC3339))
	})
	addr := fmt.Sprintf("0.0.0.0:%s", port)
	go func() {
		dlog.Info(fmt.Sprintf("admin server listening on %s", addr))
		if err := http.ListenAndServe(addr, mux); err != nil {
			dlog.Error(fmt.Sprintf("admin server stopped: %v", err))
		}
	}()
}
