package main

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/example/dbridge/internal/relay"
	"github.com/example/dbridge/pkg/admin"
	dlog "github.com/example/dbridge/pkg/log"
)

func envOrDefault(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func envInt(k string, def int) int {
	v := os.Getenv(k)
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		dlog.Warn(fmt.Sprintf("invalid %s=%q", k, v))
		return def
	}
	return n
}

func main() {
	listen := envOrDefault("LISTEN_ADDR", "0.0.0.0:4000")
	dest := os.Getenv("DEST_ADDR")
	if dest == "" {
		fmt.Println("DEST_ADDR required (e.g. example.com:80)")
		os.Exit(1)
	}

	maxConn := envInt("MAX_CONN", 1024)
	adminPort := envOrDefault("HEALTH_PORT", "9090")
	aeadMode := envOrDefault("AEAD_MODE", "none")

	cfg := relay.Config{
		ListenAddr:     listen,
		DestAddr:       dest,
		MaxConnections: maxConn,
		DialTimeout:    5 * time.Second,
		ShutdownGrace:  15 * time.Second,
		AEADMode:       aeadMode,
	}

	dlog.Info(fmt.Sprintf("starting D-Bridge relay listen=%s dest=%s max_conn=%d", listen, dest, maxConn))
	dlog.Info(fmt.Sprintf("admin server expected on port %s", adminPort))

	// start admin HTTP server in background
	go admin.Start(adminPort)

	if err := relay.RunWithSignals(cfg); err != nil {
		dlog.Error(fmt.Sprintf("relay exited with error: %v", err))
		os.Exit(1)
	}
}
