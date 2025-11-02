# C³ — Client-based Cryptographic Cloak (Demo)

C³ reshapes and reroutes traffic **on the client** to blunt AI-driven traffic analysis.  
This repo is a minimal demo scaffold and investor-facing overview.

## Quick Start
Run:
  chmod +x run_local.sh && ./run_local.sh

Test through relay1:
  curl -x http://127.0.0.1:15001 http://127.0.0.1:8080/

Stop:
  chmod +x stop_local.sh && ./stop_local.sh

## One-Command Demo (stub, safe anywhere)
  chmod +x demo.sh && ./demo.sh --preset low --duration 10

- Produces `artifacts/<timestamp>/summary.json`
- Prints a 6-line summary on stdout
- No binaries start yet; this is a safe placeholder while M6 is implemented

## Results (Example)

To run the full demo, use:
  chmod +x demo.sh && ./demo.sh --preset med --duration 10

After it completes, it prints a summary and writes detailed results to `summary.txt` in the artifacts directory. A sample summary looks like:

- preset=med
- duration_s=10
- req_total_baseline=100
- req_total_obfuscated=100
- baseline_p50_ms=34.23
- baseline_p95_ms=151.29
- obfuscated_p50_ms=64.29
- obfuscated_p95_ms=181.59
- baseline_bytes_in=72509
- baseline_bytes_out=72509
- obfuscated_bytes_in=69888
- obfuscated_bytes_out=69888
- status=OK
- artifacts=artifacts/&lt;timestamp&gt;


This shows how obfuscation changes latency and size distributions.

## Demo in One Command

To orchestrate the entire demo – stopping any existing run, starting the stub services, running both baseline and obfuscated simulations, writing a consolidated `summary.json` plus the usual summaries and plot, printing a concise summary and cleaning up – use the `demo_full.sh` script. For example:

## What’s Here
- **Demo harness**: `demo.sh`, `run_local.sh`, `stop_local.sh`, `start_chain.sh`, `stop_chain.sh`
- **Runtime**: `logs/`, `pids/`, `artifacts/` (git-ignored)
- **Investor docs**: `investor_box/` (executive summary only; personal planning stays off-repo)

## Status
- Scaffold validated. Next milestones: D-Bridge multi-hop scheduling (M1), demo polish & analyzer plots (M2), Android client shim (M3), obfuscation presets (M4), metrics/health endpoints (M5), one-command demo (M6), whitepaper v1.0 (M7).

## Security
Responsible disclosure: see `SECURITY.md`  
Contact: **Dog5pkPrrsents@proton.me**

## License
MIT — see `LICENSE`.

## CI
![CI](https://github.com/${GITHUB_REPOSITORY:-owner/repo}/actions/workflows/selftest.yml/badge.svg "D-Bridge CI Selftest")
