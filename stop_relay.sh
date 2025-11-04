#!/usr/bin/env bash
set -e

BIN_PATH="$HOME/dbridge/bin/relay"

PID=$(pgrep -f "$BIN_PATH" || true)

if [ -z "$PID" ]; then
  echo "[!] No running relay found."
  exit 0
fi

echo "[*] Stopping D-Bridge relay (PID $PID)..."
kill -SIGINT "$PID"

# Give it a moment to exit gracefully
sleep 2

if pgrep -f "$BIN_PATH" > /dev/null; then
  echo "[!] Relay did not shut down cleanly. Forcing stop..."
  kill -9 "$PID"
else
  echo "[✓] Relay stopped cleanly."
fi
