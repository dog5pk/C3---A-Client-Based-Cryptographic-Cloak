#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 analyze.py --baseline logs/baseline.csv --obfuscate logs/obfuscate.csv --outdir plots --summary summary.json
echo "Artifacts written to plots/*.png and summary.json"
