---
title: "Implementation status and evidence"
project: IBM-Uriel
updated: 2026-10-17
tags: [ibm, uriel]
---

# Implementation status and evidence

Current status: **historical Arc Angel crossing prototype plus an implemented, locally integrated two-car Grid Plane head-on avoidance slice**. The new slice uses Rust-authoritative paths and a Python BeamNG bridge. The offline arrival/clearance ML pilot is trained and evaluated; full Uriel functionality, live ML integration, obstacle handling, remote live-controller acceptance and broad acceptance remain unverified. The basic LinuxONE Rust service is now running; see its bounded deployment evidence below. Event/source-history distinctions are recorded separately in [[context-reconciliation]] and [[event-preparation]].

The table inventories current code and the bounded head-on addition; it does not certify event eligibility. Historical checks and new simulator evidence are distinguished below.

| Area | Current state |
|---|---|
| HTTP service and browser template | Implemented |
| JSON bridge protocol, owner/session/epoch identity | Implemented with lifecycle gaps |
| Frame and vehicle validation | Implemented subset |
| Per-world state and bounded blocking computation | Implemented; four global permits |
| Latest pending frame coalescing | Implemented |
| Route projection, reservations and headway | Simplified implementation; static concerns in [[coordination]] |
| Advice simulation expiry | Present in output |
| Server wall-age checks at plan emission | Legacy v1 gap remains; v2 checks telemetry lease/progress and Python enforces response/previous-lease age |
| Dashboard | HTTP polling, read-only; head-on uses a proportional 10 m grid map and smoothly interpolates minimal red/blue car icons between advancing telemetry frames; route-free collision views are regression-tested; animated preview is synthetic and labelled |
| Detailed recording | Rust JSONL and head-on telemetry implemented with reliability/metadata gaps; seeded six-vehicle crossing recorder also present. Its native accelerated sampling is capped by BeamNG physics/frame quantum; graphics FPS remains 60; recorder supports native AI aggression configuration and records BeamNG mode |
| Python BeamNG bridge and calibrated control | `scripts/beamng_headon.py` uses Rust maneuver-v2 by default; explicit standalone avoidance baseline retained; `scripts/beamng_headon_collision.py` now defaults to a Python-planned cooperative dodge with display-only telemetry to port 3001; its historical collision mode was replaced at user request. It does not request Rust control plans. The converted runner has not yet had a live trial. User runs exposed paused sensor readback, missing physics resume and a DCT selector error (`gear=1` selects Park). The collision runner now selects Drive from the actual gearbox type; all 24 Python tests pass. User run `headon-collision-a5953f0c73` subsequently recorded damage-threshold impact; no general collision acceptance is established. No general calibrated/emergency controller |
| Standalone crossing collection | `connect_beamng.py`, `collect_crossing_trials.py`, `collect_traffic_trials.py`, and `scripts/fresh_experiment.py` are preserved from teammate commit `d5038e6`; these do not connect to the Rust coordinator |
| Real West Coast USA scenario | Not configured |
| Physical/fault/load acceptance | Bounded local head-on passes demonstrated; teammate recorded Small Grid, West Coast and seeded six-vehicle crossing baselines. General closed-loop, fault/load and obstacle acceptance remain unverified |
| Ubuntu/LinuxONE deployment | SSH/Ubuntu/s390x verified; 21 remote Python tests passed; native release service running and `/health` returned `ok`; latest dashboard rebuilt and served. Live remote BeamNG pass unverified because the measured SSH latency exceeds the controller's response window |
| Arrival-time ML, dataset labels and evaluation | Offline `HistGradientBoostingRegressor` pilot in `scripts/train_arrival.py` rebuilds entry/clearance labels from spawn-OOBB telemetry, filters damaged/deviated targets, groups repeated seeds/configurations, and evaluates against distance/speed. The 2026-10-17 test set beat that baseline on moving rows; it contains only two clearance and three entry groups. See [[ml-arrival-prediction]] and local run evidence. No live inference, Rust integration or broad generalization is established |
| Python inference worker on LinuxONE | Recommended design; not implemented. The local offline estimators have no serving contract or live consumer |
| Mandatory labs / event readiness | Required according to S5; completion unverified |

Both standalone crossing collectors and head-on controllers share a BeamNG instance when pointed at it; run one scenario owner at a time. The teammate crossing defaults use port 25252 and ETK subjects; head-on defaults use port 64256 and matched Vivaces. Baseline crossing collection is distinct from Rust-integrated head-on avoidance.

## Current planning update

The latest PRD expands requirements to 3D state, richer scenarios and arrival/clearance ML; see [[latest-prd-context]]. The existing prototype remains limited as inventoried above. Team ownership and the new repo-local `uriel` skill are now recorded in [[team-workflow]]. The user reports reuse is permitted, superseding the prior conversational uncertainty; written organizer permission was not inspected. No new application implementation or physical testing was performed while creating the skill.

## Previously reported checks

Latest integrated evidence: `runs/avoidance-e8d6280410/` used the actual Rust `/ws/headon` endpoint, not the local Python planner: 127 simulator samples, 129 Rust telemetry/plan records, two accepted path acknowledgements, one stable maneuver ID, server status `complete`, zero new reported damage and minimum sampled enclosing-circle clearance 1.522 m. Independent readback confirmed physics paused and final poses stable. Source snapshots/hashes, correlated server events and API snapshots are preserved in that run. A first integrated pass `avoidance-2af29f8528` preceded lease-review fixes; use the later run as current evidence.

Verification: 9 Rust unit tests, 21 Python unit tests, build/format/whitespace checks and the explicit synthetic protocol check in `runs/protocol-check-fed323c18e/` passed. The latter verifies prepare/ack/execute, frozen-telemetry pause, ownership/reset protection, dashboard world counts and v1 crossing compatibility without simulator commands. Independent code review identified old-lease renewal and frozen-timestamp gaps; both were regression-tested and corrected before the final live repeat. This completes only the basic two-car open-map algorithm/integration demonstration, not the full U-S03 head-on-with-obstacles requirement or ML integration.

Current open-space avoidance evidence: `runs/avoidance-3d366e13bd/` records two matched red/blue Vivaces sharing a dodge to their respective left sides, passing and returning to the original line. There were no spawned obstacles, 125 samples, zero reported new damage, approximately 29.85/29.92 km/h at closest approach and 1.557 m minimum sampled conservative enclosing-circle clearance. Fourteen Python planner/monitor/configuration/alignment tests passed; `cargo test --offline` completed with zero Rust tests. These facts do not establish general avoidance, obstacle perception, emergency stopping reliability or ML benefit. See [[operations]], [[coordination]] and [[recording]].

Latest repeat: `runs/avoidance-35d4b5dbb9/` verifies the corrected immediate-pause cleanup: 128 samples, zero new damage, 30.01/30.06 km/h near passing and 1.519 m minimum sampled enclosing-circle clearance. An independent live readback confirmed physics paused and final poses stable. This is the preferred current demo evidence; the prior run remains evidence of the pass and the unresolved brake-input limitation. Both use explicit AI paths, with no obstacles or trained model.

After the dashboard update, the user requested one more run. `runs/avoidance-71873434af/` used a separate local optimized Rust server on port 3001, keeping the LinuxONE process and local port-3000 server untouched. The server returned 129 plans, both path acknowledgements and final `complete`; the BeamNG runner recorded 127 samples over 12.9 seconds, zero damage increase, 1.551 m minimum sampled enclosing-circle clearance, and a paused final scene. The 2D dashboard is available at `http://127.0.0.1:3001` and reads the final world snapshot as disconnected after the controller closes. This is another plain, obstacle-free local demonstration, not a LinuxONE run or general safety acceptance.

When the user missed that brief run, they reported that the map showed no live movement. The cause was stale world selection: the frontend kept displaying an older disconnected world while a newer run was connected. After fixing selection and rebuilding the isolated dashboard server, a further user-requested run `runs/avoidance-82ebb49eb5/` completed: 127 samples, 129 plans, zero damage increase, 1.523 m minimum sampled enclosing-circle clearance and paused final physics. During execution, the API advanced from frame 77 to 87 in one second and positions changed for both cars on the selected connected world. No browser screenshot test was available.

Latest user-requested repeat: `runs/avoidance-5eaceb9726/` ran against the same isolated local Rust coordinator on port 3001. The Rust server received 131 plans and reported `complete`; the BeamNG runner recorded 129 samples over 13.1 seconds, zero damage increase, 1.540 m minimum sampled enclosing-circle clearance and `passed_and_returned`, then paused the scene. A post-run `/api/worlds` read returned the latest world with both final vehicle positions. This was an empty-map local demonstration, not a LinuxONE run, ML evaluation or general safety acceptance.

New live evidence: the user authorized a Grid Plane two-car head-on baseline, replacing their earlier crossing request. A standalone BeamNGpy controller attached to BeamNG.tech, placed matching red/blue Vivaces on opposing straight AI paths and recorded 120 state/damage/electrics samples. Both damage sensors increased; AI inputs were stopped afterwards. See [[operations]] and `runs/headon-d0f1ef6424/`. This is one intentional-crash run, not physical acceptance of the coordinator, an integrated Python bridge, or a trained model.

The earlier conversation reported successful `cargo check --offline`, Rust formatting, JavaScript syntax checking, localhost health response, and a browser preview populated with example data. These are historical reported checks and were not rerun during the later documentation review. They do not establish coordination correctness or physical outcomes.

## Offline ML pilot evidence

The user, acting as Manikantan, authorized implementing the offline arrival/clearance training plan. `mani` was fast-forwarded to `main` at `62f423b`. The run `runs/ml-arrival/pilot-20261017T141915Z-48132635/` accepted 48 of 58 trial folders from existing local Small Grid data; failed and interrupted trials were retained in the audit with reasons. Entry test metrics were 0.398 s MAE and 1.157 s run-balanced p95 across three independent test groups. Clearance metrics were 0.470 s and 1.670 s across two test groups. On common moving rows, entry scored 0.363/1.086 s versus 5.357/19.169 s for distance/speed; clearance scored 0.381/1.484 s versus 6.196/20.751 s. Damaged/deviated targets were excluded before their corresponding event. These are small offline results on repeated configurations, not a live controller, collision/safety result or broad generalization claim. Raw telemetry and generated models remain local and ignored by Git.

## Prioritized implementation gaps

1. Correct reservation seeding, missing occupancy retention and full buffered overlap handling.
2. Wall freshness and prediction-horizon guards before results are applied/emitted; reliable disconnect/reset reconciliation and bounded write behaviour.
3. Registered vehicle completeness, initial reconciliation, rate/world limits and explicit unavailable/fallback behaviour.
4. Calibrated predictor/controller integration, approach waiting priority and route-pair geometry.
5. Recording health/drop counters, rotation/drain and experiment metadata; service/RTT/deadline measurements.
6. General bridge/controller capabilities beyond the bounded head-on slice, deployment configuration and the declared acceptance suite when testing is authorized.

The intended Uriel scope now includes arrival-time ML and event-window development. The gap list documents technical work, not authorization to continue prebuilding submission code. Earlier compilation success is not completion or evidence of eligible event work.

## Sources

- [[sources]]: S1 requirements, S2 conversation decisions, S3 source inspection; S5 new handoff; prior checks from this chat.
- Related: [[architecture]], [[coordination]], [[recording]], [[open-questions]].
