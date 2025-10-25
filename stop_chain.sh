#!/usr/bin/env bash
# stop_chain stub — symmetric with start_chain; safe and idempotent.
set -euo pipefail

# In the real version we’ll read pids/ and kill gently; for now, just report.
echo "C3: stop_chain (stub) — no running services to stop. OK."
exit 0
