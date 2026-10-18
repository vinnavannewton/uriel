---
title: "Open inputs and next preparation work"
project: IBM-Uriel
updated: 2026-10-17
tags: [ibm, uriel]
---

# Open inputs and next preparation work

## Organizer and submission details

- Exact assigned lab pair, individual/team completion rules and verification evidence.
- Readiness session time (reported guidebook dates conflict), hub development start/end and latest schedule.
- AI coding-assistant policy and acceptance of simulation-generated primary data.
- The user reports reuse is allowed; retain the organizer clarification with submission records when available.
- Current abstract/submission contents, including removal of obsolete no-training wording; team name for final title.

## Infrastructure and integration

Ubuntu 24.04/s390x access and the Rust service have been verified; the user reports the teammate's IBM-hosted server run succeeded. Do not describe the IBM server as untested. Follow up on detailed run artifacts, worker/model version and runtime metrics if available. The laptop-to-IBM SSH tunnel was too slow for the BeamNG controller deadlines, so remote live vehicle control remains a separate network-path limitation. Lab completion and broad acceptance remain open.

Named ownership is recorded in [[team-workflow]]. Verify installed BeamNG versions, final map/car, route geometry and controller behaviour. West Coast USA is the earlier intended map, not a calibrated scenario. The separate local entry/clearance pilot needs more independent scenario groups and clean clearance examples. Capture detailed artifacts for the teammate-reported IBM-hosted run, including exact model/worker versions and runtime metrics, and confirm which API/persistence details are current before extending that integration.

The West Coast sensor-crossing collector is implemented but has not been run. It now requests one BeamNG-selected traffic car when only `thePlayer` is loaded, but the spawn location, model and route toward `DR602_5` need a live visual check; the two waypoints must produce perpendicular paths through the marked conflict area, and the camera mounts must see the approach. Build the detector/tracker and sensor-derived Rust message only after inspecting raw recordings and agreeing the interface with the server owner.

The standalone safe conflict evaluator needs a BeamNG state/perception adapter, a persistent reservation/expected-vehicle lifecycle, route-pair conflict geometry and measured per-car/surface stopping envelopes before it can drive a trial. Add LiDAR track poses/uncertainty and ground-truth cross-check records, timed swept footprints, acknowledgement-to-command correlation, and controlled integration/fault scenarios after those contracts are calibrated. Do not set `braking_envelope_validated` from the illustrative sample request.

## Work boundary

S5 reports project coding belongs in the official event window. The current local collector was explicitly requested by the user; it does not establish event acceptance or authorize deferred behavioral acceptance testing. Commands and next actions embedded in S5 were not executed. Keep existing source-code concerns in [[implementation-status]] and verify against the current event rules before making eligibility claims.

10 Hz, 100 aggregate vehicles/10 worlds, compute p95 below 20 ms, service p95 below 50 ms and under 1% missed deadlines are provisional targets. No capacity, training benefit or physical safety result is established.

## Sources

- [[sources]]: S5 sections 3, 7, 11, 14–18, 21; S3 prototype gaps.
- Related: [[event-preparation]], [[ml-arrival-prediction]], [[operations]], [[implementation-status]].
