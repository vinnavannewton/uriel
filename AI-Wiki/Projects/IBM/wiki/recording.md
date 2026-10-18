---
title: "Telemetry and experiment recording"
project: IBM-Uriel
updated: 2026-10-18
tags: [ibm, uriel]
---

# Telemetry and experiment recording

## Uriel experiment and training data requirements

S5 adds actual zone-entry events/arrival labels, prediction-time feature history, model/version and preprocessing identity, prediction errors, paired outcomes and platform/resource evidence. Save run configuration, commit hash, model version, timestamps and run IDs. Keep physical shared-world trials, independent multiworld traffic and synthetic/replayed capacity evidence labelled separately. Replay ignoring advice is not closed-loop evidence.

Existing JSONL events below do not establish complete training-label or experiment instrumentation. Source: [[sources]] S5 sections 7, 11, 16, 18. Related: [[ml-arrival-prediction]], [[event-preparation]].

## West Coast two-car pilot

The standalone `scripts/collect_west_coast_arrival_trials.py` writes per-trial `telemetry.csv`, `events.jsonl`, `metadata.json` and `summary.json` under `runs/west-coast-arrival-<id>/`. It polls both saved Vivaces at a 5 Hz target and records position, orientation, velocity, controls, damage, nearest-car separation and spawn-OOBB occupancy against the provisional `junction1_wp12` radius. The target zone and proxy entry/clearance labels are not calibrated for training.

At BeamNG deterministic speed factor 4, stepping once per sample preserved the 5 Hz target and one clean road-AI pilot completed in 14.7 wall seconds for 30.8 simulation seconds: `runs/west-coast-arrival-a0d9d53e60/`. A later direct coordinate-line attempt caused an immediate damage spike and was stopped; both cars were restored to their saved poses with zero damage. The direct-line route was removed. Do not batch more runs until a safe straight-through route is loaded from the user's manual ScriptAI trajectories. See [[operations]].

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

The user-requested 30-minute six-traffic run `runs/sensor-crossing/navgraph-hour-d50474577c27/` completed 1,800.6 simulated seconds in 681.2 wall seconds (observed average speed factor 2.64×). It uses saved West Coast graph routes, red ETK at 60 km/h and black midsize car at 25 km/h with BeamNG native waypoint AI and traffic avoidance. It recorded 2,047 paired state/LiDAR frames, with 2,047 clouds for each car, 2,047 ground-truth JSONL rows covering both subjects and traffic, and a 80.4 MB sensor index. Total run size is 4,454,620,388 bytes (~4.15 GiB): red LiDAR 2.12 GB, black LiDAR 2.24 GB, ground-truth JSONL 9.0 MB. The six-traffic run initially stalled red near its start; after the user requested clearing traffic, BeamNG `traffic.reset()` relocated all six vehicles away from the player and is recorded in metadata. Red then reached its endpoint in multiple later legs. Across 44 legs, both endpoints were observed in 20, 15 ended at the time limit with an endpoint unreached, 8 stopped on the damage guard, and the final leg ended the run. Pre-reset stalled rows and post-reset intervention-conditioned rows must remain distinguishable. This JSONL/NPZ telemetry is not yet consumed by `scripts/train_arrival.py`.

The current Small Grid CSV training source `uriel_experiment/` occupies about 3.01 GB (2.80 GiB), contains 61 trial folders (50 accepted by the latest audit), and yielded 3,587 entry-target and 2,499 clearance-target rows. The latest fit produced an entry model only; clearance did not meet grouped validation requirements. The 4.15 GiB West Coast capture is separate raw LiDAR data and is not included in those training totals.

## Fresh seeded 30 Hz Small Grid experiment

`scripts/fresh_experiment.py` implements the user's supplied fresh-experiment specification, archived with each experiment. New batches live under `uriel_experiment/experiment_<uuid>/fresh_001` through `fresh_003`; creation fails rather than overwrites an existing batch. Each run has telemetry, separate event JSONL, metadata, geometry and validation report; the batch has a combined trial-summary CSV and exact collector source/hash.

The fixed virtual crossing has subject lanes on +X/+Y through (0,0), an approximately 40 m approach, central square [-3,3] m and virtual stop planes at route progress -6 m. Two default `etkc` cars differ in colour; four prior `simple_traffic` configurations are copied to the fresh scenario on fixed offset routes at +/-12 m. Background identities are recreated and linked to their prior source IDs in metadata; they are not asserted to be the same live objects after map reload. Seeds 903101/903102/903103 draw subject target speeds 5–10 m/s, background targets 4–8 m/s, initial speeds 0–2 m/s, blue/background launch delays 0–2 s and background route starts -65 to -45 m. Subject positions/headings and route assignments remain fixed. Polyline speed AI is used without prescribed arrival timestamps. Requested and measured initial speeds are stored separately; delayed cars are braked until launch.

Each trial has a 25 s maximum and records the full horizon at nominal 30 Hz (two physics steps at 60 Hz). Periodic data include identity/time, position/orientation, velocity and finite-difference acceleration, controls/gear, commanded AI state/settings, nearest-reference relative distance/radial speed, damage, virtual lane/deviation state and all spawn OOBB corners. Per-vehicle sockets are polled concurrently while physics is paused; the frame is completed before advancing physics. OOBB corners are retrieved in one game-engine Lua batch using the installed tech API's underlying `getSpawnWorldOOBB` method.

First sampled body-proxy overlap and downstream rear-proxy clearance define labels; damaged geometry is marked ambiguous. This is a spawn-OOBB proxy, not calibrated deforming-body occupancy. Contact detection is unavailable and stays null; damage changes are separate events, never verified contacts. Background routes do not enter the central square, so their central-zone non-arrival is expected. Virtual stop lines have no legal traffic-rule interpretation. Fresh trials reload vehicles, hold with realistic automatic shifting, check starting poses/damage, and initialize/measure speed. Validation checks IDs, sample count, time intervals, finite values and label consistency, reporting missing fields explicitly. See [[log]] for actual run outcomes and failures.

### Reusable CLI and speed measurements

The live `scripts/fresh_experiment.py` has parameterized trial count, duration, seed, host/port, requested telemetry cap (30/60/120 Hz), BeamNG deterministic speed factor (1–8) and output/config paths. Archived earlier collector sources remain unchanged. Event stop-duration detection uses elapsed simulation time instead of a hard-coded 15-frame window. AI launch events use the recorded frame timestamp. Inspect each run's sampling metadata for the actual rate.

The speed argument controls BeamNG's native deterministic speed factor. Graphics FPS is held at 60 during setup, capture, and cleanup, and left at 60 on exit. BeamNG advances `speed × 50 ms` per captured frame, so effective sampling is capped at `20/speed` Hz. At speed 2, this is 10 Hz; at speed 8, 2.5 Hz. At a 60 FPS cap the theoretical wall-clock ceiling is `3 × speed`; actual multiplier, measured sample rate and requested rate are recorded. Higher speed trades away temporal detail; 60 Hz simulation sampling is not supported by this per-frame API collector while accelerated. The recorder now accepts `--ai-aggression` with BeamNG's conservative/aggressive endpoint names or a numeric 0.3–1.0 value, applies it to each route-following vehicle and stores it per sample and in run metadata. Route-following telemetry uses BeamNG's built-in `manual` mode name. Background configs are durable project assets. Failures/interruption are saved, and output directories use new experiment UUIDs. Usage and limitations are in `scripts/BEAMNG_RECORDING.md` and [[operations]].

Optional `--dashboard-url http://127.0.0.1:3001` publishes the sampled state of all six vehicles to the Rust display-only observer. The crossing observer accepts the exact two subject and four traffic IDs, displays their measured positions on fixed bounds, and never emits recommendations. User-requested run `uriel_experiment/experiment_c040ffd3ca504ddbb96e2fc0a1f4dd21/fresh_001/` completed 25 simulation seconds with 251 samples per vehicle (1,506 rows), target 10 Hz and measured 1.598x wall-clock speed. Validation was PASS_WITH_LIMITATIONS with zero validation issues. Both subjects entered/cleared the virtual zone; red damage increase was 0 and blue was 6,249.84. Verified contact is unavailable, and spawn-OOBB proxy geometry remains uncalibrated; the damage increase alone does not verify a collision. Full CSV, metadata, events and exact source are retained in the local run folder.

Raw `telemetry.csv`, `arrival_labels.csv` and `events.jsonl` outputs are retained locally under the project output directories and excluded from Git by `.gitignore`. Small experiment summaries, metadata and collector sources remain reviewable and versionable.

## Offline model fitting

`scripts/train_arrival.py` reads per-trial telemetry without opening BeamNG. It recomputes virtual-square entry/rear-clearance timestamps from logged spawn OOBB corners, audits them against saved labels, and records target-specific damage/deviation exclusions and censored outcomes. It uses only the two central-crossing subject vehicles for model rows; the four offset traffic routes are audit-only. Training output, saved regressors and held-out predictions live under `runs/ml-arrival/<UUID>/`, which is ignored by Git alongside raw recordings. The command, feature list, grouped split, metrics and evidence are in [[ml-arrival-prediction]].

## West Coast LiDAR-only unknown-car crossing pilot

`scripts/collect_sensor_crossing.py` records three AI-driven West Coast runs with `thePlayer` as ego and a simulator-selected crossing vehicle. It reuses loaded `clone` if present, otherwise the first other vehicle, and asks BeamNG traffic to spawn a car when only the ego is loaded. A user run initially failed because `Damage` was attached twice; that duplicate was removed. The collector records 360-degree LiDAR point clouds, ego wheel speed and Advanced IMU readings; no camera is attached. Raw sensor files and a sensor index go under `runs/sensor-crossing/<run-id>/trials/`; exact simulator pose, velocity, model and damage go separately under `ground_truth/`. No detector/tracker or Rust sensor-track connection exists. The random traffic spawn and route are not proven to cross the intended junction. See [[sensor-crossing]]. These outputs are large and ignored by Git.

The separate braking run `runs/sensor-crossing/lidar-brake-4bd3f2c95a84/` completed three 30-second trials with red target 35 km/h and black target 60 km/h. Both cars used aggression 1.0; the collector logged 301 LiDAR frames per trial plus separate ground truth. Red reached 82.3 km/h despite the configured target. Damage values rose for both cars in the first two trials and for the black car in the third; these are damage readings, not verified contacts. This is a failed safety demonstration, not proof of obstacle avoidance. Its assumed 5.5 m/s² braking, reaction delay and margins are uncalibrated. Further use requires correcting the speed-limit behavior and doing a bounded preflight before trials.

## Randomized Small Grid LiDAR collection

The user-requested batch `uriel_lidar_experiment/experiment_20261017T180027Z_e64db751/` completed three seeded runs (781003–781005) with two perpendicular ETK subjects and four offset AI traffic cars. A 3-second preflight passed with limitations. Each 25-second trial has 751 complete 30 Hz frames × 6 vehicles (4,506 rows) and 500 LiDAR readings per subject at 20 Hz target; 59/60 red and 60/60 blue scans were nonempty during preflight. The trial clouds are separate compressed NPZ files, indexed independently of 30 Hz state CSV. The combined directory is about 1.54 GiB and remains under the ignored project-local experiment folder.

Both subjects recorded entry and rear-proxy clearance in all trials. Subject damage was zero in trials 1–2; trial 3 recorded increases of 2,784.127 red and 7,224.108 blue, making that trial's proxy event labels ambiguous. Background cars also show damage changes; none are verified contacts. The experiments use virtual Small Grid lane coordinates and do not validate real road rules, object detection, safety, or the conflict controller. See [[sensor-crossing]] and [[log]].

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


## [2026-10-18] Saved adjacent-road setup

Saved the live red `thePlayer` ETK K-Series and black `clone0` midsize placements/configuration in `scenarios/west_coast_adjacent_navgraph_20261018/`, with native scenario files installed in BeamNG's West Coast USA user folder. A live recheck matched saved positions within 0.4 mm.

A subsequent live editor-state inspection found both Drive Path Editor splines, correcting the earlier incomplete capture. `drive-path-session.json` now preserves the native editor session, including route node sequences, per-node speeds, AI settings and runtime vehicle links. Red spline 2 follows `DR371_4 → junction1_wp25 → DR360_2 → tunnel_city_B_6 → tunnel_city_A_58 → DR323_2`; black spline 1 follows `tunnel_city_A_58 → DR323_2 → junction1_wp25 → DR360_2`. Every named graph node exists in the current map. `manifest.json` maps each spline to a stable vehicle name and records node coordinates. After reloading/respawning cars, relink numeric vehicle IDs in the editor. No AI was started and route execution remains untested.


## [2026-10-18] Live saved-route trial

User authorized one trial on the saved West Coast Drive Path node sequences. `scripts/run_saved_navgraph_trial.py` connected to the placed cars, used native waypoint AI with the saved 0.3 aggression, lane driving/avoid-cars flags and per-node speeds, and recorded red LiDAR + wheel speed/IMU without cameras or Rust. A ground-truth damage/proximity guard is separate from perception; this is not LiDAR-driven stopping. Run `runs/sensor-crossing/navgraph-trial-5a063eb59f06/` stopped on the damage guard at 22.7165 simulation seconds: 182 paired state frames, 91 LiDAR frames, red damage increase 0 and black increase 6.58238. Minimum sampled reference separation was 72.2499 m; verified contacts remain unavailable, so damage cause is unclassified. Neither car reached its endpoint proximity condition. Cleanup paused physics, disabled AI and applied brakes. This is an incomplete route trial, not collision-free acceptance or a completed arrival-training group.


## [2026-10-18] repeat | Native AI saved-route trial

At the user's request, restored both cars to the saved transforms with reset and ran the saved navgraph waypoint sequences with BeamNG native AI, without Rust or cameras. Run `runs/sensor-crossing/navgraph-trial-69e3eabd7217/` reached its 45.1165-second time limit, recording 424 paired state frames and 178 red LiDAR frames plus wheel-speed/IMU. Minimum sampled car-reference separation was 44.9211 m. Damage increases were red 0 and black 0.971509, below the 1.0 guard threshold but not zero; verified contact/cause remains unavailable. Neither endpoint proximity condition was observed. Cleanup paused physics and disabled/braked both AIs. This is a full recording horizon with unfinished routes, not a collision-free or completed-route acceptance result.


## [2026-10-18] trial | Saved West Coast routes with four traffic cars

Added `--traffic` and `--reset-start` to `scripts/run_saved_navgraph_trial.py`, then executed the user-authorized repeat with four background cars (`clone1`–`clone4`). The traffic manager was explicitly restricted to background cars; both subjects kept their saved waypoint AI routes. Run `runs/sensor-crossing/navgraph-trial-0aa71001e54c/` recorded 204 paired state/traffic samples and 204 red LiDAR frames plus wheel speed/IMU over 45.1500 simulation seconds. Minimum subject-to-subject reference separation was 48.0147 m; minimum sampled subject-to-traffic reference separation was 4.8906 m. Subject damage increases: red 0, black 0.242175 (below guard threshold); background damage was not monitored and verified contacts remain unavailable. Both endpoints were unfinished at timeout. Cleanup paused physics, stopped background traffic and disabled/braked subject AIs. No cameras or Rust were used. Syntax and whitespace checks passed. Traffic spawn is unseeded; this is not a collision-free acceptance result.


## [2026-10-18] implementation | Configurable saved-route trial batches

`scripts/run_saved_navgraph_trial.py` now accepts positive `--trials N` (default 1). Every trial resets subject cars by default, reconnects after cleanup, and saves separate trial directories plus a batch summary under ignored `runs/sensor-crossing/navgraph-batch-<id>/`. `--traffic 4` retains the optional background traffic mode; existing background cars are reused, participants restricted to the requested count, and traffic reset between trials. Guard-stopped attempts remain recorded; setup/API errors stop the batch with partial failure reports. `finished` is an attempt-count status, not a safety or endpoint pass. Offline mocked orchestration checked three-trial execution, reset/traffic arguments, fail-fast reporting and invalid inputs; syntax/help/whitespace checks passed. No live BeamNG trial was run for this change. Repeated fixed configurations must stay grouped for ML evaluation.


## [2026-10-18] trial | Reload saved scene and run with traffic

The user requested another scenario run. First attempt `navgraph-batch-73f9c68a87ea` stopped with zero frames because BeamNG was at the menu (empty mission filename). Loaded the saved native West Coast scenario and verified `thePlayer`/`clone0` present. Retried with `--trials 1 --traffic 4`: `runs/sensor-crossing/navgraph-batch-1fa2070b1469/trial-001/` stopped on the damage guard at 24.1135 simulation seconds, recording 112 paired subject/traffic state frames and 111 red LiDAR frames plus wheel speed/IMU. Red damage increase was 0, black 9.37181; minimum subject reference separation was 53.7534 m. Verified contacts/cause are unavailable; neither endpoint was observed. Four background traffic IDs were clone/clone1/clone2/clone3. Cleanup paused physics, stopped traffic and disabled/braked subject AIs. No Rust or cameras used; this is an incomplete trial, not collision-free acceptance.


## [2026-10-18] repeat | Saved AI routes with traffic

User-authorized one-trial repeat using `--trials 1 --traffic 4` recorded `runs/sensor-crossing/navgraph-batch-b6038d1d7356/trial-001/`: 45.0480 simulation seconds, 208 paired subject/traffic state frames and 207 red LiDAR frames plus wheel-speed/IMU. Minimum subject reference separation was 47.3101 m. Damage increases were red 0 and black 0.233165; verified contacts/cause remain unavailable. Neither endpoint proximity condition was reached. Cleanup paused physics, stopped traffic and disabled/braked both subject AIs. This is a completed recording horizon with unfinished routes, not collision-free acceptance. No Rust or cameras were used.


## [2026-10-18] repeat | Saved AI routes stopped on damage guard

The requested one-trial repeat with four background traffic cars saved `runs/sensor-crossing/navgraph-batch-179ddcaa2152/trial-001/`. It stopped at 22.6665 simulation seconds on black damage increase 5.16970; red damage increase was 0. Recorded 105 paired subject/traffic state frames and 104 red LiDAR frames plus wheel-speed/IMU. Minimum sampled subject reference separation was 68.4933 m; verified contact/cause remains unavailable and neither endpoint was reached. Cleanup paused physics, stopped traffic and disabled/braked subject AI. No Rust or cameras used. This incomplete attempt is not collision-free acceptance.


## [2026-10-18] repeat | Saved-route traffic recording horizon

User-requested single-trial repeat with four AI traffic cars saved `runs/sensor-crossing/navgraph-batch-b1eaa8a831c5/trial-001/`: 45.1510 simulation seconds, 204 paired subject/traffic state frames and 204 red LiDAR frames plus wheel-speed/IMU. Minimum sampled subject reference separation was 47.2709 m; damage increases were red 0 and black 0.0509927. Verified contact/cause remains unavailable; neither endpoint proximity condition was reached. Cleanup paused physics, stopped traffic and disabled/braked the subject AIs. No Rust or cameras used. This completed recording horizon is not completed-route or collision-free acceptance.


## [2026-10-18] scenario and trials | Updated two-car-only editor routes

The user requested saving the newly positioned red/black cars and current graph routes, then three trials without the extra cars. Captured live poses/configuration and two linked editor splines (`red`: junction1_wp25 → junction1_wp3; `bllck`: tunnel_city_A_59 → DR323_3) into `scenarios/west_coast_red_black_20261018/`, installed its native scenario, and verified all node IDs. Preserved the earlier scenario separately. Removed the four previously generated traffic cars and verified only `thePlayer`/`clone0` remained. Added `--scene` to the runner and made the new saved scene its default; syntax/whitespace checks passed.

Executed `--scene scenarios/west_coast_red_black_20261018 --trials 3 --traffic 0`, saving `runs/sensor-crossing/navgraph-batch-fc0e932f6981/`. Trial 1: 45.1015 s, 308 state frames/181 LiDAR frames, red endpoint observed/black not, minimum subject reference separation 29.5698 m, red damage increase 0/black 0.368478. Trial 2: 15.0590 s, 121/61 frames, both endpoint proximity conditions observed, separation 28.4645 m, damage 0/0.372699. Trial 3: 14.9510 s, 120/60 frames, both endpoint proximity conditions observed, separation 29.4206 m, damage 0/0.321626. Total: 302 red LiDAR frames with wheel-speed/IMU and separate simulator ground truth. These are endpoint proximity results, not verified route compliance or collision-free acceptance; verified contacts remain unavailable. Cleanup paused physics and disabled/braked both AIs. No Rust, cameras or background traffic were used.


## [2026-10-18] attempt | ETK/MD70 speed-capped impact run

Added configurable red/black route speed caps and collision launch delay to `scripts/run_saved_navgraph_trial.py`; the runner now warms damage sensors after reset and checks that red stays near its saved pose during the truck lead-in. Requested trial used red 60 km/h, black 25 km/h and 12.5 s delay against `scenarios/west_coast_red_etk_md70_20261018/`. Initial run `runs/sensor-crossing/navgraph-batch-8f806eecac87/trial-001/` stopped on the first sample with the unstable baseline (red damage delta 24,504; black 24.3). After warm-up, `navgraph-batch-dd1be8fb3a1b/trial-001/` still produced an implausible first sample: the red was about 180 m from its saved position, red damage delta 39,811, black delta 0, and car-reference separation 282 m. Subsequent runs `navgraph-batch-793e740a0b53` and `navgraph-batch-d5cc29dc08ff` aborted before collecting telemetry because red drifted more than 3 m before release, including with AI `stopping` mode. No valid impact or speed-cap adherence is established. Cleanup pauses BeamNG and brakes/disables participant AIs. Static Python compile/help and whitespace checks passed; no ML label should be derived from these invalid/aborted runs.
## Extended user-assigned crossing route trials

On 2026-10-18, user-authorized three-trial evidence was recorded in `runs/extended-90-three-f94a7eda46/`: per-trial target speeds/routes, JSONL measured state/electrics/damage, summaries, source snapshot and final state. Both cars were existing Vivaces and routes came from the live editor. All three hit the 50 s simulation cap; only clone13 reached its destination threshold. Zero measured new damage does not establish successful two-car crossing. Labels are not training eligible. See [[operations]] for speeds and limitations. The named scene/configuration/route save now exists under `scenarios/extended-90-degree-data-collection/`.


## Collector update: saved editor routes and randomized pilot settings

On 2026-10-18, updated `scripts/collect_west_coast_arrival_trials.py` to consume the named editor-session snapshot and its per-car NavGraph waypoint lists. It randomizes subject target speeds and launch delays with CLI bounds/seed, records routes in metadata, uses AI car avoidance, and retains damage and no-motion stop conditions. Replaced the BeamNG vehicle-info lookup with a lightweight GE Lua inventory query to avoid the API path that previously timed out. Syntax compilation and CLI help both completed; no live collection was run during this implementation. Background traffic sampling/spawning remains the next collection feature. Labels remain provisional and training-ineligible. See [[operations]].


## Trial on the updated graph routes

A user-requested one-trial batch using the refreshed route snapshot is in `runs/west-coast-arrival-00e9ea6f19/`. The no-motion watchdog stopped it after 12 simulated seconds when clone13 had moved less than 0.5 m; neither vehicle entered the provisional junction zone and measured damage increase was zero. It is an invalid/incomplete run, not a successful crossing or training sample. A later relaunch attempt did not start because BeamNG was not listening on port 25252.


### Interrupted three-trial telemetry batch

Requested three randomized telemetry trials on the saved routes (seed 45, physics factor 4). The first attempt `runs/west-coast-arrival-0e2395a651/` had a frozen state clock and was interrupted; a brief resume/pause check restored advancing physics time. The restarted batch `runs/west-coast-arrival-60a81eea32/` recorded 189 samples per vehicle over 37.6 simulated seconds (22.31 wall seconds), then stopped on clone12 damage increase 3445.848. Clone13 damage increase was zero; neither car entered the provisional junction zone. Trials 2 and 3 were cancelled by the damage guard. Left the damaged scene paused for inspection; labels remain training-ineligible.


### Latest route refresh and mixed-model pilot

The model pilot helper scripts/collect_west_coast_vehicle_pilot.py reuses the recorder with explicit Vivace/ETK 800/Covet configurations and records model/configuration identity. The first requested three-run pilot (runs/west-coast-model-pilot-1db31df233/) stopped after one Vivace/ETK run at 33.0 simulated seconds on clone12 damage increase 3428.493; clone13 entered/cleared the provisional zone with zero damage increase. No second or third vehicle combination was executed. The helper preserves the exact user editor save separately from its audited ground-route overrides. Python syntax checks passed before the live pilot. The recorder now supports automaticGearbox Drive selection, model/configuration fields in group metadata, vehicle_model in CSV, and aborts after five frozen-clock samples. Its original command-line main still requires Vivaces; mixed-model operation uses the helper.

Refreshed the named scene snapshot from the latest live editor state: clone12 now uses junction1_wp3 to junction1_wp19; clone13 still uses tunnel_city_A_58, Bridge13_A, DR323_2, tunnel_city_A_59, Bridge13_B. Preserved the exact selected route order and actual Vivace/ETK 800 configurations. Upright starts now use the first connected road segment rather than aiming directly at elevated selected waypoints. The requested single run is runs/west-coast-live-route-7978196760/: 165 samples per car, 32.8 simulated seconds, 32.53 wall seconds, clone12 damage increase 2711.938, clone13 zero damage increase and no provisional junction entries. The damage guard stopped the run; cleanup reported no errors and left physics paused. Telemetry effective sampling was 5 Hz at speed factor 2; nominal launch schedule times differ from measured simulation time, so they are not calibrated event labels.

All listed West Coast labels remain provisional and training-ineligible.


### Verified correction: exact editor paths

Diagnosed the route-following failure against installed BeamNG source and a live graph comparison in `runs/route-diagnosis-f9b79fe438/path-comparison.json`: the editor expands nodes with direction penalties disabled, while waypoint AI with lane following enabled chooses legal-direction detours. The blue start-to-end path was five nodes in the editor but nineteen in the lane-aware planner. The selected node order also doubled back and included bridge detours. Updated the recorder to expand the editor road graph once and pass native `ai.driveUsingPath{path=...}` with lane replanning off and car avoidance on. It reads back and checks the actual AI path, uses measured simulation time for launch scheduling, and accepts the model stored in the scene instead of requiring Vivaces. Corrected both live editor routes to one ordered ground-level crossing, populated their visible geometry, and saved both the project snapshot and BeamNG `/gameplay/data.json`. Earlier route definitions are preserved with the run evidence. This chosen closed crossing traverses the blue road contrary to its legal one-way metadata; ordinary traffic-aware routing remains separate work.

Live verification `runs/west-coast-exact-path-b9530c2a1b/` recorded 131 samples per car over 26.0 simulation seconds / 17.0 wall seconds. Both AI path readbacks exactly matched their expanded graph paths. Clone12 entered/cleared the provisional zone at 12.8/14.8 s and clone13 at 23.6/26.0 s, with zero new damage for both. Maximum sampled 3D reference-point distance from each graph polyline was 0.422/1.475 m. Final independent readback confirmed both cars upright at their reset starts and zero damage; physics is paused. Eight focused Python checks passed, including a regression that forbids waypoint replanning in the exact-path command. This is a single successful two-car baseline, with provisional zone/body proxies and no training eligibility or general traffic acceptance.


### LiDAR trial and saved reboot state

Implemented scripts/collect_west_coast_lidar_trial.py: a seeded truck/commercial-vehicle draw on clone12 and passenger-car draw on clone13, 16-channel 360-degree roof LiDARs (70 m range), raw XYZ/RGB compressed NPZ frames, and an index linking polling times to vehicle telemetry. Acquisition timestamps are unavailable; repeated/empty readings are counted rather than presented as independent synchronized scans. Sensor mount heights are calibrated against reported world positions to clear each roof. Nine focused checks passed, including point-cloud round-trip and repeated-reading accounting. The first mount attempt runs/west-coast-lidar-55fb08fcf3/ stopped before launch; the corrected live run runs/west-coast-lidar-24a6633931/ used a delivery truck at target 21.575 km/h and a Covet at target 23.013 km/h (+10% over its random base). Both exact paths were verified, both cars cleared the provisional zone, and damage increase was zero. Recorded 134 telemetry samples per vehicle and 67 distinct nonempty LiDAR scans per vehicle: 1,734,442 truck points and 2,077,838 Covet points, approximately 38.3 MiB total evidence. All 134 NPZ scans were read back with finite XYZ and matching RGB counts. Sensors were removed after recording; their mount/configuration definitions are saved and will be recreated on the next collection run. Physics is paused and the vehicles were reset; cleanup reported no errors.

The user subsequently requested a 35% increase from the latest black-route trial speed, followed by saving for a PC restart. Set the black editor route limit to 31.067 km/h (previous 23.013), wrote and read back BeamNG /gameplay/data.json, and refreshed scenarios/extended-90-degree-data-collection/extended-90-degree-data-collection.json with the current delivery-truck/Covet configurations, poses, graph links, LiDAR definitions and persistent collection settings. The cumulative random-base multiplier is 1.485; the next default seed is 9304. The LiDAR runner now reads and preserves those saved settings, instead of reverting to its earlier 1.1 multiplier. Syntax compilation succeeded. Save backup/readback/manifest are in runs/scene-save-d450b277b6/. No additional trial or collection was started after this speed change. The 31.067 km/h setting has not yet been physically verified; the user intends to resume after reboot.


## Combined GPU training from teammate and local recordings

On 2026-10-18, the user supplied extracted Downloads data and authorized immediate GPU training. `scripts/train_combined_arrival_gpu.py` trained XGBoost entry and rear-clearance regressors on the RTX 4060 (`cuda:0`). The retained final artifact is `runs/ml-arrival/combined-gpu-cf2bc118ec/`; model files are `models/entry.ubj` and `models/clearance.ubj`. It audited local and teammate Small Grid telemetry plus exact-path local West Coast runs, rejected incomplete/damaged/incompatible records and exact-content duplicates, and joined repeated Small Grid seeds/configurations before splitting. West Coast truck/car pairings remain whole split groups. Accepted source counts were 52 Small Grid trial folders (50 from Downloads and two local) plus 27 exploratory West Coast trials. Individual target damage/deviation exclusions further reduce examples.

Training used 8,073 entry examples across 22 groups and 7,568 clearance examples across 18 groups. Held-out tests used five independent groups per target: entry 2,256 rows / 23 trials, MAE 0.369 s / p95 1.442 s; clearance 2,200 rows / 18 trials, MAE 0.438 s / p95 1.954 s. Source-specific metrics and comparisons against distance/speed are retained in the evaluation report. Both serialized models were loaded again and CPU predictions matched the GPU model predictions within 1e-5. The final data audit, fit, model selection and evaluation took 10.65 seconds after dependency setup; XGBoost 3.4.1 was installed in the existing BeamNG Python environment. No simulator collection was launched during training.

These are explicitly exploratory models: West Coast radius/spawn-OOBB labels remain provisional and Small Grid uses different virtual-square geometry. Calibration and cross-scenario acceptance are still outstanding. The extracted `Downloads/runs/sensor-crossing` sensor format was not silently converted into ETA records; incompatible LiDAR experiment telemetry is excluded in the audit. No point clouds were used. Existing `ml_worker.py` expects sklearn joblib artifacts, so these XGBoost UBJ files require an explicit loader adapter before serving. No deployment or live control integration was performed.


### Post-reboot collection and telemetry-only switch

Restored West Coast USA, both saved subject poses and enabled native graph links, then collected at user-requested deterministic factor 2. The user subsequently disabled LiDAR. Added `--no-lidar` and `--speed-factor` to the truck/car trial runner, and completed ten further telemetry-only runs plus the initial telemetry-only switch run. All eleven reported both provisional junction clearances and zero damage. `runs/west-coast-telemetry-first-batch-manifest.json` accounts for at least three clean telemetry-bearing trials in each of eight truck/car pairs (some preceding runs also contain LiDAR). Recorded counts include four pickup/ETK and four van/Covet runs. The final scene was reset to saved starts; collection cleanup paused physics. The black-route saved limit remains 31.067 km/h and randomized collection uses multiplier 1.485 over its base draw. These recordings remain provisional for model evaluation; no calibrated training eligibility is inferred from crossing completion.


## Local matched-car perpendicular hybrid pass

On 2026-10-18, persistent remote WebSocket ping timings through the existing LinuxONE SSH tunnel were 316.9, 381.9, 298.9, 321.9 and 339.0 ms. This is much faster than new HTTP connection setup, but still crosses the bridge's 350 ms request limit; the user explicitly authorized running locally instead. The remote services were preserved.

`scripts/run_grid_hybrid_crossing.py` loads a fresh Small Grid scene with two matching Vivace 160 DCT configurations, red/blue paint, equal initial rest state and equal 8 m/s route targets on perpendicular approaches. It runs a separate local Rust hybrid server and portable-model worker, sends measured state, applies Rust speed caps, logs the full wire/state/control history, and pauses/brakes the cars on completion or a guard. Native AI car avoidance is disabled so its own avoidance does not substitute for Rust yielding.

The first attempt, `runs/grid-hybrid-8e53dbe9ae/`, was aborted by `conflict_braking_infeasible` before crossing. Recorded red speed kept increasing despite a falling Rust cap. Installed BeamNG Lua showed `set_line` inserts a fixed per-node manual speed (`manSpeed`), which takes precedence over the route speed limit. The runner now supplies native coordinate script points without per-node speeds, allowing the live global cap to control speed. Failed evidence is retained.

The corrected pass is `runs/grid-hybrid-49835329e2/`: both cars cleared after 14.4 simulation seconds, 145 frames / 290 vehicle rows, with zero reported damage for both. Rust yielded red while blue proceeded. At 4 s, red measured 2.22 m/s against a 2.22 m/s cap while blue measured 6.88 m/s; at 8 s, red was 2.23 m/s and blue 7.98 m/s. Red was released after blue clearance and reached 7.79 m/s at 14 s. Minimum sampled reference-point distance was 25.32 m. Telemetry, advice, wire timing, model versions, initial state and source scenario are retained in the run directory. This is one successful local hybrid demonstration, not a remote pass or general collision guarantee. Runtime test services were stopped; the final Grid Plane scene is paused with both cars beyond the crossing.

The paired comparison runner now publishes each two-car sample, with measured pose, velocity, heading, dimensions and damage, to the dashboard's display-only observer endpoint. Its baseline still creates no control client or coordination request; dashboard observation is separate from the hybrid's Rust command path. The dashboard displays either trial on its local grid and retains the final frame as disconnected. The source change was compiled, but no new live run was possible during this update because BeamNG API port 25252 was closed.

The user then requested two head-on trials for screen recording. Updated `scripts/beamng_headon_collision.py` to accept the already-loaded `red`/`blue` Vivace pair as well as its original IDs and map those IDs to dashboard red/blue markers. Both user-authorized Grid Plane cooperative-dodge trials ran against BeamNG port 25252 at 30 km/h from 110 m separation and streamed to the local dashboard. `runs/headon-dodge-ebd6b2c455/` and `runs/headon-dodge-ded15ce9e8/` each completed `passed_and_returned` in 41 samples, with zero measured damage increase and no cleanup errors. Minimum sampled reference-point separations were 7.217 m and 7.050 m. The simulator was paused after each run; the dashboard retains the second run as disconnected final telemetry. These are avoidance passes, not deliberate impact trials or general collision-safety evidence.

Another user-requested pair ran for recording immediately afterward: `runs/headon-dodge-37187ff5b7/` completed in 41 samples with zero damage increase and a 7.148 m minimum sampled reference gap; `runs/headon-dodge-095f404c6d/` completed in 42 samples with zero damage increase and a 7.259 m minimum sampled gap. Both were streamed to the dashboard and left paused at completion.

For the user's requested two-trial 90-degree Grid demonstration, the first launch stopped before movement because the baseline branch incorrectly tried to create a Rust control client. Fixed the baseline to use direct native AI commands only, and added `--no-dashboard` as requested. The successful pair is `runs/grid-comparison-62ce5ba2fe/`: uncoordinated baseline `runs/grid-baseline-f0c9d8046f/` reached the damage threshold at 7.4 simulated seconds (red 4175.430, blue 4203.463), with 2.905 m minimum sampled reference separation and neither car cleared. Local Rust/ML hybrid `runs/grid-hybrid-ac3c12386d/` yielded red, cleared both after 14.4 simulated seconds and measured zero damage increase for both; minimum sampled reference distance was 25.322 m. BeamNG is left paused on the controlled run. Damage threshold is measured; contact attribution is unavailable and the result does not establish general safety.


## Repeatable uncoordinated versus local hybrid comparison

`scripts/run_grid_crossing_comparison.py` runs two fresh matched Small Grid trials in order, using the calling BeamNG Python environment. First it passes `--baseline` to `scripts/run_grid_hybrid_crossing.py`, creating no Rust or model-worker process and commanding both perpendicular cars to 8 m/s without native AI car avoidance. The scene pauses on a damage threshold, is displayed for five wall seconds by default (`--pause-between`), then resets both configurations/poses into a fresh scenario for local Rust hybrid control. Both use matching Vivace 160 DCT configurations, different colors and equal initial rest/target settings. Each trial saves telemetry and a summary, and the wrapper writes a comparison manifest. Errors and controller fallback stop the sequence; the final scene is paused.

User-authorized execution on 2026-10-18 produced `runs/grid-comparison-01f1eced05/`. Baseline `runs/grid-baseline-7ba0f1d1c8/` stopped after 7.4 simulation seconds with red damage 4349.547 and blue damage 4449.945, minimum sampled reference separation 2.899 m and neither car cleared. Hybrid `runs/grid-hybrid-89803b0cbb/` yielded red and cleared both after 14.4 simulation seconds, with zero damage for both and minimum sampled reference separation 25.193 m. Damage is measured; verified contact attribution remains unavailable. This paired comparison supports this specific local configuration, not general collision prevention or a LinuxONE physical pass. Both trial sources were copied into the comparison directory.

Run again with `/home/vinnavan/Projects/beamng-autonomous/.venv/bin/python scripts/run_grid_crossing_comparison.py` while BeamNG's API is listening on port 25252. This loads fresh Small Grid scenes and intentionally runs the uncoordinated impact comparison before resetting for the controlled trial.
