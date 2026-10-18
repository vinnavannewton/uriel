---
title: "Bridge protocols — crossing v1 and head-on maneuvers v2"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Bridge protocols — crossing v1 and head-on maneuvers v2

## Remaining Uriel contract additions

The crossing prototype remains version 1. A bounded head-on maneuver contract is now implemented as version 2 on a separate endpoint, documented below. The ML-worker batch interface, prediction validity/model version, history/advice features and arrival-label records remain planned; v2 does not implement the complete Uriel PRD.

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

## Head-on maneuver v2 — implemented local slice

Endpoint: `/ws/headon`, sharing optional `ARC_TOKEN` upgrade authentication and a 256 KiB message limit. Types live in [headon_protocol.rs](../../../../src/headon_protocol.rs); transport/ownership is [headon_bridge.rs](../../../../src/headon_bridge.rs), planning and guards are [headon.rs](../../../../src/headon.rs), and the client is [headon_client.py](../../../../scripts/headon_client.py). The existing `/ws/bridge` and examples remain version 1; this is not an implicit v1 upgrade.

| Message | Required behavior |
|---|---|
| `hello` → `hello_ack` | Version 2, world/epoch/bridge identity, scenario `headon-grid-v2`, map `smallgrid`, capabilities `path_origin_xy_v2` and `sim_pause_fallback`; Rust returns a fresh session |
| `headon_state` → `maneuver_plan` | Complete set of exactly `thePlayer` and `uriel_blue`, strictly increasing frame sequence, simulator time, measured 3D origin/velocity/forward/up, per-car sensor time, dimensions/enclosing radius and damage |
| `maneuver_ack` → `ack_result` | Exact session/epoch, current plan sequence, stable maneuver ID, car ID and `accepted`/`rejected`; acceptance is a controller/API result, not an achieved-motion claim |

Plan envelopes echo the exact source frame and identity, carry increasing `plan_seq`, a stable `maneuver_id`, scenario ID, issued/expiry simulation times, 500 ms wall freshness, status/reason and a complete `recommendations` array. Each car recommendation contains `speed_cap_mps`, action/reason and a complete `path_xy_m` polyline **relative to the measured vehicle origin in world metre coordinates**. Python converts origin paths to BeamNG front-point paths before calling the AI. Initial target speed is 30 km/h; active geometry and speeds stay fixed for this bounded maneuver.

Phases: `prepare` keeps physics paused while both paths are applied once; only both accepted acknowledgements permit `execute`. Python then requests a fresh execution plan before unpausing. Later state frames renew permission for the same paths, not a new path start. `pause` latches after a rejected acknowledgement, expired telemetry, nonadvancing execution simulation/sensor time, damage, deviation or other guarded motion. `complete` requires both accepted paths plus measured passing and return positions, then Python pauses physics. Equal timestamps are allowed while preparation is paused, but cannot renew execution.

Rust rejects wrong identities, duplicate/missing cars, old frames, decreasing time, invalid/nonfinite geometry, excessive speed, misaligned/moving/damaged initial cars, stale acknowledgements and wrong maneuver IDs. The initial fixed scene is red at `(0,55)` facing -Y and blue at `(0,-55)` facing +Y. The server registers one active bridge per v2 world; reconnect requires a new reset epoch and revalidating those starts. Preparation/idle read timeout is five seconds, execution read timeout 750 ms, send timeout 250 ms; missing data cannot grant a new plan. Server world snapshots share the read-only dashboard APIs and survive disconnect only in memory.

Python checks response identity/frame/sequence/finite paths/time, includes both cars, enforces the prepared starts/endpoints, rejects changed geometry or active speeds, and applies Rust's initial speed caps. During execution the receive timeout is bounded by the **previous** lease with 100 ms reserved for requesting a simulator pause; late replies cannot conceal an expired lease. This remains a best-effort desktop control loop: blocking simulator calls, OS scheduling or Python death have no simulator-side watchdog. A simulator pause is not a verified physical braking maneuver. No obstacle perception, ML or LinuxONE execution is established.

Examples: [headon-hello.json](../../../../examples/headon-hello.json), [headon-state.json](../../../../examples/headon-state.json), [headon-plan.json](../../../../examples/headon-plan.json). The state/plan session placeholders must be replaced by the actual hello session. See [[operations]] for verified runs and [[recording]] for the two correlated recording streams.

## Collision observation HTTP contract

`POST /api/collision/telemetry` is display-only and returns HTTP 204, never a driving plan. With `ARC_TOKEN` configured it requires the same Bearer header as the bridges. Fields: `world_id` (a valid ID beginning `headon-collision-` or `headon-dodge-`), increasing `frame_seq`, nondecreasing `sim_time_s`, `finished`, optional `mode` (`collision` by default, or `dodge`), and exactly the two registered cars in the existing v2 `VehicleState` shape. Rust validates identities, dimensions and finite measurements; rejects duplicate/out-of-order frames and a competing recently active producer; retains one latest collision world. Snapshots use scenario `collision-grid-observer-v1`, `observation_only=true`, `observation_mode` reflecting the sender’s mode, `last_plan=null` and a fixed grid extent from the first positions. These are read through the ordinary world APIs; the protocol-version field on the snapshot selects the existing XY head-on rendering and does not grant a maneuver-v2 execution lease. Completion preserves positions as disconnected; missing frames become stale.

## Conflict evaluator HTTP contract (new, standalone)

`POST /api/conflicts/evaluate` accepts one bounded assessment frame with `frame_seq`, `sim_time_s`, validated stop-estimator thresholds, observations, caller-supplied prior reservations and route-conflict pairs. An observation includes identity/route, speed and optional acceleration, front-to-entry and rear-clearance distances, predicted times, waiting age, dimensions, telemetry age/uncertainty, occupancy/clearance facts and an optional braking deceleration explicitly marked as validated. It returns the state-aware actions, retained/allocated reservations, phase, safe-hold flag and independent monitor verdict for each action. The route-conflict matrix is caller-supplied; the endpoint does not infer intersection topology from the map.

`POST /api/conflicts/command-result` accepts a command record and the observed speed. It preserves separate acknowledgement and verified-response fields and appends the result to the event log. It does not send a command or authenticate it against a prior plan/reservation. Both endpoints use the configured Bearer token when `ARC_TOKEN` is set. See [[conflict-resolution]] and the example request `examples/conflict-evaluate.json`. This API is currently not wired into `/ws/bridge` or any BeamNG controller.

## Sources

- [[sources]]: S1 PRD section 8; S3 code inspection.
- [protocol.rs](../../../../src/protocol.rs), [hello sample](../../../../examples/hello.json), [state sample](../../../../examples/state_batch.json).
- Related: [[architecture]], [[implementation-status]].
- [[sources]] S9: current v2 source and correlated local run evidence.
