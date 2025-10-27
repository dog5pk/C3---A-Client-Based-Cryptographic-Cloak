# C³ Pilot Brief (2 Weeks)
**Goal**: Quantify privacy gain vs. performance cost on your traffic.

**Scope**
- Integrate C³ SDK at socket/transport boundary in a test build.
- Run A/B traffic: baseline vs. C³.
- Collect on-device logs; run fingerprint/linkability tests.

**Success Criteria**
1) Linkability/error-rate improvement vs. baseline.
2) Latency/bandwidth/battery within budgets.
3) Stability over 7 days.

**Deliverables**
- Report with linkability metrics (and KS/JS divergences), perf overhead, and config used.
- Recommendations for productionization.

**Privacy/Legal**
- Endpoint-side shaping; no content decryption or access-control bypass.
