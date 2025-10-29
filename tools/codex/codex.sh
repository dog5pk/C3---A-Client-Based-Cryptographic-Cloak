#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="${CODEX_CONFIG:-$ROOT/codex.config.yml}"
echo "[codex] start"
echo "[codex] config: $CFG"
echo '{"status":"ok","ts":"'"$(date -u +%FT%TZ)"'"}' > "$ROOT/report.json"
echo "[codex] done"
