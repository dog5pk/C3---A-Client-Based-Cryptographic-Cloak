#!/usr/bin/env bash
# C3 M6: Full demo run (build → run → soak → summarise)
#
# This script orchestrates a complete run of the synthetic C3 demo.
# It stops any existing demo processes, starts the stub chain (if available),
# runs the synthetic traffic generator, produces a machine‑readable
# summary in JSON format, prints a concise human‑readable summary,
# and finally stops any services it started.
#
# It is POSIX‑compliant and assumes `demo.sh` and `analyzer.py` exist.

set -euo pipefail

# Defaults (overridable via env or flags)
PRESET="${C3_PRESET:-low}"
DURATION=10
OUT="artifacts/$(date -u +%Y%m%dT%H%M%SZ)"

# Parse flags: --preset, --duration, --out
while [ "$#" -gt 0 ]; do
    case "$1" in
        --preset)    PRESET="${2:-$PRESET}"; shift 2 ;;
        --duration)  DURATION="${2:-$DURATION}"; shift 2 ;;
        --out)       OUT="${2:-$OUT}"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

# Step 1: Stop any prior run – kill pids and run stop_chain if present
echo "[demo_full] Stopping previous run…"
if [ -d pids ]; then
    for pidfile in pids/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile"
    done
fi
[ -x ./stop_chain.sh ] && ./stop_chain.sh || true

# Step 2: Start the stub chain (if available)
echo "[demo_full] Starting chain…"
if [ -x ./start_chain.sh ]; then
    ./start_chain.sh || true
else
    echo "start_chain.sh not found; skipping chain start" >&2
fi

# Step 3: Run the synthetic traffic demo (baseline + obfuscated)
echo "[demo_full] Running synthetic demo…"
if [ -x ./demo.sh ]; then
    ./demo.sh --preset "$PRESET" --duration "$DURATION" --out "$OUT" > /dev/null
else
    echo "demo.sh not found" >&2
    exit 1
fi

# Step 4: Generate summary.json from baseline & obfuscated summaries
echo "[demo_full] Generating summary.json…"
python3 - <<'PY' "$OUT"
import json, os, sys
out_dir=sys.argv[1]
with open(os.path.join(out_dir,'baseline_summary.json'),'r',encoding='utf-8') as f: base=json.load(f)
with open(os.path.join(out_dir,'obfuscated_summary.json'),'r',encoding='utf-8') as f: obf=json.load(f)
summary={
  'preset': base.get('preset'),
  'duration_s': base.get('duration_s'),
  'req_total_baseline': base.get('req_total'),
  'req_total_obfuscated': obf.get('req_total'),
  'baseline_p50_ms': base.get('p50_latency_ms'),
  'baseline_p95_ms': base.get('p95_latency_ms'),
  'obfuscated_p50_ms': obf.get('p50_latency_ms'),
  'obfuscated_p95_ms': obf.get('p95_latency_ms'),
  'baseline_bytes_in': base.get('bytes_in'),
  'baseline_bytes_out': base.get('bytes_out'),
  'obfuscated_bytes_in': obf.get('bytes_in'),
  'obfuscated_bytes_out': obf.get('bytes_out'),
}
with open(os.path.join(out_dir,'summary.json'),'w',encoding='utf-8') as f: json.dump(summary,f,indent=2)
PY

# Step 5: Print concise summary lines and artifacts path
python3 - <<'PY' "$OUT"
import json, os, sys
out_dir=sys.argv[1]
with open(os.path.join(out_dir,'summary.json'),'r',encoding='utf-8') as f: s=json.load(f)
print(f"preset={s['preset']}")
print(f"duration_s={s['duration_s']}  req_total_baseline={s['req_total_baseline']}  req_total_obfuscated={s['req_total_obfuscated']}")
print(f"baseline_p50_ms={s['baseline_p50_ms']}  baseline_p95_ms={s['baseline_p95_ms']}")
print(f"obfuscated_p50_ms={s['obfuscated_p50_ms']}  obfuscated_p95_ms={s['obfuscated_p95_ms']}")
print(f"baseline_bytes_in={s['baseline_bytes_in']}  baseline_bytes_out={s['baseline_bytes_out']}")
print(f"obfuscated_bytes_in={s['obfuscated_bytes_in']}  obfuscated_bytes_out={s['obfuscated_bytes_out']}")
print('status=OK')
print(f'artifacts={out_dir}')
PY

# Step 6: Stop the chain to clean up
echo "[demo_full] Stopping chain…"
[ -x ./stop_chain.sh ] && ./stop_chain.sh || true
