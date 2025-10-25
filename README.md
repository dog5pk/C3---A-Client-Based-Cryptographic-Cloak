# C³ — Client-based Cryptographic Cloak (Demo)

Local scaffold checkpoint.

Run:
  chmod +x run_local.sh && ./run_local.sh

Test through relay1:
  curl -x http://127.0.0.1:15001 http://127.0.0.1:8080/

Stop:
  chmod +x stop_local.sh && ./stop_local.sh

Repo layout:
- bin_relay1 / bin_relay2 / bin_upstream — demo binaries
- run_local.sh / stop_local.sh / start_chain.sh / stop_chain.sh — harness
- logs/ pids/ artifacts/ — runtime output (git-ignored)
