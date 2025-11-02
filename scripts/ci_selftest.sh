#!/usr/bin/env bash
# CI-safe E2E: spawn relays (no systemd), run hash-equality self-test.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT="$ROOT/client"
RELAYS="$ROOT/relays"
CHAIN="127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002"

# Build relay
(cd "$RELAYS" && go build -o relay relay.go)

# Python env
cd "$CLIENT"
python3 -m venv .venv >/dev/null 2>&1 || true
. .venv/bin/activate
pip install --disable-pip-version-check -q cryptography

# Fresh local secret
python3 - <<'PY'
import json,secrets,pathlib
pathlib.Path("secrets.json").write_text(json.dumps({"root_secret": secrets.token_hex(32)}, indent=2))
print("secrets.json generated")
PY

# Payload
echo "ci selftest" > ci_selftest.txt

# Send → Forward → Receive (spawn relays each call)
python3 dbridge.py --tcp --spawn-relays --relay-bin ../relays/relay \
  --chain "$CHAIN" --secrets secrets.json --pad 512 --mtu 700 sendfile ci_selftest.txt

python3 dbridge.py --tcp --spawn-relays --relay-bin ../relays/relay \
  --chain "$CHAIN" --mtu 700 forward final_obfuscated_output.bin

python3 dbridge.py --tcp --spawn-relays --relay-bin ../relays/relay \
  --chain "$CHAIN" --secrets secrets.json --pad 512 --replay-db ../dbridge_replay.sqlite --mtu 700 receive relay_output_3.bin

# Verify
diff -q ci_selftest.txt received_output.bin && echo "[CI] selftest passed ✅"
