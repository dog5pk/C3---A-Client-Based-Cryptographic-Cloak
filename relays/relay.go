// D-Bridge relay (production): length-prefixed echo with timeouts, caps, keepalive, /healthz
package main

import (
	"encoding/binary"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"sync/atomic"
	"time"
)

var (
	host        = flag.String("host", "0.0.0.0", "listen host")
	port        = flag.Int("port", 9000, "listen TCP port")
	maxPayload  = flag.Int("max-bytes", 64<<20, "maximum payload (bytes)")
	readTO      = flag.Duration("read-timeout", 60*time.Second, "per-conn read timeout")
	writeTO     = flag.Duration("write-timeout", 60*time.Second, "per-conn write timeout")
	keepAlive   = flag.Duration("keepalive", 30*time.Second, "TCP keepalive")
	concurrency = flag.Int("max-conns", 4096, "max concurrent connections")
	healthAddr  = flag.String("health-addr", "127.0.0.1:0", "HTTP health address (empty disables)")
)

var (
	activeConns int64
	totalReqs   uint64
	totalBytes  uint64
)

func main() {
	flag.Parse()
	addr := fmt.Sprintf("%s:%d", *host, *port)

	// optional /healthz
	if *healthAddr != "" {
		go func() {
			mux := http.NewServeMux()
			mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "text/plain")
				fmt.Fprintf(w, "ok active=%d totalReqs=%d totalBytes=%d goroutines=%d\n",
					atomic.LoadInt64(&activeConns), atomic.LoadUint64(&totalReqs),
					atomic.LoadUint64(&totalBytes), runtime.NumGoroutine())
			})
			srv := &http.Server{
				Addr:              *healthAddr,
				Handler:           mux,
				ReadHeaderTimeout: 2 * time.Second,
			}
			_ = srv.ListenAndServe()
		}()
	}

	ln, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("listen %s: %v", addr, err)
	}
	log.Printf("relay listening on %s pid=%d", addr, os.Getpid())

	sem := make(chan struct{}, *concurrency)
	for {
		c, err := ln.Accept()
		if err != nil {
			log.Printf("accept: %v", err)
			continue
		}
		select {
		case sem <- struct{}{}:
			go func() {
				defer func() { <-sem }()
				handle(c)
			}()
		default:
			// too many connections
			_ = c.Close()
		}
	}
}

func handle(c net.Conn) {
	defer c.Close()

	// TCP keepalive if possible
	if tc, ok := c.(*net.TCPConn); ok && *keepAlive > 0 {
		_ = tc.SetKeepAlive(true)
		_ = tc.SetKeepAlivePeriod(*keepAlive)
	}

	atomic.AddInt64(&activeConns, 1)
	defer atomic.AddInt64(&activeConns, -1)

	for {
		_ = c.SetReadDeadline(time.Now().Add(*readTO))
		_ = c.SetWriteDeadline(time.Now().Add(*writeTO))

		var hdr [4]byte
		if err := readExact(c, hdr[:]); err != nil {
			if err != io.EOF {
				// minor: log once per conn failure
				log.Printf("read len: %v", err)
			}
			return
		}
		n := binary.BigEndian.Uint32(hdr[:])
		if n > uint32(*maxPayload) {
			log.Printf("refuse payload >%d: %d", *maxPayload, n)
			return
		}
		if n == 0 {
			if _, err := c.Write(hdr[:]); err != nil {
				return
			}
			continue
		}
		buf := make([]byte, n)
		if err := readExact(c, buf); err != nil {
			return
		}
		atomic.AddUint64(&totalReqs, 1)
		atomic.AddUint64(&totalBytes, uint64(len(buf)))

		if _, err := c.Write(hdr[:]); err != nil {
			return
		}
		if _, err := c.Write(buf); err != nil {
			return
		}
	}
}

func readExact(r io.Reader, p []byte) error {
	off := 0
	for off < len(p) {
		n, err := r.Read(p[off:])
		if n > 0 {
			off += n
		}
		if err != nil {
			return err
		}
	}
	return nil
}

// Optional tiny CLI helper: prints healthy if /healthz returns ok
// curl "http://127.0.0.1:HEALTHPORT/healthz" or use docker/compose healthcheck
func healthCheck(addr string) bool {
	resp, err := http.Get("http://" + addr + "/healthz")
	return err == nil && resp.StatusCode == 200
}

// _ satisfies import of strconv in case we want dynamic flags via env (future).
var _ = strconv.Itoa
