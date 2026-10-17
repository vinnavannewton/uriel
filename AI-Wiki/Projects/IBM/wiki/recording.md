---
title: "Telemetry and experiment recording"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Telemetry and experiment recording

## Uriel experiment and training data requirements

S5 adds actual zone-entry events/arrival labels, prediction-time feature history, model/version and preprocessing identity, prediction errors, paired outcomes and platform/resource evidence. Save run configuration, commit hash, model version, timestamps and run IDs. Keep physical shared-world trials, independent multiworld traffic and synthetic/replayed capacity evidence labelled separately. Replay ignoring advice is not closed-loop evidence.

Existing JSONL events below do not establish complete training-label or experiment instrumentation. Source: [[sources]] S5 sections 7, 11, 16, 18. Related: [[ml-arrival-prediction]], [[event-preparation]].

Each startup creates `runs/<UUID>/metadata.json` and `events.jsonl`. Metadata includes the loaded scenario, protocol version and package version. Events have kind, server uptime in milliseconds and event-specific data.

Recorded kinds include hello, accepted telemetry, rejected messages, plan, applied result, vehicle removal, disconnect and compute error. Accepted telemetry records vehicle states and world/session/epoch/frame/time identity. Plan records include compute time and the outgoing recommendation.

A queue of 4096 events feeds one asynchronous file writer. Queue overflow warns and drops the record; writer failures log an error. `/api/status` reports the fixed string `jsonl`, not actual writer health. There is no rotation, retention policy, record-drop counter or guaranteed shutdown drain.

Metadata does not yet capture commit hash, machine allocation, effective freshness/control settings or full paired-trial configuration. Acknowledgement and plan event envelopes do not consistently include all identity fields independently. Detailed prediction internals, reservation transition events and complete service/RTT/deadline metrics remain to implement.

Preserve actual recordings outside the wiki. Ingest only named run summaries with metadata and links, reporting missing records and detector limitations. No contacts, throughput gains or deadline targets have been measured.

## Sources

The standalone open-space avoidance controller writes a separate format under `runs/avoidance-<id>/`: configuration/initial state and source hashes in `metadata.json`, variable-rate per-vehicle state/damage/electrics samples with individual simulation times in `telemetry.jsonl`, and outcome/guard/clearance/damage details in `summary.json`. This is not the Rust `events.jsonl` schema. `runs/avoidance-3d366e13bd/` additionally preserves the executed controller/planner sources and a later pause verification. The 125 samples establish one zero-new-damage pass, not an independently labelled or split ML dataset; the closest distances are sampled and sensor polls are sequential.

Preferred current evidence is the later repeat `runs/avoidance-35d4b5dbb9/`: 128 samples, metadata, summary, hash-verified executed-source copies and `verification.json` with independent final pause/stable-position readback. Both passes and aborted setup attempts remain separate runs, rather than being merged into a misleading success-only dataset.

The later **Rust-integrated** current evidence is `runs/avoidance-e8d6280410/`, superseding the standalone run as the integration reference. Python records raw measured samples plus `rust_plan_seq`/status, configuration/source hashes, full request-response timing in `bridge-wire.jsonl`, and summary identity/maneuver/outcome. Rust's shared `events.jsonl` now adds `headon_hello`, `headon_telemetry`, `headon_plan`, `headon_maneuver_ack`, `headon_rejected` and `headon_disconnect`. Correlate world, reset epoch, session, frame, plan and stable maneuver IDs; the final run has 129 telemetry/plan pairs and two accepted paths. Acceptance records do not establish achieved motion; measured telemetry and completion evidence are separate.

The run includes filtered server events, source snapshots, API snapshots and `verification.json`. A maximum local request/response time of about 1.33 ms was observed in that one run; it is not a LinuxONE or load benchmark. Existing writer health/drop/drain limitations still apply. No arrival/dodge labels, complete-run dataset split, training or model evaluation were added.

- [[sources]]: S1 PRD sections 9–10, S3 static inspection; [main.rs](../../../../src/main.rs).
- Related: [[implementation-status]], [[open-questions]].
