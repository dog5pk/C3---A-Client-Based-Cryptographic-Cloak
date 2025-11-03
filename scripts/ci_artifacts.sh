#!/usr/bin/env bash
# Download latest CI artifact (tar.gz + .sha256) for this repo and verify.
set -euo pipefail
cd "$(dirname "$0")/.."

# Find latest successful run of our workflow
RUN_ID="$(gh run list --workflow 'D-Bridge CI Selftest' --json databaseId,conclusion,createdAt \
  --jq '[.[] | select(.conclusion=="success")][0].databaseId' 2>/dev/null || true)"

[ -n "${RUN_ID:-}" ] || { echo "[error] no successful runs found"; exit 1; }

OUTDIR="ci_artifacts/${RUN_ID}"
mkdir -p "$OUTDIR"

# Download artifact named 'dbridge-artifact'
gh run download "$RUN_ID" --name dbridge-artifact -D "$OUTDIR"

TGZ="$(ls -1 "$OUTDIR"/dbridge_release_*.tar.gz | head -n1 || true)"
SHA="${TGZ}.sha256"
[ -f "$TGZ" ] || { echo "[error] tarball not found in $OUTDIR"; exit 1; }
[ -f "$SHA" ] || { echo "[error] sha256 file not found in $OUTDIR"; exit 1; }

echo "[verify] computed : $(sha256sum "$TGZ" | awk '{print $1}')"
echo "[verify] recorded : $(awk '{print $1}' "$SHA")"
sha256sum -c "$SHA"
echo "[verify] checksum VERIFIED ✅"
echo "[saved] $OUTDIR"
