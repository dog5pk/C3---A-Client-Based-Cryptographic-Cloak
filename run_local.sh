#!/usr/bin/env bash
# Wrapper to run the demo with sane defaults. Safe on any machine.
set -euo pipefail

# Defaults (override by exporting before call, or pass flags through)
: "${C3_PRESET:=low}"
: "${C3_DURATION:=10}"

# Pass through any flags given to this script
./demo.sh --preset "$C3_PRESET" --duration "$C3_DURATION" "$@"
