#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Build + spawn 3 relays locally with health ports 19000..19002
cd "$ROOT/relays"
[ -x ./relay ] || go build -o relay relay.go
./relay --host=127.0.0.1 --port=9000 --health-addr=127.0.0.1:19000 & P0=$!
./relay --host=127.0.0.1 --port=9001 --health-addr=127.0.0.1:19001 & P1=$!
./relay --host=127.0.0.1 --port=9002 --health-addr=127.0.0.1:19002 & P2=$!
cd "$ROOT"

# Wait a moment and confirm health endpoints
sleep 1
for hp in 19000 19001 19002; do
  curl -fsS "http://127.0.0.1:${hp}/healthz" >/dev/null
done

# E2E: send → forward → receive
cd "$ROOT/client"
echo "CI selftest" > e2e_test.txt
python dbridge.py --tcp --chain "127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" --pad 512 --mtu 700 sendfile e2e_test.txt
python dbridge.py --tcp --chain "127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" --mtu 700 forward final_obfuscated_output.bin
python dbridge.py --tcp --chain "127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" --pad 512 --replay-db ../dbridge_replay.sqlite --mtu 700 receive "relay_output_3.bin"

# Verify integrity
sha256sum e2e_test.txt received_output.bin | awk '{print $1}' | sort | uniq | wc -l | grep -qx '1'

# Stop relays
kill $P0 $P1 $P2 || true
wait || true
