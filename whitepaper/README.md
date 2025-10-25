# C³ Whitepaper — v1.0 (skeleton)

**Working title:** Client-Based Traffic Morphing and Offline Relay for Privacy-Preserving Network Communication

## 1) Abstract
150 words max. Plain language. What C³ does, why now, what’s new.

## 2) Motivation & Threat Model
Adversaries: traffic analysis, censors, metadata harvesters.  
Out of scope: endpoint compromise, user opsec failure.

## 3) System Overview
Client-first layer; sits above apps and below the network.  
Components: client shim, relay1, relay2, upstream; presets.

## 4) Protocol Mechanics
Timing jitter buckets, size morphing, multi-hop (D-Bridge) scheduling, offline peer relay (store-and-forward).

## 5) Security Considerations
Fingerprinting, correlation, active probing; failure modes; degrade-gracefully behavior.

## 6) Performance & Tradeoffs
Latency per preset; bandwidth overhead; tunables and defaults.

## 7) Implementation Status
What exists now; roadmap to MVP; links to demo artifacts.

## 8) Ethics & Disclosure
Dual-use acknowledgement; see `SECURITY.md` for responsible disclosure.

## Appendix
Config examples; metrics plots; references (to be added in `references.bib`).
