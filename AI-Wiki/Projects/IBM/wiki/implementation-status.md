---
title: "Implementation status and evidence"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Implementation status and evidence

Current status: **Uriel planning/submission preparation plus an existing historical Arc Angel prototype**. S5's statement that no working codebase was demonstrated belongs to its own conversation; earlier files exist here. Neither source establishes a complete Uriel implementation, trained model, deployment or benchmark. The newly reported prohibition on continuation projects leaves this pre-event code's submission eligibility unresolved. See [[context-reconciliation]] and [[event-preparation]].

The table below inventories the earlier prototype; it does not certify event eligibility. Source inspection and historical checks are not a new behavioural test run.

| Area | Current state |
|---|---|
| HTTP service and browser template | Implemented |
| JSON bridge protocol, owner/session/epoch identity | Implemented with lifecycle gaps |
| Frame and vehicle validation | Implemented subset |
| Per-world state and bounded blocking computation | Implemented; four global permits |
| Latest pending frame coalescing | Implemented |
| Route projection, reservations and headway | Simplified implementation; static concerns in [[coordination]] |
| Advice simulation expiry | Present in output |
| Server wall-age checks at plan emission | Missing |
| Dashboard | HTTP polling, read-only, labelled demo mode |
| Detailed recording | Standalone seeded six-vehicle recorder implemented; BeamNG frame limiter fixed at 60 during and after collection; per-frame accelerated sampling is capped by BeamNG's physics step quantum |
| Python BeamNG bridge and calibrated control | Connection helper and standalone Small Grid pilot collector now present; Rust telemetry/control integration and calibrated control remain absent |
| Real West Coast USA scenario | Not configured |
| Physical/fault/load acceptance | Small Grid, West Coast traffic and fresh seeded 30 Hz plus ten 60 Hz baseline trials recorded; no Uriel closed-loop/fault/load acceptance established |
| Ubuntu/LinuxONE deployment | Not performed; Ubuntu 24.04/s390x target reported confirmed in S5 |
| Arrival-time ML, dataset labels and evaluation | Standalone pilot collects sampled front-point arrival labels; no trained model or held-out evaluation established |
| Python inference worker on LinuxONE | Recommended design; not implemented |
| Mandatory labs / event readiness | Required according to S5; completion unverified |

## Current planning update

The latest PRD expands requirements to 3D state, richer scenarios and arrival/clearance ML; see [[latest-prd-context]]. The existing prototype remains limited as inventoried above. Team ownership and the new repo-local `uriel` skill are now recorded in [[team-workflow]]. The user reports reuse is permitted, superseding the prior conversational uncertainty; written organizer permission was not inspected. No new application implementation or physical testing was performed while creating the skill.

## Previously reported checks

The earlier conversation reported successful `cargo check --offline`, Rust formatting, JavaScript syntax checking, localhost health response, and a browser preview populated with example data. These are historical reported checks and were not rerun during the later documentation review. They do not establish coordination correctness or physical outcomes.

## Prioritized implementation gaps

1. Correct reservation seeding, missing occupancy retention and full buffered overlap handling.
2. Wall freshness and prediction-horizon guards before results are applied/emitted; reliable disconnect/reset reconciliation and bounded write behaviour.
3. Registered vehicle completeness, initial reconciliation, rate/world limits and explicit unavailable/fallback behaviour.
4. Calibrated predictor/controller integration, approach waiting priority and route-pair geometry.
5. Recording health/drop counters, rotation/drain and experiment metadata; service/RTT/deadline measurements.
6. Bridge, deployment configuration and the declared acceptance suite when testing is authorized.

The intended Uriel scope now includes arrival-time ML and event-window development. The gap list documents technical work, not authorization to continue prebuilding submission code. Earlier compilation success is not completion or evidence of eligible event work.

## Sources

- [[sources]]: S1 requirements, S2 conversation decisions, S3 source inspection; S5 new handoff; prior checks from this chat.
- Related: [[architecture]], [[coordination]], [[recording]], [[open-questions]].
