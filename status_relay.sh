#!/usr/bin/env bash
set -e

BIN_PATH="$HOME/dbridge/bin/relay"
LOG_PATH="$HOME/dbridge/relay.log"

PID=$(pgrep -f "$BIN_PATH" || true)

if [ -z "$PID" ]; then
  echo "[!] Relay is not running."
else
  echo "[✓] Relay running with PID $PID"
fi

if [ -f "$LOG_PATH" ]; then
  echo
  echo "--- Last 5 log lines ---"
  tail -n 5 "$LOG_PATH"
fi
