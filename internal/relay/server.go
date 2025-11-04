package relay

import (
	"context"
	"crypto/rand"
	"fmt"
	"net"
	"os"
	"os/signal"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/example/dbridge/pkg/crypto"
	dlog "github.com/example/dbridge/pkg/log"
)

// Server handles incoming TCP connections and forwards them, optionally encrypted.
type Server struct {
	cfg      Config
	listener net.Listener
	active   int32
	wg       sync.WaitGroup
	shutting int32
}

// NewServer returns a relay server configured for plaintext or AEAD forwarding.
func NewServer(cfg Config) *Server {
	return &Server{cfg: cfg}
}

// Start runs until the context is cancelled or a fatal error occurs.
func (s *Server) Start(ctx context.Context) error {
	if s.cfg.ListenAddr == "" || s.cfg.DestAddr == "" {
		return fmt.Errorf("ListenAddr and DestAddr must be set")
	}

	ln, err := net.Listen("tcp", s.cfg.ListenAddr)
	if err != nil {
		return fmt.Errorf("listen on %s: %w", s.cfg.ListenAddr, err)
	}
	s.listener = ln
	dlog.Info(fmt.Sprintf("listening on %s -> %s (AEAD: %v)", s.cfg.ListenAddr, s.cfg.DestAddr, s.cfg.AEADMode))

	errCh := make(chan error, 1)

	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				if atomic.LoadInt32(&s.shutting) == 1 {
					errCh <- nil
					return
				}
				if ne, ok := err.(net.Error); ok && ne.Temporary() {
					dlog.Warn(fmt.Sprintf("temporary accept error: %v", err))
					time.Sleep(100 * time.Millisecond)
					continue
				}
				errCh <- fmt.Errorf("accept error: %w", err)
				return
			}

			if s.cfg.MaxConnections > 0 && int(atomic.LoadInt32(&s.active)) >= s.cfg.MaxConnections {
				dlog.Warn("reject: max connections reached")
				_ = conn.Close()
				continue
			}

			atomic.AddInt32(&s.active, 1)
			s.wg.Add(1)
			go s.handleConn(conn)
		}
	}()

	select {
	case <-ctx.Done():
		return s.shutdown()
	case err := <-errCh:
		if err != nil {
			dlog.Error(fmt.Sprintf("server error: %v", err))
		}
		return err
	}
}

// handleConn encrypts and forwards data through the configured chain.
func (s *Server) handleConn(inConn net.Conn) {
	defer s.wg.Done()
	defer func() {
		atomic.AddInt32(&s.active, -1)
		_ = inConn.Close()
	}()

	remote := inConn.RemoteAddr().String()
	dlog.Info(fmt.Sprintf("accepted connection from %s", remote))

	target := s.cfg.DestAddr
	if len(s.cfg.NextHops) > 0 {
		chain := append(s.cfg.NextHops, s.cfg.DestAddr)
		for _, hop := range chain {
			dlog.Info(fmt.Sprintf("→ hop %s", hop))
			target = hop
		}
	}

	dialer := &net.Dialer{Timeout: s.cfg.DialTimeout}
	if dialer.Timeout == 0 {
		dialer.Timeout = 5 * time.Second
	}

	outConn, err := dialer.Dial("tcp", target)
	if err != nil {
		dlog.Error(fmt.Sprintf("dial %s failed: %v", target, err))
		return
	}
	defer outConn.Close()

	// Setup AEAD encryption if configured
	useAEAD := false
	var mode crypto.AEADMode
	var key []byte

	if s.cfg.AEADMode != "" && s.cfg.AEADMode != "none" {
		useAEAD = true
		mode = crypto.AEADMode(s.cfg.AEADMode)

		key = make([]byte, crypto.KeySize)
		if _, err := rand.Read(key); err != nil {
			dlog.Error(fmt.Sprintf("keygen failed: %v", err))
			useAEAD = false
		}
	}

	sp := NewSecurePipe(key, mode, useAEAD)
	sp.Forward(inConn, outConn)

	dlog.Info(fmt.Sprintf("closed connection from %s", remote))
}

// shutdown stops listening and waits for all connections to drain.
func (s *Server) shutdown() error {
	if s.listener == nil {
		return nil
	}
	atomic.StoreInt32(&s.shutting, 1)
	_ = s.listener.Close()
	dlog.Info("waiting for active connections to drain...")
	s.wg.Wait()
	dlog.Info("server shutdown complete")
	return nil
}

// RunWithSignals runs the relay until SIGINT or SIGTERM.
func RunWithSignals(cfg Config) error {
	srv := NewServer(cfg)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigCh
		dlog.Warn(fmt.Sprintf("signal received: %s; shutting down", sig.String()))
		cancel()
	}()

	return srv.Start(ctx)
}
