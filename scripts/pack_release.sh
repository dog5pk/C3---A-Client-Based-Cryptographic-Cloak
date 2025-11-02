#!/usr/bin/env bash
# Create a portable dbridge_release.tar.gz archive with core binaries, client, and usage docs
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dbridge_release.tar.gz"

echo "🧼 Cleaning up prior outputs..."
rm -f "$OUT"

echo "📦 Creating archive..."
tar -czf "$OUT" \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='*.sqlite' \
  --exclude='*.bin' \
  --exclude='*.swp' \
  --exclude='*.DS_Store' \
  --exclude='logs/*' \
  --exclude='evaluation/*' \
  -C "$ROOT" \
  relays/relay \
  client/dbridge.py \
  client/README_DEMO.md \
  scripts/demo_systemd.sh \
  scripts/demo_spawn.sh \
  README.md \
  LICENSE \
  USAGE.md \
  Makefile

echo "✅ Release archive created at: $OUT"
