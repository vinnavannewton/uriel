---
title: "Protocol version 1 — current code"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Protocol version 1 — current code

## Uriel contract additions remain planned

S5 describes the identity/timing contract as a design, while this workspace has the earlier prototype message types documented below. Preserve that distinction. A new ML-worker batch interface must return prediction validity/status and model version with bounded timeouts; it is not defined in the current bridge schema. History/advice features and prediction/arrival records need versioned definitions.

The hard-coded prototype 0.5-second advice horizon is provisional, not a calibrated approved control limit. Server/laptop monotonic times must remain separate; pauses cannot retain stale permission. Source: [[sources]] S5 sections 6–10. Related: [[ml-arrival-prediction]], [[context-reconciliation]].

The bridge connects to `/ws/bridge`, optionally sending `Authorization: Bearer …` when `ARC_TOKEN` is configured. Message size is capped at 256 KiB. A connection must send `hello` before world messages.

| Incoming type | Purpose |
|---|---|
| `hello` | Version, world, epoch, scenario and bridge identity; returns server session |
| `state_batch` | Complete vehicle snapshot, increasing frame sequence and simulation time |
| `applied_result` | Applied/rejected/overridden advice, cap and reason |
| `vehicle_removed` | Removal with reason exactly `confirmed_clear` |

Outputs are `hello_ack`, `recommendation_batch` and `error`. Advice carries frame/plan numbers, epoch/session, cap/action/reason, optional reservation/window and 0.5 simulation-second expiry. The hello response also declares 0.5-second wall freshness; the bridge must enforce its own response age.

Units: metres, metres/second, radians, simulation seconds. World IDs isolate physical simulations. A new session is issued on each reconnect; a new epoch is required after simulator resets. Reset currently means closing and handshaking with a new epoch; there is no reset message.

Current validation rejects unsupported version/scenario, duplicate IDs, unknown routes, invalid finite/bounded numerical fields, more than 100 vehicles per batch, non-increasing frame sequence and decreasing simulator time. Equal simulator timestamps are allowed. Only some rejections increment per-world counters.

No initial registered vehicle list or expected-vehicle completeness check exists. The bridge's full-snapshot contract is not comprehensively enforced. Unknown JSON fields are not explicitly rejected. No handshake timeout, total-world limit or accepted-update-rate limiter is configured.

## Sources

- [[sources]]: S1 PRD section 8; S3 code inspection.
- [protocol.rs](../../../../src/protocol.rs), [hello sample](../../../../examples/hello.json), [state sample](../../../../examples/state_batch.json).
- Related: [[architecture]], [[implementation-status]].
