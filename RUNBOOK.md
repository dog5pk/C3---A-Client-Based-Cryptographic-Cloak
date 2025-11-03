# D-Bridge RUNBOOK (V01.01)

## Ship Ritual (single command)
    ./scripts/ship.sh

## Manual Steps
    make selftest
    make pack
    make verify

## Health & Relays
    ./scripts/check_health.sh
    ./scripts/restart_relays.sh

## Secrets
    ./scripts/rotate_secret.sh   # rotates root_secret; old messages become unreadable

## Cleanup
    ./scripts/clean_demo.sh

Notes:
- Flags must come BEFORE the subcommand in dbridge.py.
- Relays are localhost-only by default (systemd + UFW).
- Nothing is pushed anywhere by these scripts; all operations are local.
