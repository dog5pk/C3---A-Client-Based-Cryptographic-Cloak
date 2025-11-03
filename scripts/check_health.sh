#!/usr/bin/env bash
set -euo pipefail
CHAIN="${1:-127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002}"
ok=0; total=0
IFS=',' read -ra HOPS <<<"$CHAIN"
echo "[check] listeners:"
ss -ltnp | grep -E ':(9000|9001|9002)\b' || true
echo "[check] health endpoints:"
for hop in "${HOPS[@]}"; do
  port="${hop##*:}"; hp=$((10000+port)); total=$((total+1))
  if curl -fsS "http://127.0.0.1:${hp}/healthz" >/dev/null; then
    echo "  OK  :$port (health :$hp)"; ok=$((ok+1))
  else
    echo "  FAIL:$port (health :$hp)"
  fi
done
echo "[summary] $ok / $total healthy"
[ "$ok" -eq "$total" ]
