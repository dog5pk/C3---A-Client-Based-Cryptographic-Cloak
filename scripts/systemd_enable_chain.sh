#!/usr/bin/env bash
set -euo pipefail
CHAIN="${1:-127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002}"
sudo systemctl daemon-reload
IFS=',' read -ra HOPS <<<"$CHAIN"
for hop in "${HOPS[@]}"; do
  port="${hop##*:}"
  sudo systemctl enable --now dbridge-relay@"$port".service
done
systemctl --no-pager --full status dbridge-relay@*.service || true
