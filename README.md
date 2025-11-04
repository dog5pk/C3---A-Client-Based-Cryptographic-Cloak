# D-Bridge

**D-Bridge** is a multi-hop, encrypted TCP relay system designed for privacy research and secure network obfuscation.  
It forwards arbitrary TCP streams through independently configurable hops, optionally applying per-hop authenticated encryption (AEAD).

## Quickstart

```bash
git clone https://github.com/example/dbridge.git
cd dbridge
go build -o bin/relay ./cmd/relay

LISTEN_ADDR="127.0.0.1:4000" \
DEST_ADDR="example.com:80" \
HEALTH_PORT="9090" \
AEAD_MODE="xchacha" \
./bin/relay
