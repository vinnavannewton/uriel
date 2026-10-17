---
title: "Arrival-time ML plan"
project: IBM-Uriel
updated: 2026-10-17
tags: [ibm, uriel]
---

# Arrival-time ML plan

Status: **offline supervised-learning pilot implemented and evaluated** with scikit-learn's `HistGradientBoostingRegressor`. It predicts remaining seconds to virtual-zone entry and rear clearance from existing Small Grid telemetry. It does not connect to BeamNG or control vehicles. Labels use spawn OOBB proxy occupancy, not calibrated deforming-body geometry; no live inference or Rust integration is implemented.

## Reproduce the local pilot

From the repository root, create the separate pinned ML environment and run the offline pipeline:

```bash
python3 -m venv .venv-ml
.venv-ml/bin/pip install -r requirements-ml.txt
.venv-ml/bin/python scripts/train_arrival.py --data-root uriel_experiment --output runs/ml-arrival --seed 42
```

Each invocation creates a UUID directory under the output parent. It contains the trial/label audit, grouped split manifest, feature schema, Python/package versions, validation candidates and selected model files, test predictions and evaluation report. The artifacts remain local under ignored `runs/`; raw telemetry remains in its source experiment folders and is ignored by Git. The saved regressors load with `joblib` in the recorded Python/scikit-learn environment, but no inference API has been defined.

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

## Evaluation and future integration

The first repeatable offline pilot is now available, but broader recordings still need varied gaps, speeds, traffic and driver response. Keep features restricted to information available at prediction time. Stopped and non-arriving cars need explicit handling; do not invent arrival labels. Continue splitting complete grouped runs rather than neighboring frames, then evaluate downstream waiting, completed crossings and contact/proximity outcomes after integration is authorized.

A small Python inference worker on the same LinuxONE host is recommended. Rust could send bounded feature batches and receive predictions, validity/status and model version. Framework, API schema and persistence format remain undecided. Add timeouts and defined degraded prediction/yield behaviour; unavailable inference cannot stall networking. The current local estimators have no serving contract, confidence calibration or deployed consumer.

## Sources

- [[sources]]: S5 sections 6–7, 14, 16; S10 local offline training run and implementation.
- Related: [[architecture]], [[coordination]], [[recording]], [[implementation-status]].
