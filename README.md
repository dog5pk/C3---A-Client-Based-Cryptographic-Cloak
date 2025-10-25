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
