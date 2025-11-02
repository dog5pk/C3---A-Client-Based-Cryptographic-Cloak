#!/usr/bin/env bash
set -euo pipefail
CHAIN="${1:-127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002}"
ok=0
IFS=',' read -ra HOPS <<<"$CHAIN"
for hop in "${HOPS[@]}"; do
  port="${hop##*:}"
  health=$((10000 + port)) # from unit: --health-addr=127.0.0.1:1%i
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${health}/healthz" || true)
  if [ "$code" = "200" ]; then
    echo "OK :$port (health :$health)"
    ok=$((ok+1))
  else
    echo "FAIL :$port (health :$health)"
  fi
done
[ "$ok" -eq "${#HOPS[@]}" ]
