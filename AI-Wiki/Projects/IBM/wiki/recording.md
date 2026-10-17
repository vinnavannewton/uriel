---
title: "Telemetry and experiment recording"
project: IBM-Uriel
updated: 2026-10-17
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

## Local Small Grid pilot recorder

[collect_crossing_trials.py](../../../../collect_crossing_trials.py) creates three independent `smallgrid` scenes with red/blue `etkc` cars on perpendicular approaches. The user explicitly authorized AI driving and three collection trials, superseding the prior behavioural-testing deferral for this scope. This standalone pilot does not use the Rust coordinator or train a model.

Outputs are under `runs/crossing-<uuid>/`: batch metadata, per-trial `telemetry.csv`, `arrival_labels.csv` and `summary.json`. Telemetry contains simulator timestamps, pose, velocity, direction, Electrics control readings and Damage values. At 60 requested physics steps/second, collection advances six steps per sample (nominal 10 Hz) for 20 simulator seconds per trial. Each trial reloads fresh vehicles. Manifest includes script hash, BeamNGpy version, AI target speeds and delay; actual achieved motion is recorded separately. Red/blue target schedules are 8/8 m/s, 8/8 with blue delayed three seconds, and 10/6 m/s. Initial transients mean target speed/time is not achieved-speed evidence.

Arrival labels use the first sampled **front reference point** inside the square x/y in [-3,3] metres; time resolution is nominally 0.1 seconds. These are simulator-ground-truth pilot labels, not full body entry/rear-clearance measurements. Non-arrivals are explicitly censored. Damage increases are observations, not a complete collision detector or attribution. Split later model evaluation by whole runs; this three-run pilot cannot establish model quality or generalization. See [[log]] for actual execution results.

## Current-scene traffic recorder

`collect_traffic_trials.py` preserves the user's two West Coast USA subject starting poses (`thePlayer`, `clone`) and uses BeamNG waypoint AI toward road nodes DR193_2 and DR602_5. The corrected collector waits for four background vehicles and records all six vehicles. It restricts traffic participants to background cars, resets traffic before subject teleport, and checks both starting poses and damage before each trial. Earlier attempts without these guards are explicitly invalidated in their metadata; see [[log]]. Three 30-second runs use speed limits 8/8, 6/8 and 8/6 m/s. Before each run, subject recovery/teleport and background traffic reset are requested. These traffic resets are unseeded and do not establish identical paired conditions.

Telemetry includes subjects and the connected background inventory: 3D pose/orientation, front reference, velocity, finite-difference acceleration, controls and damage. The approximate junction detector uses an 8 m horizontal radius about (-454,146,100), with 4 m elevation tolerance. This is an approximate arrival proxy, not surveyed lane conflict geometry. Non-arrivals are censored. Per-trial summaries include damage changes, displacement, peak speed and observed background proximity. Full initial vehicle configurations and collector source are retained in the run folder. This is standalone BeamNG AI baseline collection, not Uriel control or model training. See [[log]] for measured outcomes and limitations.

## Fresh seeded 30 Hz Small Grid experiment

`scripts/fresh_experiment.py` implements the user's supplied fresh-experiment specification, archived with each experiment. New batches live under `uriel_experiment/experiment_<uuid>/fresh_001` through `fresh_003`; creation fails rather than overwrites an existing batch. Each run has telemetry, separate event JSONL, metadata, geometry and validation report; the batch has a combined trial-summary CSV and exact collector source/hash.

The fixed virtual crossing has subject lanes on +X/+Y through (0,0), an approximately 40 m approach, central square [-3,3] m and virtual stop planes at route progress -6 m. Two default `etkc` cars differ in colour; four prior `simple_traffic` configurations are copied to the fresh scenario on fixed offset routes at +/-12 m. Background identities are recreated and linked to their prior source IDs in metadata; they are not asserted to be the same live objects after map reload. Seeds 903101/903102/903103 draw subject target speeds 5–10 m/s, background targets 4–8 m/s, initial speeds 0–2 m/s, blue/background launch delays 0–2 s and background route starts -65 to -45 m. Subject positions/headings and route assignments remain fixed. Polyline speed AI is used without prescribed arrival timestamps. Requested and measured initial speeds are stored separately; delayed cars are braked until launch.

Each trial has a 25 s maximum and records the full horizon at nominal 30 Hz (two physics steps at 60 Hz). Periodic data include identity/time, position/orientation, velocity and finite-difference acceleration, controls/gear, commanded AI state/settings, nearest-reference relative distance/radial speed, damage, virtual lane/deviation state and all spawn OOBB corners. Per-vehicle sockets are polled concurrently while physics is paused; the frame is completed before advancing physics. OOBB corners are retrieved in one game-engine Lua batch using the installed tech API's underlying `getSpawnWorldOOBB` method.

First sampled body-proxy overlap and downstream rear-proxy clearance define labels; damaged geometry is marked ambiguous. This is a spawn-OOBB proxy, not calibrated deforming-body occupancy. Contact detection is unavailable and stays null; damage changes are separate events, never verified contacts. Background routes do not enter the central square, so their central-zone non-arrival is expected. Virtual stop lines have no legal traffic-rule interpretation. Fresh trials reload vehicles, hold with realistic automatic shifting, check starting poses/damage, and initialize/measure speed. Validation checks IDs, sample count, time intervals, finite values and label consistency, reporting missing fields explicitly. See [[log]] for actual run outcomes and failures.

### Reusable CLI and speed measurements

The live `scripts/fresh_experiment.py` has parameterized trial count, duration, seed, host/port, requested telemetry cap (30/60/120 Hz), BeamNG deterministic speed factor (1–8) and output/config paths. Archived earlier collector sources remain unchanged. Event stop-duration detection uses elapsed simulation time instead of a hard-coded 15-frame window. AI launch events use the recorded frame timestamp. Inspect each run's sampling metadata for the actual rate.

The speed argument controls BeamNG's native deterministic speed factor. Graphics FPS is held at 60 during setup, capture, and cleanup, and left at 60 on exit. BeamNG advances `speed × 50 ms` per captured frame, so effective sampling is capped at `20/speed` Hz. At speed 2, this is 10 Hz; at speed 8, 2.5 Hz. At a 60 FPS cap the theoretical wall-clock ceiling is `3 × speed`; actual multiplier, measured sample rate and requested rate are recorded. Higher speed trades away temporal detail; 60 Hz simulation sampling is not supported by this per-frame API collector while accelerated. The recorder now accepts `--ai-aggression` with BeamNG's conservative/aggressive endpoint names or a numeric 0.3–1.0 value, applies it to each route-following vehicle and stores it per sample and in run metadata. Route-following telemetry uses BeamNG's built-in `manual` mode name. Background configs are durable project assets. Failures/interruption are saved, and output directories use new experiment UUIDs. Usage and limitations are in `scripts/BEAMNG_RECORDING.md` and [[operations]].

Raw `telemetry.csv`, `arrival_labels.csv` and `events.jsonl` outputs are retained locally under the project output directories and excluded from Git by `.gitignore`. Small experiment summaries, metadata and collector sources remain reviewable and versionable.

## Offline model fitting

`scripts/train_arrival.py` reads per-trial telemetry without opening BeamNG. It recomputes virtual-square entry/rear-clearance timestamps from logged spawn OOBB corners, audits them against saved labels, and records target-specific damage/deviation exclusions and censored outcomes. It uses only the two central-crossing subject vehicles for model rows; the four offset traffic routes are audit-only. Training output, saved regressors and held-out predictions live under `runs/ml-arrival/<UUID>/`, which is ignored by Git alongside raw recordings. The command, feature list, grouped split, metrics and evidence are in [[ml-arrival-prediction]].

### Ten-run 60 Hz collection

The user ran the documented command with system `python`, which lacked BeamNGpy. Rerunning with `.venv/bin/python` completed ten fresh runs in `uriel_experiment/experiment_c03ce1dbb91143a4b66cdb7f56c7fbef`, seeds 903101–903110. Each run is 25 simulation seconds, 1,501 samples per vehicle across six vehicles (9,006 rows/run; 90,060 total). All ten validation reports are PASS_WITH_LIMITATIONS with no validation issues. Measured telemetry is 60 Hz, and mean wall-clock speed is 0.333x; the requested 2x was not reached.

| Run | Red entry / clear (s) | Blue entry / clear (s) | Damage increase (red / blue) |
|---|---:|---:|---:|
| 001 | 6.967 / 8.350 | 9.334 / 10.884 | 0 / 7498.742 |
| 002 | 7.817 / 9.517 | 7.084 / 8.317 | 0 / 0 |
| 003 | 6.583 / 7.933 | 6.950 / 9.400 | 2902.954 / 6756.178 |
| 004 | 6.700 / 7.917 | 7.617 / 9.150 | 3667.158 / 0 |
| 005 | 7.650 / 10.234 | 7.317 / 8.700 | 11830.625 / 1053.930 |
| 006 | 7.400 / 16.833 | 7.317 / 10.283 | 7902.346 / 2276.218 |
| 007 | 7.750 / 10.217 | 8.517 / 10.450 | 348.098 / 9531.010 |
| 008 | 8.134 / 11.984 | 7.684 / 12.100 | 5275.086 / 4601.482 |
| 009 | 7.000 / 9.133 | 7.367 / 10.500 | 4692.970 / 6621.091 |
| 010 | 6.517 / 7.634 | 7.900 / 9.200 | 0 / 0 |

Damage values are not verified collisions; contact remains unavailable, and entry/clearance use virtual-zone spawn-OOBB proxies. Route deviations occurred in runs 003 (red), 006 (both) and 007 (blue). An earlier interrupted attempt with the same seeds is preserved as `experiment_aae76144cd1a4556bf2b1737253a6035`; its first four runs completed, two later runs hit zero-time acceleration division, and the run was interrupted before completion. The collector now leaves acceleration null for a repeated simulator timestamp instead of aborting; the completed rerun had no validation issues. The original failed files remain unchanged.
