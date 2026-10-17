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

- [[sources]]: S1 PRD sections 9–10, S3 static inspection; [main.rs](../../../../src/main.rs).
- Related: [[implementation-status]], [[open-questions]].
