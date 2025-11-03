#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- build & start relays ---
cd "$ROOT/relays"
go mod init dbridge-relay >/dev/null 2>&1 || true
go build -o relay relay.go

./relay --host=127.0.0.1 --port=9000 --health-addr=127.0.0.1:19000 & P1=$!
./relay --host=127.0.0.1 --port=9001 --health-addr=127.0.0.1:19001 & P2=$!
./relay --host=127.0.0.1 --port=9002 --health-addr=127.0.0.1:19002 & P3=$!

cleanup() { kill $P1 $P2 $P3 2>/dev/null || true; }
trap cleanup EXIT

sleep 1
for hp in 19000 19001 19002; do curl -fsS "http://127.0.0.1:${hp}/healthz" >/dev/null; done

# --- end-to-end test ---
cd "$ROOT/client"
echo "CI selftest" > e2e_test.txt

python3 dbridge.py --tcp --chain "127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" --pad 512 --mtu 700 sendfile e2e_test.txt
python3 dbridge.py --tcp --chain "127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" --mtu 700 forward final_obfuscated_output.bin
python3 dbridge.py --tcp --chain "127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" --pad 512 --mtu 700 receive relay_output_3.bin

cmp -s e2e_test.txt received_output.bin
echo "[OK] CI round-trip verified"
