# D-Bridge V01.01 — Hardened Release Notes

## Summary
Production-hardened multi-hop TCP relay chain with layered AEAD obfuscation, per-hop HKDF keys, replay protection, nonce audit, MTU fragmentation, and a reproducible end-to-end self-test.

## What’s New
- **Client (`client/dbridge.py`)**
  - ChaCha20-Poly1305 per hop; keys via HKDF-SHA256 (`info = "host:port"`).
  - Versioned framing (`DB1`), flags, `msg_id`, original length, padding.
  - `--pad` (fixed multiple) and `--mtu` (app-layer fragmentation).
  - `--replay-db` SQLite store; `--nonce-log` CSV audit.
  - Subcommands: `send`, `sendfile`, `forward`, `receive`.
- **Relays (`relays/relay.go`)**
  - Length-prefixed echo, read/write timeouts, keepalive, max-bytes, max-conns.
  - `/healthz` (localhost) per instance (mapped 1<p>).
  - systemd units `dbridge-relay@{9000,9001,9002}` with strong sandboxing.
- **Ops hardening**
  - Relays bind `127.0.0.1`; UFW denies 9000–9002 from non-localhost.
  - Helper scripts: `scripts/check_health.sh`, `scripts/selftest.sh`, `scripts/pack_release.sh`.
  - Self-contained demos: `scripts/demo_systemd.sh`, `scripts/demo_spawn.sh`.

## Quickstart (Local Demo)
    ./scripts/demo_systemd.sh
    # or
    ./scripts/demo_spawn.sh

## Self-Test (hash equality)
    make selftest

## Pack a Clean Release Artifact
    make pack
    # outputs: dbridge_release_V01.01.tar.gz  and  dbridge_release_V01.01.tar.gz.sha256

## Security Notes
- No secrets in VCS; generate locally:
    ./scripts/rotate_secret.sh
- systemd hardening: `NoNewPrivileges`, `ProtectSystem=strict`, `CapabilityBoundingSet=`, `PrivateTmp`, syscall filter `@system-service`.
- Replay defense via SQLite (`--replay-db`).
- Default chain is localhost-only; exposing relays externally requires firewall rules and a separate threat model.

## Health & Operations
    ./scripts/check_health.sh
    ./scripts/restart_relays.sh

## Troubleshooting
- Pager stuck → press `q` or add `--no-pager`.
- Busy port → `sudo lsof -i :9000` then kill PID and restart unit.
- Argparse error → place flags **before** the subcommand.
- Hash mismatch → `./scripts/clean_demo.sh` then rerun selftest.

## Verification
    make selftest && make pack && sha256sum -c dbridge_release_V01.01.tar.gz.sha256
You should see selftest **OK** and checksum **OK**.
