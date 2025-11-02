---

## 1) What D-Bridge Is

A **multi-hop TCP relay chain** with **per-hop authenticated encryption** and traffic shaping:

- **Client:** `client/dbridge.py`
  - **AEAD per hop**: ChaCha20-Poly1305
  - **Key schedule**: HKDF-SHA256 (salted; hop-scoped `info`)
  - **Framing**: Versioned header (`DB1`), flags, 8-byte `msg_id`, original length, padded payload
  - **Padding**: fixed multiple (default `--pad 512`)
  - **Fragmentation**: `--mtu` to break payload across application-level chunks
  - **Anti-replay**: SQLite db (`--replay-db`) keyed by `msg_id`
  - **Nonce audit**: optional CSV (`--nonce-log`)
  - **Ops**: chain loaded via `--chain` or config; forwards/receives over TCP with replay-safe, layered deobfuscation
  - **CLI**: `send`, `sendfile`, `forward`, `receive`

- **Relays:** `relays/relay.go`
  - Stateless, **length-prefixed** echo
  - **Hardened I/O**: read/write timeouts, max payload, TCP keepalive, connection cap
  - **Health endpoint** `/healthz` on per-instance localhost port (1<p>)
  - Deployed as **systemd** instances: `dbridge-relay@9000/9001/9002`

---

## 2) Security Model (Why It’s Hard To Break)

- **Confidentiality + Integrity:** Each hop wraps payload in **ChaCha20-Poly1305** with independent key material.
- **Key Separation:** HKDF derives **per-hop keys** using hop address as `info`; compromise of one hop doesn’t expose others.
- **Replay Resistance:** Persistent **SQLite replay DB** rejects repeated `msg_id`s (`--replay-db`).
- **Traffic Obfuscation:** Padding to fixed multiples (`--pad`) + optional fragmentation (`--mtu`) distort packet size profiles.
- **Protocol Versioning:** `DB1` + flag byte allows safe evolution.
- **Operational Isolation:** Relays run as a **dedicated user**, sandboxed by **systemd** (no new privs, private tmp/dev, strict FS, syscall filter, no caps).
- **Exposure Control:** Relays bind to **127.0.0.1** only; **UFW** explicitly denies 9000–9002 from non-localhost.
- **Health/Observability:** `/healthz` shows liveness and minimal counters.

---

## 3) What’s Installed (Files & Layout)
dbridge/ ├── client/ │ ├── dbridge.py # Hardened client (AEAD, HKDF, anti-replay, MTU, nonce audit) │ ├── analyze.py # Optional traffic analyzer (histograms; optional use) │ ├── e2e_test.txt # Created at test time │ └── (generated at runtime) final_obfuscated_output.bin, relay_output_*.bin, received_output.bin ├── relays/ │ ├── relay.go # Hardened relay (timeouts, caps, healthz) │ └── relay # Built binary (ignored in VCS) ├── scripts/ │ ├── check_relays.sh # Health sweep over chain │ └── systemd_enable_chain.sh # Helper to enable instances ├── .github/workflows/e2e.yml # (optional) CI to run E2E on push/PR ├── Makefile # (optional) One-command E2E runner └── .gitignore # Prevents secrets/binaries from being committed
**Systemd unit (installed):** `/etc/systemd/system/dbridge-relay@.service`  
ExecStart:
/opt/dbridge/relays/relay --host=127.0.0.1 --port=%i --health-addr=127.0.0.1:1%i --max-bytes=67108864 --read-timeout=60s --write-timeout=60s --keepalive=30s --max-conns=4096
`
with hardening: `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `CapabilityBoundingSet=`, `RestrictAddressFamilies=AF_INET AF_INET6`, `SystemCallFilter=@system-service`, etc.

**Firewall (UFW) rules:**  
- `ALLOW IN` on `lo` (loopback)  
- `DENY IN` tcp `9000, 9001, 9002` (v4+v6)

---

## 4) Acceptance Tests (Reproducible)

> Run exactly these. Expected: health OK, listeners on 127.0.0.1, and **identical hashes** for input/output.

### 4.1 Health & Listeners
bash # Ports bound to loopback only ss -ltnp | grep -E ':9000|:9001|:9002' # Health endpoints (should print "ok ...") for p in 9000 9001 9002; do hp=$((10000+p)); curl -fsS "http://127.0.0.1:${hp}/healthz" && echo " OK :$p"; done
`

### 4.2 End-to-End (send → forward → receive → hash)
bash cd ~/dbridge/client . .venv/bin/activate 2>/dev/null || { python3 -m venv .venv && . .venv/bin/activate; pip install -q cryptography; } # Generate a fresh root secret (local only, ignored by VCS) python3 - <<'PY' import json,secrets,pathlib pathlib.Path("secrets.json").write_text(json.dumps({"root_secret": secrets.token_hex(32)}, indent=2)) print("secrets.json generated") PY echo "release verification" > e2e_test.txt CHAIN="127.0.0.1:9000,127.0.0.1:9001,127.0.0.1:9002" python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad 512 --mtu 700 sendfile e2e_test.txt python3 dbridge.py --tcp --chain "$CHAIN" --mtu 700 forward final_obfuscated_output.bin python3 dbridge.py --tcp --chain "$CHAIN" --secrets secrets.json --pad 512 --replay-db ../dbridge_replay.sqlite --mtu 700 receive relay_output_3.bin sha256sum e2e_test.txt received_output.bin # EXPECT: the two hashes are identical
**Pass criteria:**

* Health checks OK for all three relays
* `ss` shows `127.0.0.1:900{0,1,2}` (not `*`)
* `sha256sum` shows **identical** hashes for `e2e_test.txt` and `received_output.bin`

---

## 5) Operational Hardening Summary

* **Systemd lifecycle**: auto-restart (`Restart=always`), fast rebind, sandboxing
* **Least privilege**: dedicated `dbridge` user; `NoNewPrivileges`; zero capabilities
* **Network scope**: loopback bind only; UFW denies external access to relay ports
* **Resource control**: connection cap; max payload; read/write timeouts; keepalive
* **Health monitoring**: `/healthz` per instance; `scripts/check_relays.sh`
* **Crypto hygiene**: per-hop keys via **HKDF**; **AEAD** encryption; replay DB; nonce audit logs
* **Safe defaults**: versioned framing; padding; MTU fragmentation

---

## 6) Operational Runbook (Minimal)

* **Start/enable relays** (already enabled):
bash for p in 9000 9001 9002; do sudo systemctl enable --now dbridge-relay@"$p".service; done
* **Inspect relays**:
bash systemctl --no-pager status dbridge-relay@9000.service journalctl --no-pager -u dbridge-relay@9000.service -n 100
* **Rotate root secret** (invalidates old messages):
bash cd ~/dbridge/client python3 - <<'PY' import json,secrets,pathlib pathlib.Path("secrets.json").write_text(json.dumps({"root_secret": secrets.token_hex(32)}, indent=2)) print("root secret rotated") PY
---

## 7) Compliance & Release Hygiene

* **No secrets in VCS** (`client/secrets.json` is git-ignored)
* **Binaries ignored** (`relays/relay`, `*.bin`, `*.sqlite`, logs)
* **Local artifact**: `dbridge_release.tar.gz` can be built without secrets/venv/binaries
* **Optional CI**: `.github/workflows/e2e.yml` runs the E2E on push/PR (if present)

---

## 8) Known Limits (Transparent & Intentional)

* Relays are **stateless** echo; they don’t inspect or route content—by design.
* Deployment model here is **localhost chain**; binding to external interfaces requires reviewing firewall + threat model.
* Side-channel resistance (timing/size) is improved with padding/fragmentation, but not a substitute for full cover traffic.

---
