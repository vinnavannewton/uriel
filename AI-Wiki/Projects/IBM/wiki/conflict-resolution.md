---
title: "Safe multi-vehicle conflict resolution"
project: IBM-Uriel
updated: 2026-10-17
tags: [ibm, uriel, coordination, safety]
---

# Safe multi-vehicle conflict resolution

## Implemented local evaluator

`src/conflict_resolution.rs` adds a state-aware evaluation component exposed at `POST /api/conflicts/evaluate`. It accepts a bounded frame of vehicle observations, explicit route-conflict pairs, caller-supplied prior reservations and conservative timing/braking inputs. When `ARC_TOKEN` is configured the endpoint requires the same Bearer token as the bridge endpoints. `examples/conflict-evaluate.json` is a sample request.

The evaluator classifies approaching, stop-feasible, stop-uncertain, stopping-infeasible, inside/clearing, stopped, cleared and unknown states. Stopping distance includes reaction time, control delay, timing uncertainty, braking distance, safety margin and half the vehicle length. The caller must define distance-to-entry consistently with vehicle reference-point geometry. A deceleration value is accepted only when the caller marks its envelope validated. Missing/uncalibrated braking data or stale telemetry yields `SAFE_HOLD`; a known infeasible stop also avoids a stop/yield command and blocks conflicting releases. The evaluator does not invent braking capability. Existing zone occupancy is retained first; `continue_to_clear` is proposed only when the caller marks its continuation path as verified safe, otherwise the zone remains reserved in `SAFE_HOLD`. Rear-clear observations remove a reservation only from measured input; timers do not clear it. Waiting age is considered before estimated entry time for ties. The initial evaluator permits only one reserved vehicle through the managed zone at a time, including when route pairs are absent from the conflict table.

An independent safety monitor checks each proposed action against the observation freshness, stopping feasibility, and conflict reservations. A disagreement converts a proposed yield/release to `safe_hold`; an occupied vehicle's justified clearance action is preserved. Entering occupancy upgrades a tentative reservation to committed, and measured rear clearance removes it. `POST /api/conflicts/command-result` records command identity, acknowledgement and observed speed; acknowledgement alone leaves response verification unknown, and stop/yield is verified only after measured speed meets the submitted threshold. Both endpoints append records to the existing server JSONL event stream.

## Limits and next integration work

This is an evaluation API, not yet a BeamNG actuator or the authoritative `/ws/bridge` scheduler. It requires a bridge/client to calculate the observation fields and to apply and acknowledge actions. It does not itself send vehicle commands. The current request schema includes 2D route IDs and scalar timing/occupancy; it does not yet carry timed swept-footprint polygons, LiDAR point tracks, simulator ground-truth cross-check results, a registered expected-vehicle manifest, prediction intervals for entry/clearance, or a server-owned persistent reservation state. The caller currently submits the prior reservations on each request. The v1 bridge's existing coordinator has not been replaced by this endpoint.

No route geometry, car-specific braking envelope, controller delay or surface/friction profile has been calibrated for the current West Coast poses or Small Grid. Do not mark `braking_envelope_validated=true` without separate measurement evidence. The sample's 5 m/s² is illustrative only. A five-frame, two-vehicle reservation replay exercised release, yield, occupied-zone continuation, committed-reservation upgrade, rear-clearance release and the next vehicle's passage through an isolated local HTTP server; all monitor verdicts accepted. This replay issued no simulator commands and is not a BeamNG behavioral run. A live attempt was blocked because the BeamNG API port 25252 refused connections and no Rust server was listening on port 3000. The module is not a safety certification or general collision-avoidance acceptance.

## Sources

- [[sources]] S12: raw user request, implementation and isolated API/unit verification.
- [[coordination]], [[protocol]], [[implementation-status]].


## Local XGBoost and Rust hybrid integration

On 2026-10-18, branch `vinn` fast-forwarded to `origin/main` commit `f36d049`, then its prior staged/unstaged/untracked work was restored. Four wiki conflicts were resolved by preserving both upstream and local content. The recovery stash `codex-preserve-vinn-before-main-ml-integration` is retained; no commit or push was performed.

`scripts/ml_worker.py` now loads the trained combined XGBoost UBJ models, validates schema/evaluation/version/model hashes, selects two-thread CPU inference and warms both predictors. Rust still has the 40 ms worker bound and five-second failure cooldown. `ARC_ML_MODE=hybrid` opts into learned timing in both `/ws/bridge` reservations and `/api/conflicts/evaluate`; default crossing behavior remains observe-only. Valid model estimates can widen the physical/input occupancy window (earlier entry, later clearance), with an experimental two-second allowance. Invalid or reversed timing and unavailable inference fall back to physics/input timing. Occupancy, braking feasibility and measured rear-clearance logic are retained. The new HTTP response includes additive `ml_predictions` and `ml_mode` fields. HTTP observations lack history, height and nearest-vehicle measurements; those model features remain missing. Rust nearest-relative-speed now uses radial velocity, matching the recorder feature convention.

A saved West Coast route export is `scenarios/extended-90-degree-data-collection/rust-crossing.json`. `scripts/run_arrival_hybrid.py` starts a worker and Rust process on unoccupied local ports, and stops its children on Ctrl+C. Commands, artifact contract and limitations are in `scripts/ARRIVAL_HYBRID.md`. It starts services, not simulator driving.

Validation: 38 Rust tests and four Python worker tests passed. An isolated socket integration loaded the actual combined models, obtained ten model-bearing Rust crossing responses (maximum local round trip 2.20 ms), exercised the HTTP conflict evaluator with accepted monitor verdicts, and verified that stopping the worker preserved Rust recommendations. Evidence is under `runs/ml-arrival/combined-gpu-cf2bc118ec/integration/`. Test services were stopped after verification. No live BeamNG hybrid trial or remote deployment was executed. The two-second allowance is not a calibrated prediction interval, West Coast labels remain provisional, and missing-feature behavior/geometry reference alignment require physical validation before acceptance.
