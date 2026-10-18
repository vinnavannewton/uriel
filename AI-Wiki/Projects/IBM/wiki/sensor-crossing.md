---
title: "West Coast LiDAR-only unknown-car crossing"
project: IBM-Uriel
updated: 2026-10-18
tags: [ibm, uriel, sensors, crossing]
---

# West Coast LiDAR-only unknown-car crossing

Status: **West Coast LiDAR-only raw collection completed; 90-degree West Coast geometry unresolved; separate randomized Small Grid LiDAR experiment completed; no controller acceptance**. A live BeamNG API inspection on 2026-10-17 found `thePlayer` (user-identified red ego) and `clone` (user-identified black unknown), both ETK K-Series cars, on West Coast USA. Their saved positions are about 175.0 m apart. Their path directions differ by only 0.49° when treated as unoriented lines (the cars face nearly opposite directions), with about 12.4 m lateral offset. This is not evidence of the requested 90-degree crossing, so no intersection point was saved. The exact setup/ground-truth states are preserved in `runs/sensor-crossing/scene-snapshots/west-coast-live-20261017T154736Z.json`; they are setup/ground-truth data, not perception input. Camera-free collection `runs/sensor-crossing/run-cb772b417eba/` completed 3 × 151 LiDAR frames and 302 ground-truth rows per trial. Minimum simultaneous car separation was 36.63 m; damage remained 0.0. The separate LiDAR braking runner is implemented but lacks calibrated stopping performance and verified live acceptance.

## Run after the scene is ready

Load West Coast USA and make sure `thePlayer` is present in the current mission. The ego should be at the approach for waypoint `DR193_2`. The script uses loaded `clone` if available, otherwise the first other loaded vehicle; if only `thePlayer` is loaded, it requests one random car from BeamNG traffic and stops the traffic controller before setting that car's AI route to `DR602_5`. These waypoints are inherited from `collect_traffic_trials.py`. The traffic spawn position and resulting route still need a live visual preflight; traffic spawning does not guarantee that the selected car begins close enough to the intersection to complete a pass in 30 seconds.

From the repository root:

```bash
./.venv/bin/python scripts/collect_sensor_crossing.py
```

The script requires BeamNG.tech running and reachable on localhost port 25252 (or `--launch` with `--home`). It checks that the active map is West Coast USA and that the ego exists, then reuses or requests a second car. It pauses the scene on exit. Defaults are three 30-second trials at 60 Hz deterministic physics and 5 Hz LiDAR frames. The seed, speeds, delay, selected vehicle ID/model/spawn source, simulator/BeamNGpy details and script hash are saved in metadata. A spawned traffic car remains in the scene after collection and may be reused by a later invocation.

## Captured data and separation

The ego receives only a 360-degree LiDAR for perception. The recorder also attaches Advanced IMU and Electrics for ego motion; wheel speed is auxiliary and is not another-vehicle perception source. Sensor frames contain compressed point clouds, point count, ego wheel speed and controls, and IMU output. No camera is attached and no image data is written. The sensor stream contains no unknown vehicle ID, pose, velocity, model, bounding box or simulator labels.

All output is local and ignored under `runs/sensor-crossing/<run-id>/`. Compressed point clouds are stored separately from `sensor_index.jsonl`. Simulator pose, velocity, model and damage are written only under `ground_truth/` for later scoring. The ground-truth folder must never be included in perception or Rust decision requests.

## Current limits and next step

This is a raw sensor recorder, not a LiDAR detector or tracker. It does not yet send sensor-derived tracks to Rust. The standalone [[conflict-resolution]] evaluator accepts an assessment payload but does not do LiDAR preprocessing or connect to this collector. A perception adapter and sensor-track message contract with uncertainty/freshness handling are still needed before the unknown vehicle can drive a reservation decision. The saved simulator ground truth can later measure detection and arrival-time errors. A BeamNG traffic spawn is simulator-selected but its model, starting position and path are not proven to produce the requested perpendicular pass.

Camera-free run `runs/sensor-crossing/run-cb772b417eba/` completed three 30-second trials with 151 LiDAR frames and 302 ground-truth rows per trial. Total data size is about 461 MB with no images. Minimum same-frame car separations were 76.86 m, 36.63 m and 61.05 m; recorded damage stayed 0.0. This verifies raw sensor capture, not a close crossing or obstacle stop.

## Randomized Small Grid LiDAR experiment

`scripts/collect_lidar_intersection_experiment.py` implements the preserved three-trial request using the Small Grid map. It runs a 3-second validation preflight, then three randomized 25-second runs with fixed perpendicular red/blue ETK subjects plus four offset AI traffic vehicles. Vehicle state is recorded at 30 Hz and both subjects have 360-degree 80 m, 32-channel LiDAR configured for 20 Hz; the short validation displays scans, while trial clouds are saved separately. The collector records scenario seeds, all six vehicle states, footprints, route outcomes, damage, and separate ground-truth/event and binary cloud streams. There are no camera sensors in this experiment.

The completed batch is `uriel_lidar_experiment/experiment_20261017T180027Z_e64db751/`, seeds 781003–781005. Validation was `PASS_WITH_LIMITATIONS`: measured state rate was 29.9999986 Hz; all six vehicles moved; LiDAR returned 60 frames per subject (59 nonempty red, 60 nonempty blue) with roughly 58.7k–59.1k mean points. Each trial recorded 4,506 state rows (751 frames × 6 vehicles) and 500 LiDAR reads per subject, approximately 1,000 clouds per run. All subjects entered and rear-cleared the virtual zone in each run. The subject damage readings increased only in trial 3 (red 2,784.127; blue 7,224.108); damage is not verified contact, and those trial 3 labels are marked ambiguous. Trials 1–2 had no subject damage increase. Four background traffic vehicles had damage increases across the trials. `verified_contact` remains unavailable. The full ignored run occupies about 1.54 GiB; summaries/configuration remain reviewable.

This is an artificial virtual crossing on Small Grid, not a surveyed/painted intersection. LiDAR remains raw, not object detections/tracks; simulator IDs and ground truth are separate and must not be fed to perception. It does not exercise the Rust controller or establish safe multi-vehicle behavior. One earlier failed preflight and a resumable partial output were preserved separately; only the named complete batch is summarized here.

## LiDAR emergency-braking approach

`scripts/collect_lidar_braking_trials.py` configures the red ego for a 35 km/h target and the black unknown for 50 km/h by default; the completed user run below overrode the black target to 60 km/h. Aggression was 1.0. The red uses BeamNG `manual` waypoint AI until LiDAR reports occupied returns in a 1.8 m half-width forward corridor inside an assumed braking envelope; it disables AI and requests full braking, then resumes after clear frames beyond an 8 m hysteresis margin. The black uses `chase` AI with built-in avoid-cars enabled. The envelope assumes 5.5 m/s² deceleration, 0.3 s reaction time and a 5 m margin; these are not calibrated limits.

The completed run `runs/sensor-crossing/lidar-brake-4bd3f2c95a84/` recorded three 30-second trials with 301 LiDAR frames each and repeated brake/resume events. Ground-truth speed for the red reached 82.3 km/h despite its 35 km/h target; the black reached 61.6–61.8 km/h with a 60 km/h target. Damage readings increased for both cars in trials 1–2; trial 3 showed a large increase for the black car. Damage does not prove contact, but these results fail to establish safe braking and show that the red target was not enforced. Do not use this as a validated controller or repeat the run until speed limiting, braking response and route behavior are corrected and checked in a bounded preflight. This experiment is occupied-path detection, not an object tracker.

The saved start poses remain nearly collinear, so the run must be described as an approach-and-brake experiment, not a verified 90-degree turning encounter. Reposition both vehicles onto perpendicular approaches before making that claim.

## Sources

- [[sources]] S11: West Coast local collector; [[sources]] S13: randomized Small Grid experiment and raw request.
- Related: [[recording]], [[protocol]], [[ml-arrival-prediction]], [[implementation-status]].


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

## [2026-10-18] fix | Saved-route participant ID preflight

The user ran the three-trial command and the first attempt failed before collecting frames with `KeyError('clone0')`: the current BeamNG vehicle list did not contain that saved ID. The runner now resolves red/black IDs from saved roles, accepts `--red-id` and `--black-id` overrides, and reports the loaded IDs plus setup guidance before trial control if a participant is missing. Metadata records the actual live IDs. Four offline unit tests cover defaults, overrides, missing-car diagnostics and duplicate-ID rejection; Python compilation, help output and whitespace checks passed. This fix has not been tested against the live simulator; load the saved two-car scenario or provide its current IDs before retrying.

## [2026-10-18] trial | Three saved-route runs after participant reload

After the user asked to run the scenario, loaded the installed saved scenario through BeamNG, then used `scripts/run_saved_navgraph_trial.py --trials 3 --traffic 0`. Batch `runs/sensor-crossing/navgraph-batch-6b833c216195/` finished all attempts: trial state/LiDAR counts were 130/65, 152/64 and 125/63; all six endpoint-proximity flags were true. Observed minimum center-reference separations were 14.21 m, 31.95 m and 30.15 m. Red damage deltas were 0; black deltas were 0.642, 0.644 and 0.676, below the 1.0 stop threshold but nonzero. Verified contact data is unavailable, so these are completed-route-proximity runs, not verified collision-free results. The batch contains 201,238,938 bytes of local telemetry and sensor data. No background traffic, Rust, camera or LiDAR-driven braking was used; route control was native BeamNG waypoint AI.

## [2026-10-18] trial | Three saved-route runs with four traffic vehicles

The user requested the same saved-route run with background traffic. Reused four BeamNG traffic vehicles (`clone`, `clone1`, `clone2`, `clone3`) and ran `scripts/run_saved_navgraph_trial.py --trials 3 --traffic 4`. Batch `runs/sensor-crossing/navgraph-batch-6e0faed50d53/` recorded 84/83, 82/81 and 74/74 state/LiDAR frames. Both subjects reached endpoint proximity in all three trials. Minimum subject center-reference separations were 33.98 m, 34.37 m and 31.91 m. Nearest sampled traffic-to-subject center separations were 8.41 m, 8.24 m and 60.02 m. Red damage deltas were 0; black deltas were 0.635, 0.675 and 0.638. Verified contact data is unavailable, so collision-free behavior is not established. The batch contains 252,855,432 bytes (~241 MiB) of local data. It uses native waypoint AI, red-only LiDAR capture, no camera/Rust/LiDAR-derived control. Four background traffic vehicles were re-enabled and left moving after collection for the user's video.


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


## Saved ETK/MD70 speed-impact attempt

The user asked to raise the red ETK speed for an impact run with a black MD70. `scripts/run_saved_navgraph_trial.py` now accepts `--red-speed-kmh`, `--black-speed-kmh`, and `--collision-launch-delay-s`; it applies BeamNG native AI route speed limits, disables `avoid_cars` only in collision mode, records LiDAR/IMU/wheel-speed and separate simulator ground truth, and warms the damage sensor after reset. Run `navgraph-batch-dd1be8fb3a1b/trial-001` used red 60 km/h, black 25 km/h and a 12.5 s truck lead-in. Its first telemetry sample was already far from the saved start poses and showed implausibly large damage deltas (red 39,811; black 0); it is not valid evidence of a vehicle-to-vehicle impact. Follow-up runs `navgraph-batch-793e740a0b53` and `navgraph-batch-d5cc29dc08ff` aborted before telemetry when the red car drifted more than 3 m before its scheduled release. The earlier trial `navgraph-batch-8f806eecac87` used an unstable pre-warmup damage baseline and is also invalid. The intended speed cap is implemented, but the live controller/reset behavior prevents a valid impact result; actual speed-limit adherence and contact remain unverified. All batch data stays under ignored `runs/sensor-crossing/`.


## [2026-10-18] live check | Red car stalled during medium-traffic run

The user asked to check the red car during `runs/sensor-crossing/navgraph-hour-d50474577c27/`. The process remains active with its 1,800 s simulation-time target; the latest observed frame was 1067 at 940.4 s. Across the preceding samples, red stayed near its saved start (about `[-432.85, 681.43]` m) with speed below 0.3 km/h. At that sample, background `clone2` was about 1.8 m from red and `clone1` about 11.4 m forward along red's heading. This is evidence consistent with traffic blocking the start/approach, but does not prove the cause. The run continues and will contain stalled-red frames; route progress and trial completion are not established. No live vehicle control was changed during this check.

Follow-up read during the same check reached frame 1193 at 1,052.8 simulated seconds; red remained at approximately `[-432.85, 681.43]` m and below 0.3 km/h. The recorder was still running at that point.

The user then requested removing nearby traffic and restarting/continuing the run. While preserving all six traffic participants and the active recording, called BeamNG's `traffic.reset()` API, which relocates active traffic away from the player. The reset is annotated in the run's `metadata.json`. Red resumed movement and both subject cars reached their route endpoints in legs 28 and 29. The run then completed at 1,800.6 simulated seconds: 2,047 paired state/LiDAR frames, 2,047 clouds per subject, 44 route legs, six traffic vehicles, and a total folder size of 4,454,620,388 bytes (~4.15 GiB). Leg outcomes: 20 both-endpoint observations, 15 time limits with an endpoint unreached, 8 damage guards, and the final hour-complete leg. Earlier stalled-red frames remain in the dataset and must be excluded from route-progress learning; post-reset frames are a separate intervention condition. This format is not accepted by the current Small Grid ML trainer.
