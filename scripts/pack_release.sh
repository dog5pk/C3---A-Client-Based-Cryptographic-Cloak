#!/usr/bin/env bash
# Build sanitized release tarball (no secrets, bins, venvs, logs)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="${VERSION:-$(git describe --tags --abbrev=0 2>/dev/null || date +%Y%m%d)}"
OUT="dbridge_release_${VERSION}.tar.gz"
tar --exclude-vcs \
    --exclude='./client/.venv' \
    --exclude='./.venv' \
    --exclude='*.bin' \
    --exclude='*.sqlite' \
    --exclude='*.log' \
    --exclude='./nonce_log.csv' \
    --exclude='./relays/relay' \
    --exclude='./client/secrets.json' \
    --exclude='./dbridge_release_*.tar.gz' \
    -czf "$OUT" .
sha256sum "$OUT" | tee "${OUT}.sha256"
echo "Wrote: $OUT"
