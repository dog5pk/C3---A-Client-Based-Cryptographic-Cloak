#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CHAIN="127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002"
cd relays && go build -o relay relay.go && cd ..

cd client
. .venv/bin/activate 2>/dev/null || { python3 -m venv .venv && . .venv/bin/activate; }
pip install -q cryptography

echo '{"root_secret": "abcdef"}' > secrets.json
echo "spawned relay demo" > demo.txt

python3 dbridge.py --tcp --spawn-relays --relay-bin ../relays/relay --chain "$CHAIN" --secrets secrets.json --pad 512 --mtu 700 sendfile demo.txt
python3 dbridge.py --tcp --spawn-relays --relay-bin ../relays/relay --chain "$CHAIN" --mtu 700 forward final_obfuscated_output.bin
python3 dbridge.py --tcp --spawn-relays --relay-bin ../relays/relay --chain "$CHAIN" --secrets secrets.json --pad 512 --replay-db ../dbridge_replay.sqlite --mtu 700 receive relay_output_3.bin

sha256sum demo.txt received_output.bin
diff -q demo.txt received_output.bin && echo "OK ✅"
