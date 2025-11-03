#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Build & spawn 3 relays locally (health on 19000..19002)
cd "$ROOT/relays"
[ -x ./relay ] || go build -o relay relay.go
./relay --host=127.0.0.1 --port=9000 --health-addr=127.0.0.1:19000 & P1=$!
./relay --host=127.0.0.1 --port=9001 --health-addr=127.0.0.1:19001 & P2=$!
./relay --host=127.0.0.1 --port=9002 --health-addr=127.0.0.1:19002 & P3=$!
trap 'kill -9 $P1 $P2 $P3 2>/dev/null || true' EXIT
sleep 1
for hp in 19000 19001 19002; do curl -fsS "http://127.0.0.1:${hp}/healthz" >/dev/null; done

# Client E2E in its own venv
cd "$ROOT/client"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
# cryptography needs build toolchain sometimes; the runner has them after workflow step
pip install "cryptography>=41,<43"

# Secrets (local to CI)
[ -f secrets.json ] || python - <<'PY'
import json, secrets, pathlib
pathlib.Path("secrets.json").write_text(json.dumps({"root_secret": secrets.token_hex(32)}, indent=2))
print("secrets.json generated")
PY

CHAIN="127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002"
PAD=512
MTU=700

echo "CI selftest payload" > e2e_test.txt
python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad $PAD --mtu $MTU sendfile e2e_test.txt
python3 dbridge.py --tcp --chain "$CHAIN" --mtu $MTU forward final_obfuscated_output.bin
python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad $PAD --mtu $MTU --replay-db ../dbridge_replay.sqlite receive relay_output_3.bin

cmp -s e2e_test.txt received_output.bin
echo "[OK] CI selftest passed"
deactivate
