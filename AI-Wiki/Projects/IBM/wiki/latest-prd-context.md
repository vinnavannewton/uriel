---
title: "Latest Uriel PRD context"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Latest Uriel PRD context

Source: the full [[Projects/IBM/raw/uriel-product-requirements-v1|Uriel Product Requirements Document v1.0]], supplied from the lead's Documents folder and preserved byte-for-byte in this project. Read the original for exact scenario acceptance wording; this page is a navigation summary. Provenance/hash are in `../raw/uriel-product-requirements-v1-provenance.json`.

The named ownership in [[team-workflow]] is the lead's later direct allocation and takes precedence over the PRD's generic role table. The PRD is requirements context; it does not independently authorize code changes, deployments or test execution.

## Current requirements

Uriel's requested product scope is cooperative vehicle conflict and road-hazard coordination. Preserve the full catalogue; stages organize dependencies and the team selects demonstrations. Features are requirements, not implementation claims.

| ID | Scenario family |
|---|---|
| U-S01 | Connected two-vehicle 90-degree crossing |
| U-S02 | More vehicles and multiple intersections |
| U-S03 | Connected head-on encounter with obstacles |
| U-S04 | Controller/driver non-response and controlled stop |
| U-S05 | Sensor-derived unknown vehicle at a crossing |
| U-S06 | Unknown oncoming vehicle |
| U-S07 | Rear-end threat |
| U-S08 | Mixed vehicles, trucks and articulated rear clearance |
| U-S09 | Elevation, slopes, flyovers and stacked roads |
| U-S10 | Airborne/falling vehicle prediction |
| U-S11 | Potholes, disturbance and shared hazard map |
| U-S12 | Blockages, unstable surfaces and rerouting |
| U-S13 | Capability-gated suspension/obstacle-jump experiment |

Backend: Rust/Axum/Tokio plus a persistent Python ML worker on LinuxONE. BeamNG/bridges and scan preprocessing run on Fedora laptops. The PRD reports one shared Ubuntu 24.04/s390x VM with 3 vCPUs, 8 GB RAM and 50 GB disk, individual SSH keys, and an `ibm-ml-labs` container. These were not independently verified in this skill task. Training/inference should begin in that Python environment with bounded threads and requests.

The first required ML task covers arrival and, where useful, rear clearance time. A small gradient-boosted regressor is proposed, with a simpler physical/regression baseline. Collect varied commands/configurations; split by complete runs; handle censored arrivals and avoid future-data or hidden-ground-truth leakage. Measure offline timing and actual downstream outcomes.

Protocol requirements expand to 3D pose/orientation, body height/articulation, capability/health/uncertainty, sensor-derived tracks, hazards and versioned plans with acknowledgement/achieved-motion separation. The old XY/heading-only prototype does not meet these requirements. Proposed `/v1/` HTTP/WebSocket interfaces and internal `/predict/batch` are not implemented endpoints.

Modes: baseline, observe-only, algorithm-only, hybrid, fault injection and replay. Use one scenario owner for control, world/run isolation, actual rear clearance, bounded queues, freshness and tested local fallback. Separate decks need 3D geometry/connectivity; unknown vehicles receive no commands or hidden telemetry.

Initial targets include 10 Hz compact updates, 100 tracks across declared worlds, five-minute measured load, decision p95 below 50 ms and combined sustained memory below 6 GB. These are unmeasured targets. Scenario acceptance, capabilities and model benefit require evidence; all thirteen families are not promised in one event.

## Sources

- S6 in [[sources]]: complete preserved Uriel PRD v1.0 and its provenance.
- Related: [[implementation-status]], [[team-workflow]], [[context-reconciliation]].
