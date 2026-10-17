---
title: "Open inputs and next preparation work"
project: IBM-Uriel
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

Ubuntu 24.04/s390x is reported confirmed; do not reopen architecture selection as if no target were known. Still confirm SSH access, vCPU/RAM, installed tools/ML packages, permissions, networking and allowed remote access method. No completed lab or deployed model/service is established.

Named ownership is recorded in [[team-workflow]]. Verify installed BeamNG versions, final map/car, route geometry and controller behaviour. West Coast USA is the earlier intended map, not a calibrated scenario. Resolve actual entry labels, feature history, preprocessing, whole-run held-out split, model family, worker API/framework and persistence format.

## Work boundary

Current request is wiki ingestion. Preparation can document architecture, data and roles; S5 reports project coding belongs in the official event window. Commands and next actions in that source were not executed. Keep existing source-code concerns in [[implementation-status]] for later work.

10 Hz, 100 aggregate vehicles/10 worlds, compute p95 below 20 ms, service p95 below 50 ms and under 1% missed deadlines are provisional targets. No capacity, training benefit or physical safety result is established.

## Sources

- [[sources]]: S5 sections 3, 7, 11, 14–18, 21; S3 prototype gaps.
- Related: [[event-preparation]], [[ml-arrival-prediction]], [[operations]], [[implementation-status]].
