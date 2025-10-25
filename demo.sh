#!/usr/bin/env bash
# C3 demo stub — safe, no dependencies. Progress toward M6.
set -euo pipefail

# Defaults (override via flags)
PRESET="low"
DURATION=10
OUT="artifacts/$(date -u +%Y%m%dT%H%M%SZ)"

# Parse flags: --preset X, --duration N, --out PATH
while [ $# -gt 0 ]; do
  case "$1" in
    --preset) PRESET="${2:-low}"; shift 2 ;;
    --duration) DURATION="${2:-10}"; shift 2 ;;
    --out) OUT="${2:-$OUT}"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

mkdir -p "$OUT"
mkdir -p logs pids

# Placeholder “run”: just sleep to simulate soak
START_TS=$(date -u +%s)
sleep 1
REQS=$((DURATION * 10))   # pretend 10 req/s
P50=30                    # ms (placeholder)
P95=85                    # ms (placeholder)
BIN=123456                # bytes_in (placeholder)
BOUT=123789               # bytes_out (placeholder)

# Write stub summary
cat > "$OUT/summary.json" <<JSON
{
  "preset": "$PRESET",
  "duration_s": $DURATION,
  "req_total": $REQS,
  "p50_latency_ms": $P50,
  "p95_latency_ms": $P95,
  "bytes_in": $BIN,
  "bytes_out": $BOUT,
  "started_at": $START_TS
}
JSON

# Terse console summary (6 lines max, per M6)
echo "C3 demo (stub) complete"
echo "preset=$PRESET  duration_s=$DURATION"
echo "req_total=$REQS  p50_ms=$P50  p95_ms=$P95"
echo "bytes_in=$BIN  bytes_out=$BOUT"
echo "artifacts=$OUT"
echo "status=OK"
