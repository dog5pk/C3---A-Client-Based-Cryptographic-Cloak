#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

RELEASE_DIR="release"
BIN_NAME="relay"
VERSION="${1:-$(date +v%Y.%m.%d-%H%M)}"

echo "[*] Building deterministic release $VERSION ..."
mkdir -p "$RELEASE_DIR"/artifacts "$RELEASE_DIR"/bin

# clean build
go mod tidy
go vet ./...

# deterministic build
go build -trimpath -buildvcs=false -ldflags="-s -w -buildid=" -o "$RELEASE_DIR/bin/$BIN_NAME" ./cmd/relay

echo "[*] Calculating SHA256 checksums..."
sha256sum "$RELEASE_DIR/bin/$BIN_NAME" > "$RELEASE_DIR/artifacts/SHA256SUMS"

echo "[*] Creating provenance statement..."
cat > "$RELEASE_DIR/artifacts/PROVENANCE.txt" <<EOF
D-Bridge Build Provenance
=========================
Version: $VERSION
Date: $(date -u)
Go Version: $(go version)
Git Commit: $(git rev-parse --short HEAD 2>/dev/null || echo "none")
SHA256: $(cut -d ' ' -f1 "$RELEASE_DIR/artifacts/SHA256SUMS")
Build Flags: -trimpath -buildvcs=false -ldflags="-s -w -buildid="
EOF

echo "[*] Signing checksum (local, unsigned demo key)..."
openssl dgst -sha256 -sign ~/.ssh/id_rsa -out "$RELEASE_DIR/artifacts/SHA256SUMS.sig" "$RELEASE_DIR/artifacts/SHA256SUMS" 2>/dev/null || echo "(no signing key, skipping)"

echo "[*] Packaging release archive..."
tar -czf "$RELEASE_DIR/dbridge_${VERSION}.tar.gz" -C "$RELEASE_DIR" bin artifacts

echo
echo "[+] Release complete: $RELEASE_DIR/dbridge_${VERSION}.tar.gz"
echo "[+] Verify using: ./verify_provenance.sh $RELEASE_DIR/dbridge_${VERSION}.tar.gz"

