#!/usr/bin/env bash
# Ship ritual: health -> selftest -> pack -> verify
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[ship] health"
./scripts/check_health.sh >/dev/null || { echo "[ship] starting relays"; for p in 9000 9001 9002; do sudo systemctl enable --now dbridge-relay@"$p".service >/dev/null || true; done; sleep 1; ./scripts/check_health.sh; }

echo "[ship] selftest"
./scripts/selftest.sh

echo "[ship] pack"
./scripts/pack_release.sh

echo "[ship] verify"
./scripts/verify_release.sh V01.01 || ./scripts/verify_release.sh

echo "[ship] DONE ✅"
