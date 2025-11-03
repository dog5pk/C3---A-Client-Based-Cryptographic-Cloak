#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT="$ROOT/client"
CHAIN="${CHAIN:-127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002}"

# Health (require green)
"$ROOT/scripts/check_health.sh" "$CHAIN" >/dev/null || {
  echo "[info] starting relays via systemd ..."
  for p in 9000 9001 9002; do sudo systemctl enable --now dbridge-relay@"$p".service >/dev/null || true; done
  sleep 1
  "$ROOT/scripts/check_health.sh" "$CHAIN"
}

# Python env
cd "$CLIENT"
python3 -m venv .venv >/dev/null 2>&1 || true
. .venv/bin/activate
pip install -q cryptography

# Fresh local secret (git-ignored)
python3 - <<'PY'
import json,secrets,pathlib
pathlib.Path("secrets.json").write_text(json.dumps({"root_secret": secrets.token_hex(32)}, indent=2))
print("secrets.json generated")
PY

# Payload & pipeline
echo "dbridge selftest" > selftest.txt
python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad 512 --mtu 700 sendfile selftest.txt
python3 dbridge.py --tcp --chain "$CHAIN" --mtu 700 forward final_obfuscated_output.bin
python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad 512 --replay-db ../dbridge_replay.sqlite --mtu 700 receive relay_output_3.bin

# Verify (diff fails on mismatch)
diff -q selftest.txt received_output.bin && echo "[OK] selftest passed ✅"
