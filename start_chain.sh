#!/usr/bin/env bash
# start_chain stub — placeholder for real relays; safe on any machine.
set -euo pipefail

: "${ADMIN_ADDR:=:18022}"
: "${RELAY1_PORT:=15001}"
: "${RELAY2_PORT:=15002}"
: "${UPSTREAM_ADDR:=127.0.0.1:8080}"
: "${C3_PRESET:=low}"

echo "C3: start_chain (stub) — admin=$ADMIN_ADDR r1=:${RELAY1_PORT} r2=:${RELAY2_PORT} upstream=${UPSTREAM_ADDR} preset=${C3_PRESET}"
echo "No services started (this is a stub). OK."
exit 0
