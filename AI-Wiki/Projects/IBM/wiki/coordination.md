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
