---
title: "Arrival-time ML plan"
project: IBM-Uriel
updated: 2026-10-18
tags: [ibm, uriel]
---

# Arrival-time ML plan

Status: **offline trainer, localhost inference worker and optional Rust observe-only client are implemented**. The Rust client does not alter recommendations. Current checkout does not contain a sufficiently varied trained model or a live inference result, so the worker is not running and LinuxONE/BeamNG integration remains unverified. Labels use spawn OOBB proxy occupancy, not calibrated deforming-body geometry.

## Reproduce the local pilot

From the repository root, create the separate pinned ML environment and run the offline pipeline:

```bash
python3 -m venv .venv-ml
.venv-ml/bin/pip install -r requirements-ml.txt
.venv-ml/bin/python scripts/train_arrival.py --data-root uriel_experiment --output runs/ml-arrival --seed 42
```

Each invocation creates a UUID directory under the output parent. It contains the trial/label audit, grouped split manifest, feature schema, Python/package versions, validation candidates and selected model files, test predictions and evaluation report. The artifacts remain local under ignored `runs/`; raw telemetry remains in its source experiment folders and is ignored by Git. The inference worker loads `models/entry.joblib` and `models/clearance.joblib` from one completed run directory and verifies the feature schema, completed evaluation status and exact NumPy/scikit-learn/joblib versions before serving.

The implementation rebuilds entry and clearance events from spawn-OOBB corner coordinates against the virtual square `x,y ∈ [-3,3] m`, then checks recomputed timestamps against saved labels. It uses only subject vehicles. Offset background routes remain in the audit as expected non-arrivals and are excluded from this zone's training examples. Incomplete trials and failed validation are retained in the audit with exclusion reasons. A target is excluded when damage or route deviation occurs before that event; damage after entry does not invalidate the entry label. Non-arrivals stay right-censored with null event times and receive no regression target.

Rows are sampled at no more than 5 Hz from recorded simulation timestamps, without interpolation. The feature allowlist is route-relative distance to entry/rear clearance, forward speed and acceleration, past speed at 0.5/1 second, trailing 1-second speed mean/std, vehicle dimensions, and current nearest-vehicle distance/relative speed. Run IDs, seed, vehicle ID/colour, target event time and future outcomes are not inputs. Missing feature values remain `NaN` for the histogram-based estimator.

Repeated seeds and identical randomized route configurations across folders are connected into one split group. A fixed `GroupShuffleSplit` produces approximately 60/20/20 train/validation/test groups. Four validation candidates vary learning rate `{0.05, 0.1}` and leaf count `{7, 15}`; they use 200 iterations, 20 minimum samples per leaf, L2 `1.0`, no internal early stopping, and equal weight per trial. The selected model is refit on train plus validation and scored once on test groups. Metrics weight each trial equally. The physical baseline predicts route distance divided by positive forward speed; it is unavailable at or below 0.2 m/s. Models and baseline are compared on common moving rows, and stopped/slow model results are reported separately.

## Recorded pilot result

The local evaluation report at `runs/ml-arrival/pilot-20261017T141915Z-48132635/evaluation_report.json` discovered 58 trial folders. It accepted 48 completed, passing trials and excluded 10 failed/interrupted trials; it found no exact telemetry duplicates. Accepted data produced 3,150 pre-entry examples from 48 trial folders and 11 seed/configuration groups. Clearance produced 2,000 pre-clearance examples from 26 folders and 7 groups. Of 96 subject entry events, 95 were eligible and one was excluded for damage before entry. Of 96 clearance events, 52 were eligible; 39 were excluded for prior damage and five for damage plus route deviation. Censored times and excluded targets remain listed in the local audit.

| Target | Held-out test | ML MAE / p95, all rows | Common moving rows | Distance/speed baseline on same moving rows | Independent test groups |
|---|---:|---:|---:|---:|---:|
| Entry | 799 rows, 13 trial folders | 0.398 / 1.157 s | 742 | 5.357 / 19.169 s | 3 |
| Rear clearance | 238 rows, 4 trial folders | 0.470 / 1.670 s | 215 | 6.196 / 20.751 s | 2 |

The all-row ML results include stopped/slow observations; the distance/speed baseline covered 93% of entry rows and 90% of clearance rows. On stopped/slow rows the ML MAE/p95 are 0.769/2.011 s for entry (57 rows) and 1.423/3.434 s for clearance (23 rows), where the physical baseline is unavailable. Entry selected learning rate 0.1 and 15 leaves; clearance selected 0.05 and 15 leaves. Both models beat the baseline MAE and p95 on the common moving test rows.

This is an encouraging offline comparison on a narrow repeated-seed data set. Test sets contain only two or three independent groups, and clearance labels lose many trajectories to damage. Gather varied, clean scenario configurations and repeat held-out evaluation before using either model for decisions. These results do not establish a safety bound, collision reduction or generalization beyond the recorded setup.

## 2026-10-18 offline retraining

The user requested training within ten minutes. Using `.venv-ml`, `scripts/train_arrival.py --data-root uriel_experiment --output runs/ml-arrival --seed 42` completed in about seven seconds. It scanned 61 trial folders, accepted 50, and found no exact telemetry duplicates. Entry has 3,587 eligible pre-entry rows across 13 independent groups; the held-out set contains 1,069 rows from 16 trials and 3 groups. The saved model is `runs/ml-arrival/pilot-20261018T023331Z-1b27bbac/models/entry.joblib`.

Held-out entry MAE/p95 absolute error were 0.375/1.211 s over all 1,069 rows. On 941 common moving rows, the model scored 0.307/1.052 s versus 4.343/18.967 s for distance divided by speed. Stopped/slow rows scored 0.809/2.010 s (128 rows). This is a small grouped test on seeded Small Grid data, not a safety or live-control result.

The same training invocation did **not** fit a new clearance model: 2,499 eligible rows span 9 groups, but the fixed seed placed only one clearance-bearing group in validation. The report therefore has overall status `insufficient_data` and the command exits 2, while retaining the evaluated entry model. An older clearance model remains in the 2026-10-17 pilot, but this rerun does not update or revalidate it. The active West Coast LiDAR recorder was not used because its JSONL/NPZ format and route labels are not accepted by this Small Grid CSV trainer. Artifacts and diagnostics are in the run directory; nothing is integrated into the Rust server.

## Evaluation and future integration
The previously reported successful pilot and its model files were not present in the current checkout. A fresh run on currently available `uriel_experiment` found only two accepted unique trials, grouped into one scenario group for each target, so it returned `insufficient_data` and produced no `.joblib` models (`runs/ml-arrival/pilot-20261017T145311Z-c9d35d9e/`). This is insufficient for current model serving; retain the earlier metrics as historical evidence only until a reproducible completed artifact is available.

## Rust and Python worker contract

The optional worker listens on `127.0.0.1:3100` by default and uses one newline-delimited JSON request per TCP connection. It is intended to run on the same host as Rust; the ML port is not public. Set Rust's `ARC_ML_ADDR=127.0.0.1:3100` to enable calls. `deploy/uriel-ml-worker.service` runs `scripts/ml_worker.py` with models under `~/.local/share/uriel/ml/current`; the model directory must be installed before enabling that unit. Rust's `deploy/uriel.service` sets the optional address.

Request: `{"type":"predict_batch","features":[{"vehicle_id":"car-a","values":{...13 ordered names from the feature schema...}}]}`. Missing values are JSON `null` and become NumPy `NaN`; extra or missing feature names, invalid batches and more than 100 rows are rejected. Response includes `status`, `model_version` (the model run-directory name), and per-vehicle `entry_eta_s`, `rear_clearance_eta_s` and `status`. Rust verifies the response count and vehicle IDs, and abandons a call after 40 ms. Worker errors also trigger a five-second retry cooldown to avoid per-frame connection/log churn. A timeout or worker error omits the ML field while retaining the existing Rust plan. Values appear in `recommendation_batch.ml_predictions` and are recorded with the plan; they are telemetry only and do not affect reservations, speed caps or actions.

Rust derives route-relative distance/speed, speed history, dimensions, and nearest-vehicle measures from crossing-v1 state. Height is `null` because crossing-v1 does not transmit it. Speed history is sampled at 5 Hz. Use a model trained with this exact ordered feature schema; do not apply it to head-on maneuver-v2 or the separate collision observer.

## Evaluation and next steps

The first repeatable offline pilot is now available, but broader recordings still need varied gaps, speeds, traffic and driver response. Keep features restricted to information available at prediction time. Stopped and non-arriving cars need explicit handling; do not invent arrival labels. Continue splitting complete grouped runs rather than neighboring frames, then evaluate downstream waiting, completed crossings and contact/proximity outcomes after integration is authorized.

The worker and Rust consumer are now implemented behind the optional loopback address. Remaining work is to produce/recover a complete trained artifact, install compatible Python packages and model files on LinuxONE, check the 40 ms call bound there, then connect the local BeamNG bridge through the existing SSH tunnel for an observe-only crossing run. Prediction validity is not calibrated, and learned estimates remain outside vehicle control.

## Proposed LiDAR/camera crossing experiment

On 2026-10-17 the user asked how to repeat the 90-degree crossing without direct simulator vehicle locations. Proposed scope: onboard RGB cameras covering forward and lateral approaches plus 360-degree LiDAR; estimate objects, road geometry and motion in a vehicle-relative frame, then predict crossing occupancy. Wheel speed/IMU may supply ego motion if allowed; a strict camera/LiDAR-only experiment would additionally require visual/LiDAR odometry. Sensor timestamps, calibration and coordinate conventions must be checked before fusion. Simulator annotations, exact poses and bounding boxes may support separate labels/evaluation but must not enter the perception/decision inputs. Setup coordinates and BeamNG route-following AI must be disclosed as scenario scaffolding; using them does not demonstrate perception-based steering.

Start with a visible marked intersection and clear sight lines at real-time speed, measure actual camera/LiDAR rates, and record synchronized raw measurements, estimated tracks, uncertainty, latency and separate ground truth. A blank Grid Plane does not visually define the earlier virtual square. Unknown/occluded road space cannot be treated as clear. The existing 13-feature regressors use simulator-derived geometry and motion; using estimated replacements requires matching semantics and fresh evaluation/retraining. Rust would need a versioned track/prediction contract, crossing identity, frame registration where tracks are combined, uncertainty and stale-data handling. No sensor pipeline or control integration was implemented or run for this proposal.

Capabilities checked against official [LiDAR documentation](https://documentation.beamng.com/beamng_tech/sensors/lidar/) and [camera documentation](https://documentation.beamng.com/beamng_tech/sensors/camera/): vehicle-mounted sensors, 360-degree LiDAR, RGB/depth/annotation outputs and configurable updates are available. Depth and annotation are optional privileged simulator outputs and are excluded from the proposed RGB-plus-range inputs. The first recorder implementation is tracked in [[sensor-crossing]].

## Sources

- [[sources]]: S5 sections 6–7, 14, 16; S10 local offline training run and implementation.
- Related: [[architecture]], [[coordination]], [[recording]], [[sensor-crossing]], [[implementation-status]].
- Related: [[architecture]], [[coordination]], [[recording]], [[implementation-status]].


## Combined GPU training from teammate and local recordings

On 2026-10-18, the user supplied extracted Downloads data and authorized immediate GPU training. `scripts/train_combined_arrival_gpu.py` trained XGBoost entry and rear-clearance regressors on the RTX 4060 (`cuda:0`). The retained final artifact is `runs/ml-arrival/combined-gpu-cf2bc118ec/`; model files are `models/entry.ubj` and `models/clearance.ubj`. It audited local and teammate Small Grid telemetry plus exact-path local West Coast runs, rejected incomplete/damaged/incompatible records and exact-content duplicates, and joined repeated Small Grid seeds/configurations before splitting. West Coast truck/car pairings remain whole split groups. Accepted source counts were 52 Small Grid trial folders (50 from Downloads and two local) plus 27 exploratory West Coast trials. Individual target damage/deviation exclusions further reduce examples.

Training used 8,073 entry examples across 22 groups and 7,568 clearance examples across 18 groups. Held-out tests used five independent groups per target: entry 2,256 rows / 23 trials, MAE 0.369 s / p95 1.442 s; clearance 2,200 rows / 18 trials, MAE 0.438 s / p95 1.954 s. Source-specific metrics and comparisons against distance/speed are retained in the evaluation report. Both serialized models were loaded again and CPU predictions matched the GPU model predictions within 1e-5. The final data audit, fit, model selection and evaluation took 10.65 seconds after dependency setup; XGBoost 3.4.1 was installed in the existing BeamNG Python environment. No simulator collection was launched during training.

These are explicitly exploratory models: West Coast radius/spawn-OOBB labels remain provisional and Small Grid uses different virtual-square geometry. Calibration and cross-scenario acceptance are still outstanding. The extracted `Downloads/runs/sensor-crossing` sensor format was not silently converted into ETA records; incompatible LiDAR experiment telemetry is excluded in the audit. No point clouds were used. Existing `ml_worker.py` expects sklearn joblib artifacts, so these XGBoost UBJ files require an explicit loader adapter before serving. No deployment or live control integration was performed.


## Local XGBoost and Rust hybrid integration

On 2026-10-18, branch `vinn` fast-forwarded to `origin/main` commit `f36d049`, then its prior staged/unstaged/untracked work was restored. Four wiki conflicts were resolved by preserving both upstream and local content. The recovery stash `codex-preserve-vinn-before-main-ml-integration` is retained; no commit or push was performed.

`scripts/ml_worker.py` now loads the trained combined XGBoost UBJ models, validates schema/evaluation/version/model hashes, selects two-thread CPU inference and warms both predictors. Rust still has the 40 ms worker bound and five-second failure cooldown. `ARC_ML_MODE=hybrid` opts into learned timing in both `/ws/bridge` reservations and `/api/conflicts/evaluate`; default crossing behavior remains observe-only. Valid model estimates can widen the physical/input occupancy window (earlier entry, later clearance), with an experimental two-second allowance. Invalid or reversed timing and unavailable inference fall back to physics/input timing. Occupancy, braking feasibility and measured rear-clearance logic are retained. The new HTTP response includes additive `ml_predictions` and `ml_mode` fields. HTTP observations lack history, height and nearest-vehicle measurements; those model features remain missing. Rust nearest-relative-speed now uses radial velocity, matching the recorder feature convention.

A saved West Coast route export is `scenarios/extended-90-degree-data-collection/rust-crossing.json`. `scripts/run_arrival_hybrid.py` starts a worker and Rust process on unoccupied local ports, and stops its children on Ctrl+C. Commands, artifact contract and limitations are in `scripts/ARRIVAL_HYBRID.md`. It starts services, not simulator driving.

Validation: 38 Rust tests and four Python worker tests passed. An isolated socket integration loaded the actual combined models, obtained ten model-bearing Rust crossing responses (maximum local round trip 2.20 ms), exercised the HTTP conflict evaluator with accepted monitor verdicts, and verified that stopping the worker preserved Rust recommendations. Evidence is under `runs/ml-arrival/combined-gpu-cf2bc118ec/integration/`. Test services were stopped after verification. No live BeamNG hybrid trial or remote deployment was executed. The two-second allowance is not a calibrated prediction interval, West Coast labels remain provisional, and missing-feature behavior/geometry reference alignment require physical validation before acceptance.


## LinuxONE hybrid deployment and network blocker

On 2026-10-18, explicitly authorized SSH deployment to `linux1@148.100.77.240` succeeded using the existing Documents key; private key content was not transferred. The host is s390x with Python 3.12.3 and no XGBoost package. `scripts/export_portable_eta.py` exports regression trees and validates `scripts/portable_eta.py` inference against native XGBoost, including float32 comparisons/accumulation and missing branches. Both targets matched exactly on 500 mixed finite/missing test inputs. Portable model SHA256 and the same prediction fixtures are checked at worker load on LinuxONE. Inference needs NumPy and the existing Python dependencies, without XGBoost or a GPU on the target.

Source and portable models were staged in `~/uriel-releases/hybrid-cf2bc118ec/`, built natively with the existing Rust cache, and activated through the `uriel.service` hybrid drop-in plus `uriel-ml-worker.service`. The server loads the saved West Coast Rust route export and `ARC_ML_MODE=hybrid`; both listeners stay on remote loopback. Old service configuration and the running old executable were saved under the release's `rollback/`; `rollback/rollback.sh` restores the old executable/configuration and stops the new worker. No firewall or public port was opened.

Remote verification made ten actual HTTP conflict-evaluation calls through Rust to model `combined-gpu-cf2bc118ec`, all with accepted monitor results; maximum remote-local elapsed time was 4.97 ms. `/health` returned `ok`, and both systemd user services were active. Evidence was copied to `runs/ml-arrival/combined-gpu-cf2bc118ec/integration/linuxone-verification.json`. Four Python worker checks also passed after adding the portable loader. Deployment is verified, not a BeamNG physical pass.

A laptop SSH tunnel now exposes the remote dashboard at `http://127.0.0.1:3300`. Three measured HTTP health round trips took 1952.2, 2298.4 and 2806.1 ms. This exceeds the bridge's 350 ms request and 500 ms plan lease limits; a remote live-control run is blocked by current latency. Do not relax those guards merely to start cars. Resolve connectivity/control placement before a guarded two-car hybrid trial. Route geometry, braking, provisional labels and model uncertainty still require physical validation; deployment does not establish collision avoidance.
