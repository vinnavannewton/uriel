---
title: "Implemented coordination and limits"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Implemented coordination and limits

## Uriel planning update

S5 adds learned arrival timing to buffered occupancy estimates while retaining explicit geometry, feasibility, conservative reservations and headway. It does not claim ML directly commands braking or certifies safety. First-approach waiting age, actual clearance and response calibration remain requirements. The code described below is the earlier simplified non-ML scheduler; it does not implement the new predictor. Source: [[sources]] S5 sections 7–9. Related: [[ml-arrival-prediction]], [[context-reconciliation]].

The current scheduler is deterministic for the supplied ordered state: first observed frame sequence, then vehicle ID. It projects positions onto declared polylines and uses velocity magnitude for arrival estimates.

Each route has a distance along the route for the zone center. Entry/exit buffers use zone half-extent, margin and half vehicle length. All reservations are treated as incompatible rather than consulting a route-pair conflict table. Vehicle width and heading are not used for swept-footprint prediction.

Occupied, committed or unable-to-stop cars receive proceed advice. A stopped vehicle is handled using minimum-speed assumptions rather than division by zero. Waiting cars get a greedy predicted window; delayed cars receive a zero cap. Same-route following caps are then applied as a separate pass.

Provisional constants include 3 m/s² braking, 0.5 s response allowance, four-metre deviation threshold and two-second headway. They are not measured car/controller properties. `yield_s_m` is parsed but not used for scheduling the stop location.

## Static concerns to resolve

### Separate Grid Plane avoidance experiment

The later user request authorizes immediate local two-car avoidance experiments and then explicitly defers physical obstacles. `scripts/headon_planner.py` is a separate Python geometry/controller experiment, not a change to the Rust scheduler. It uses metre coordinates centred on the encounter: red faces -Y and blue +Y; positive X is red's left and blue's right. Both moving to their own left means **opposite world sides**, not the same world direction.

The planner selects one fixed pair of paths for the whole pass. Open-space preference assigns +3.5 m to red and -3.5 m to blue, with smooth outbound shifts, a hold through the encounter and a return after passing. Vehicle footprints are enclosed by circles measured from each live bounding box relative to its reference point. Candidate checks include continuous point-to-segment distance for supplied static circles and a sampled pairwise timing window of +/-0.5 s at the declared speed. Single-car alternatives and a no-feasible-plan brake result have unit coverage. **No physical pole, obstacle sensing or obstacle trial was performed.** Known obstacle coordinates in a geometry fixture are not perception.

Live monitoring checks finite/upright state, sensor-time skew, path deviation, new damage and a one-second constant-velocity envelope projection. These are experiment guards, not calibrated guarantees. Telemetry failure braking is best-effort and does not establish a simulator-side disconnect watchdog. The controller is bounded to an empty flat map, the existing matched Vivaces, a 110 m initial reference separation and <=10 m/s planner speed. Dynamic hazards, road boundaries, late-start dodge feasibility, varying initial speeds, multi-car negotiation, integrated server messages and ML remain outside demonstrated scope.

The completed run `runs/avoidance-3d366e13bd/` passed with zero new reported damage. Its minimum **sampled** enclosing-circle clearance was 1.557 m; this is a conservative geometry metric, not a directly measured body-surface gap. The controller finishes by pausing physics because acknowledged brake inputs alone did not establish a complete stop. See [[operations]] for API-specific alignment and pause details.

The final repeat `runs/avoidance-35d4b5dbb9/` also passed without new damage, with a 1.519 m minimum sampled circle clearance. Immediate scene pause on guard abort/completion is now implemented and the final paused poses were verified stable. This simulator pause must not be presented as successful physical emergency braking or a disconnect watchdog.

### Integrated Rust head-on slice

The subsequent contract/integration task moved authoritative path generation to `src/headon.rs` and the live bridge to `/ws/headon` (v2). `scripts/beamng_headon.py --run` now uses Rust by default; the Python planner is an explicitly selected standalone baseline. The Rust scene is intentionally limited to the open flat map, repaired/stopped matched cars at `(0,+55)` and `(0,-55)`, a fixed own-left paired shift (+3.5/-3.5 m) and 30 km/h target. It uses enclosing-radius clearance checks with +/-0.5 s sampled timing variation, holds paths stable, waits for both acceptances, and guards measured motion before renewing a 500 ms lease.

The final physical run `runs/avoidance-e8d6280410/` records one stable Rust maneuver across 129 telemetry/plan exchanges, both path acceptances, measured completion and zero new damage. No obstacles, learned timing or general alternate-path negotiation were exercised. Review regressions cover not renewing after old-lease expiry and not renewing frozen execution timestamps. Bridge failures request a simulator pause; there is no verified physical braking controller or independent process-death watchdog. Source and run provenance are in [[sources]] S9. These facts complete a basic integrated algorithm-only demonstration, not full U-S03 acceptance.

- Seed occupied/committed reservations before processing any waiting candidate. Current order can allocate an incompatible waiting slot first.
- Treat missing occupancy as unresolved until justified clearance; finite predicted times are insufficient.
- Revisit overlap checks over full candidate duration; the current conflict check uses a two-second estimate before computing actual slot length and does not iterate to a stable conflict-free result.
- Route deviation requires conservative occupancy even when a car is not classified committed.
- Reconcile headway-induced speed changes with reservation timing.
- Replace first-seen frame priority with recorded approach arrival/waiting age, calibrated prediction intervals and controller feasibility.

These are source-derived concerns, not reproduced trials. The implementation does not prove collision prevention.

## Sources

- [[sources]]: S1 PRD sections 6–7; S3 static inspection.
- [coordinator.rs](../../../../src/coordinator.rs), [scenario.rs](../../../../src/scenario.rs).
- Related: [[implementation-status]], [[open-questions]].
