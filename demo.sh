#!/usr/bin/env bash
# C3 demo script
#
# This script produces baseline and obfuscated summaries of synthetic traffic
# and generates a comparison plot using analyzer.py. It can be run on any
# machine without requiring the real relays.

set -euo pipefail

# Defaults: honour C3_PRESET if set, else use "low"
PRESET="${C3_PRESET:-low}"
DURATION=10
OUT="artifacts/$(date -u +%Y%m%dT%H%M%SZ)"

# Parse command‑line flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --preset)
            PRESET="${2:-$PRESET}"
            shift 2
            ;;
        --duration)
            DURATION="${2:-$DURATION}"
            shift 2
            ;;
        --out)
            OUT="${2:-$OUT}"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done
echo "Using preset $PRESET"

# Location of presets configuration (override via PRESETS_FILE env var)
PRESETS_FILE="${PRESETS_FILE:-presets.json}"

# Ensure output and runtime directories exist
mkdir -p "$OUT" logs pids

# Use Python to generate baseline and obfuscated summaries. Pass the presets file path.
python3 - <<'PY' "$OUT" "$DURATION" "$PRESET" "$PRESETS_FILE"
import json
import sys
import os
import random
import statistics
import math

out_dir, duration_str, preset, presets_path = sys.argv[1:5]
duration = int(duration_str)
req_total = duration * 10  # simulate ~10 requests per second

def sample_baseline(n):
    sizes = []
    for _ in range(n):
        val = int(random.lognormvariate(math.log(600), 0.5))
        val = min(max(val, 64), 2000)
        sizes.append(val)
    ipd = [random.expovariate(1/50.0) for _ in range(n)]
    return sizes, ipd

def apply_obfuscation(sizes, ipd, preset_name):
    # Load preset from JSON file, fallback to defaults
    try:
        with open(presets_path, "r", encoding="utf-8") as pf:
            presets = json.load(pf)
    except Exception:
        presets = {}
    spec = presets.get(preset_name) or presets.get("low", {"buckets": [256, 512, 1024], "jitter": [5, 15]})
    buckets = spec["buckets"]
    jitter_low, jitter_high = spec["jitter"]
    new_sizes = [min(buckets, key=lambda b: abs(b - s)) for s in sizes]
    new_ipd = [max(t + random.uniform(jitter_low, jitter_high), 0.0) for t in ipd]
    return new_sizes, new_ipd

def summarize(sizes, ipd, preset_name):
    bytes_total = sum(sizes)
    p50 = round(statistics.quantiles(ipd, n=100)[49], 2) if ipd else 0.0
    p95 = round(statistics.quantiles(ipd, n=100)[94], 2) if ipd else 0.0
    return {
        "preset": preset_name,
        "duration_s": duration,
        "req_total": len(sizes),
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "bytes_in": bytes_total,
        "bytes_out": bytes_total,
        "sizes": sizes,
        "ipd_ms": [round(x, 2) for x in ipd],
    }

sizes_base, ipd_base = sample_baseline(req_total)
baseline_summary = summarize(sizes_base, ipd_base, preset)
sizes_obf, ipd_obf = apply_obfuscation(sizes_base, ipd_base, preset)
obfuscated_summary = summarize(sizes_obf, ipd_obf, preset)

os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "baseline_summary.json"), "w", encoding="utf-8") as f:
    json.dump(baseline_summary, f, indent=2)
with open(os.path.join(out_dir, "obfuscated_summary.json"), "w", encoding="utf-8") as f:
    json.dump(obfuscated_summary, f, indent=2)
PY

# Produce summary and plot using analyzer.py
python3 analyzer.py \
  --baseline "$OUT/baseline_summary.json" \
  --obfuscated "$OUT/obfuscated_summary.json" \
  --out "$OUT" > /dev/null

# Display summary and artifacts path
cat "$OUT/summary.txt"
echo "artifacts=$OUT"


