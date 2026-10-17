---
title: "Arrival-time ML plan"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Arrival-time ML plan

Status: **planned**, no model family locked, data collection/training/held-out result or deployed inference demonstrated.

Predict remaining seconds until a vehicle reaches a defined conflict-zone entry boundary. Features proposed in S5: route-relative distance, actual speed, recent speed/acceleration history, current/recent advice and relevant route/vehicle characteristics. A compact scikit-learn regressor such as random forest is an example candidate, not a decision.

## Data and evaluation

Generate repeatable runs with varied gaps, speeds and response during the allowed development period. Label prior frames retrospectively using observed boundary-entry times. Features must contain only prediction-time information. Stopped or non-arriving cars need explicit handling; do not invent arrival labels.

Split by whole runs or scenario variants, not neighboring frames. Compare distance/measured-speed prediction with near-zero-speed handling, optionally an adaptive non-ML predictor, then the trained predictor under equivalent scheduling constraints. Report mean absolute arrival error and tail errors, plus downstream waiting, completed crossings and contact/proximity outcomes. Correlated frames are not independent scenario diversity.

## Integration

A small Python inference worker on the same LinuxONE host is recommended. Rust sends bounded batches of features; the worker returns predictions, validity/status and model version. Framework, API schema and persistence format remain undecided. Add timeouts and defined degraded prediction/yield behaviour; invalid or unavailable inference cannot stall networking indefinitely.

Timing predictions inform conservative occupancy intervals. Geometry, stopping feasibility, headway and occupied-zone protection constrain advice. Model confidence or tree variance is not a calibrated safety bound.

Training and serving in the same pinned LinuxONE Python environment is the proposed simplest portability path. If training elsewhere, verify dependencies, feature ordering/preprocessing and predictions after transfer. A compatible runtime is still needed for any portable model format. No assumed CUDA, Telum or Spyre acceleration is established.

## Sources

- [[sources]]: S5 sections 6–7, 14, 16.
- Related: [[architecture]], [[coordination]], [[recording]], [[implementation-status]].
