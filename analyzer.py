#!/usr/bin/env python3
# C3 analyzer stub — reads the latest artifacts/<ts>/summary.json and prints a short report.
import os, json, glob, sys

ARTIFACTS = "artifacts"

def find_latest_summary():
    if not os.path.isdir(ARTIFACTS):
        return None
    runs = sorted([d for d in glob.glob(os.path.join(ARTIFACTS, "*")) if os.path.isdir(d)], reverse=True)
    for run in runs:
        p = os.path.join(run, "summary.json")
        if os.path.isfile(p):
            return p
    return None

def main(path_arg=None):
    path = path_arg or find_latest_summary()
    if not path or not os.path.isfile(path):
        print("No summary.json found. Run:  chmod +x demo.sh && ./demo.sh")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        s = json.load(f)
    # Minimal, friendly output (6-ish lines)
    print("C3 analyzer (stub)")
    print(f"summary: {path}")
    print(f"preset={s.get('preset')}")
    print(f"duration_s={s.get('duration_s')}  req_total={s.get('req_total')}")
    print(f"p50_ms={s.get('p50_latency_ms')}  p95_ms={s.get('p95_latency_ms')}")
    print(f"bytes_in={s.get('bytes_in')}  bytes_out={s.get('bytes_out')}")
    print("status=OK")

if __name__ == "__main__":
    # optional arg: path to a specific summary.json
    main(sys.argv[1] if len(sys.argv) > 1 else None)
