package relay

import (
	"crypto/rand"
	"errors"
	"fmt"
	"io"
	"net"

	"github.com/example/dbridge/pkg/crypto"
	dlog "github.com/example/dbridge/pkg/log"
)

// SecurePipe wraps two net.Conn objects and encrypts traffic between them.
type SecurePipe struct {
	mode     crypto.AEADMode
	master   []byte
	useAEAD  bool
}

// NewSecurePipe initializes a secure data pipe using AEAD.
// If useAEAD is false, traffic is forwarded plaintext.
func NewSecurePipe(masterKey []byte, mode crypto.AEADMode, useAEAD bool) *SecurePipe {
	return &SecurePipe{
		mode:    mode,
		master:  masterKey,
		useAEAD: useAEAD,
	}
}

// Forward copies data bidirectionally between src and dst.
// If encryption is enabled, each direction is independently protected.
func (sp *SecurePipe) Forward(src, dst net.Conn) {
	if !sp.useAEAD {
		// Plaintext fast path
		errCh := make(chan error, 2)
		go pipe(dst, src, errCh)
		go pipe(src, dst, errCh)
		<-errCh
		return
	}

	// Derive per-connection keys
	saltA := make([]byte, 32)
	saltB := make([]byte, 32)
	if _, err := rand.Read(saltA); err != nil {
		dlog.Error(fmt.Sprintf("rand saltA failed: %v", err))
		return
	}
	if _, err := rand.Read(saltB); err != nil {
		dlog.Error(fmt.Sprintf("rand saltB failed: %v", err))
		return
	}

	keyA, err := crypto.DeriveKey(sp.master, saltA)
	if err != nil {
		dlog.Error(fmt.Sprintf("key derivation A failed: %v", err))
		return
	}
	keyB, err := crypto.DeriveKey(sp.master, saltB)
	if err != nil {
		dlog.Error(fmt.Sprintf("key derivation B failed: %v", err))
		return
	}

	aeadA, err := crypto.NewAEAD(sp.mode, keyA)
	if err != nil {
		dlog.Error(fmt.Sprintf("AEAD A init failed: %v", err))
		return
	}
	aeadB, err := crypto.NewAEAD(sp.mode, keyB)
	if err != nil {
		dlog.Error(fmt.Sprintf("AEAD B init failed: %v", err))
		return
	}

	errCh := make(chan error, 2)
	go sp.pipeEncrypt(aeadA, dst, src, "upstream", errCh)
	go sp.pipeDecrypt(aeadB, src, dst, "downstream", errCh)
	<-errCh
}

// pipe handles plaintext forwarding with io.Copy
func pipe(dst, src net.Conn, errCh chan error) {
	_, err := io.Copy(dst, src)
	if err != nil && !errors.Is(err, io.EOF) {
		errCh <- fmt.Errorf("pipe error: %w", err)
		return
	}
	errCh <- nil
}

// pipeEncrypt reads from src, encrypts, and writes to dst
func (sp *SecurePipe) pipeEncrypt(aead *crypto.AEAD, dst, src net.Conn, tag string, errCh chan error) {
	buf := make([]byte, 4096)
	for {
		n, err := src.Read(buf)
		if n > 0 {
			ct, e := aead.Encrypt(buf[:n], nil)
			if e != nil {
				errCh <- fmt.Errorf("%s encrypt error: %w", tag, e)
				return
			}
			if _, e := dst.Write(ct); e != nil {
				errCh <- fmt.Errorf("%s write error: %w", tag, e)
				return
			}
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				errCh <- nil
				return
			}
			errCh <- fmt.Errorf("%s read error: %w", tag, err)
			return
		}
	}
}

// pipeDecrypt reads ciphertext from src, decrypts, and writes plaintext to dst
func (sp *SecurePipe) pipeDecrypt(aead *crypto.AEAD, dst, src net.Conn, tag string, errCh chan error) {
	buf := make([]byte, 8192)
	for {
		n, err := src.Read(buf)
		if n > 0 {
			pt, e := aead.Decrypt(buf[:n], nil)
			if e != nil {
				errCh <- fmt.Errorf("%s decrypt error: %w", tag, e)
				return
			}
			if _, e := dst.Write(pt); e != nil {
				errCh <- fmt.Errorf("%s write error: %w", tag, e)
				return
			}
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				errCh <- nil
				return
			}
			errCh <- fmt.Errorf("%s read error: %w", tag, err)
			return
		}
	}
}
