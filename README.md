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

## What’s Here
- **Demo harness**: `run_local.sh`, `stop_local.sh`, `start_chain.sh`, `stop_chain.sh`
- **Binaries**: `bin_relay1`, `bin_relay2`, `bin_upstream` (used by the harness)
- **Runtime**: `logs/`, `pids/`, `artifacts/` (git-ignored)
- **Investor docs**: `investor_box/` (executive summary only; no private planning files)

## Status
- Local scaffold validated. Next milestones: D-Bridge multi-hop scheduling, mobile client shim, obfuscation presets, metrics dashboard.

## Security
Responsible disclosure policy: see `SECURITY.md`.  
Contact: **Dog5pkPrrsents@proton.me**

## License
MIT — see `LICENSE`.
