#!/usr/bin/env bash
# CI ship flow: ci_selftest -> pack -> verify
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

./scripts/ci_selftest.sh
VERSION="${VERSION:-V01.01}"
./scripts/pack_release.sh
./scripts/verify_release.sh "$VERSION" || ./scripts/verify_release.sh
echo "[CI] ship flow DONE ✅"
