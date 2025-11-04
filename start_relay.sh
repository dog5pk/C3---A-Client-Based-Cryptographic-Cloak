#!/usr/bin/env bash
set -e

BIN_PATH="$HOME/dbridge/bin/relay"
LOG_PATH="$HOME/dbridge/relay.log"
HEALTH_URL="http://127.0.0.1:9090/health"

echo "[+] Starting D-Bridge relay..."

# Ensure binary exists
if [ ! -x "$BIN_PATH" ]; then
  echo "[!] Relay binary not found or not executable: $BIN_PATH"
  exit 1
fi

# Start in background safely (disown to prevent WSL hang)
nohup "$BIN_PATH" > "$LOG_PATH" 2>&1 &
PID=$!
disown

sleep 2

# Verify with curl
if curl -s --max-time 2 "$HEALTH_URL" | grep -q "ok"; then
  echo "[✓] Relay running in background (PID $PID)"
else
  echo "[!] Relay may not have started correctly. Check $LOG_PATH"
fi
