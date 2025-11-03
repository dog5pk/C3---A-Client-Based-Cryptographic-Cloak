#!/usr/bin/env bash
set -euo pipefail
for p in 9000 9001 9002; do
  sudo systemctl restart dbridge-relay@"$p".service
  hp=$((10000+p)); curl -fsS "http://127.0.0.1:${hp}/healthz" >/dev/null && echo "OK :$p"
done
