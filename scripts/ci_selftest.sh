#!/usr/bin/env bash
set -euo pipefail
set -x  # trace everything for CI logs

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[env] GO:"; go version || true
echo "[env] PY:"; python3 --version || true
echo "[env] PIP:"; python3 -m pip --version || true
echo "[env] CURL:"; curl --version | head -n1 || true
echo "[env] LSOF:"; lsof -v 2>/dev/null | head -n1 || true

# Build & spawn 3 relays
cd "$ROOT/relays"
[ -x ./relay ] || go build -v -o relay relay.go

./relay --host=127.0.0.1 --port=9000 --health-addr=127.0.0.1:19000 & P1=$!
./relay --host=127.0.0.1 --port=9001 --health-addr=127.0.0.1:19001 & P2=$!
./relay --host=127.0.0.1 --port=9002 --health-addr=127.0.0.1:19002 & P3=$!
trap 'kill -9 $P1 $P2 $P3 2>/dev/null || true' EXIT
sleep 1

for hp in 19000 19001 19002; do
  curl -fsS "http://127.0.0.1:${hp}/healthz" >/dev/null || { echo "[FAIL] health ${hp}"; exit 1; }
done
echo "[OK] relays up"

# Client E2E in venv
cd "$ROOT/client"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
# Ensure wheels present; cryptography wheel should exist on ubuntu-latest
python -m pip install "cryptography>=41,<43"

# Secrets local to CI
python - <<'PY'
import json,secrets,pathlib
p=pathlib.Path("secrets.json")
if not p.exists():
  p.write_text(json.dumps({"root_secret":secrets.token_hex(32)}, indent=2))
  print("secrets.json generated")
else:
  print("secrets.json present")
PY

CHAIN="127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002"
PAD=512
MTU=700

echo "CI selftest payload" > e2e_test.txt

python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad $PAD --mtu $MTU sendfile e2e_test.txt
python3 dbridge.py --tcp --chain "$CHAIN" --mtu $MTU forward final_obfuscated_output.bin
python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad $PAD --mtu $MTU --replay-db ../dbridge_replay.sqlite receive relay_output_3.bin

cmp -s e2e_test.txt received_output.bin || { echo "[FAIL] mismatch"; exit 1; }
echo "[OK] CI selftest passed"
deactivate
