#!/usr/bin/env bash
# C3 demo script
#
# This script produces baseline and obfuscated summaries of synthetic traffic
# and generates a comparison plot using analyzer.py. It can be run on any
# machine without requiring the real relays.

set -euo pipefail

# Defaults
PRESET="low"
DURATION=10
# Default output directory uses UTC timestamp
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

# Ensure output and runtime directories exist
mkdir -p "$OUT" logs pids

# Use Python to generate baseline and obfuscated summaries
python3 - <<'PY' "$OUT" "$DURATION" "$PRESET"
import json
import sys
import os
import random
import statistics
import math

out_dir, duration_str, preset = sys.argv[1:4]
duration = int(duration_str)
# We'll simulate approx 10 requests per second
req_total = duration * 10

def sample_baseline(n):
    # Baseline packet sizes: lognormal distribution around 600 bytes
    # Lognormal ensures positive values and skew typical of network traffic
    # We clamp values to a minimum of 64 bytes and maximum of 2000 bytes
    sizes = []
    for _ in range(n):
        # generate lognormal with mean log(600) and sigma 0.5
        val = int(random.lognormvariate(math.log(600), 0.5))
        val = min(max(val, 64), 2000)
        sizes.append(val)
    # Inter‑packet delays: exponential with mean 50ms
    ipd = [random.expovariate(1/50.0) for _ in range(n)]
    return sizes, ipd

def apply_obfuscation(sizes, ipd, preset_name):
    # Define buckets and jitter ranges per preset
    presets = {
        'low':    {'buckets': [256, 512, 1024], 'jitter': (5, 15)},
        'med':    {'buckets': [384, 768, 1536], 'jitter': (15, 40)},
        'high':   {'buckets': [512, 1024, 2048], 'jitter': (40, 90)},
    }
    spec = presets.get(preset_name, presets['low'])
    buckets = spec['buckets']
    jitter_low, jitter_high = spec['jitter']
    # For each size, map to nearest bucket
    new_sizes = []
    for s in sizes:
        nearest = min(buckets, key=lambda b: abs(b - s))
        new_sizes.append(nearest)
    # Apply jitter to IPDs (ms)
    new_ipd = []
    for t in ipd:
        jitter = random.uniform(jitter_low, jitter_high)
        new = max(t + jitter, 0.0)
        new_ipd.append(new)
    return new_sizes, new_ipd

def summarize(sizes, ipd, preset_name):
    # Compute bytes_in/out as sum of packet sizes (in/out symmetrical here)
    bytes_total = sum(sizes)
    # Calculate p50 and p95 latency (IPD) in ms
    p50 = round(statistics.quantiles(ipd, n=100)[49], 2) if ipd else 0.0
    p95 = round(statistics.quantiles(ipd, n=100)[94], 2) if ipd else 0.0
    return {
        'preset': preset_name,
        'duration_s': duration,
        'req_total': len(sizes),
        'p50_latency_ms': p50,
        'p95_latency_ms': p95,
        'bytes_in': bytes_total,
        'bytes_out': bytes_total,
        'sizes': sizes,
        'ipd_ms': [round(x, 2) for x in ipd],
    }

# Generate baseline
sizes_base, ipd_base = sample_baseline(req_total)
baseline_summary = summarize(sizes_base, ipd_base, preset)
# Generate obfuscated based on baseline sizes/ipds
sizes_obf, ipd_obf = apply_obfuscation(sizes_base, ipd_base, preset)
obfuscated_summary = summarize(sizes_obf, ipd_obf, preset)

# Write summaries
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, 'baseline_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(baseline_summary, f, indent=2)
with open(os.path.join(out_dir, 'obfuscated_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(obfuscated_summary, f, indent=2)
PY

# Invoke analyzer to produce summary.txt and plot.png. Suppress its stdout to avoid
# duplicate summary lines; we'll print the summary ourselves.
python3 analyzer.py \
  --baseline "$OUT/baseline_summary.json" \
  --obfuscated "$OUT/obfuscated_summary.json" \
  --out "$OUT" > /dev/null

# Print concise summary and path to artifacts
cat "$OUT/summary.txt"
echo "artifacts=$OUT"

