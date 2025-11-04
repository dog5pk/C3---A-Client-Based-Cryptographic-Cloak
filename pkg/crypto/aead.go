package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"errors"
	"fmt"
	"io"

	"golang.org/x/crypto/chacha20poly1305"
	"golang.org/x/crypto/hkdf"
)

// AEADMode defines the supported encryption algorithms.
type AEADMode string

const (
	AEADXChaCha20 AEADMode = "xchacha"
	AEADAESGCM    AEADMode = "aesgcm"
)

// KeySize defines the base key size for HKDF output.
const KeySize = 32 // 256 bits

// AEAD wraps an AEAD cipher with deterministic key derivation.
type AEAD struct {
	aead cipher.AEAD
	mode AEADMode
}

// DeriveKey uses HKDF-SHA256 to derive a per-connection key from a master key and salt.
func DeriveKey(master, salt []byte) ([]byte, error) {
	if len(master) == 0 || len(salt) == 0 {
		return nil, errors.New("master key and salt required")
	}
	h := hkdf.New(sha256.New, master, salt, nil)
	key := make([]byte, KeySize)
	if _, err := io.ReadFull(h, key); err != nil {
		return nil, err
	}
	return key, nil
}

// NewAEAD initializes an AEAD cipher based on the given mode.
func NewAEAD(mode AEADMode, key []byte) (*AEAD, error) {
	switch mode {
	case AEADXChaCha20:
		aead, err := chacha20poly1305.NewX(key)
		if err != nil {
			return nil, err
		}
		return &AEAD{aead: aead, mode: mode}, nil
	case AEADAESGCM:
		block, err := aes.NewCipher(key)
		if err != nil {
			return nil, err
		}
		aead, err := cipher.NewGCM(block)
		if err != nil {
			return nil, err
		}
		return &AEAD{aead: aead, mode: mode}, nil
	default:
		return nil, fmt.Errorf("unsupported AEAD mode: %s", mode)
	}
}

// Encrypt encrypts plaintext with a random nonce and returns nonce||ciphertext.
func (a *AEAD) Encrypt(plaintext, aad []byte) ([]byte, error) {
	nonce := make([]byte, a.aead.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	ct := a.aead.Seal(nil, nonce, plaintext, aad)
	return append(nonce, ct...), nil
}

// Decrypt decrypts a ciphertext of form nonce||ciphertext and returns plaintext.
func (a *AEAD) Decrypt(ciphertext, aad []byte) ([]byte, error) {
	n := a.aead.NonceSize()
	if len(ciphertext) < n {
		return nil, errors.New("ciphertext too short")
	}
	nonce := ciphertext[:n]
	ct := ciphertext[n:]
	return a.aead.Open(nil, nonce, ct, aad)
}
