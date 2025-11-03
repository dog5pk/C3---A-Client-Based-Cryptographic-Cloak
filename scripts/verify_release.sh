#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VER="${1:-}"
if [ -z "$VER" ]; then
  TGZ="$(ls -1t dbridge_release_*.tar.gz 2>/dev/null | head -n1 || true)"
else
  TGZ="dbridge_release_${VER}.tar.gz"
fi
SHA="${TGZ}.sha256"

[ -f "$TGZ" ] || { echo "[error] not found: $TGZ"; exit 1; }
[ -f "$SHA" ] || { echo "[error] not found: $SHA"; exit 1; }

echo "[verify] file: $TGZ"
echo "[verify] computed : $(sha256sum "$TGZ" | awk '{print $1}')"
echo "[verify] recorded : $(awk '{print $1}' "$SHA")"
sha256sum -c "$SHA"
echo "[verify] checksum VERIFIED ✅"
