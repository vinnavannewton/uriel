# Repeatable 90-degree crossing collection

From the Uriel folder, with BeamNG.tech already listening on localhost:25252:

```bash
.venv/bin/python scripts/fresh_experiment.py --trials 10 --speed 2 --telemetry-hz 60
.venv/bin/python scripts/fresh_experiment.py --trials 3 --ai-aggression aggressive
```

Defaults: three trials, 25 simulation seconds per trial, BeamNG speed factor 2, requested telemetry cap 60 Hz, first seed 903101. Each subsequent trial increments the seed. The graphics FPS limit is fixed at 60 throughout setup, recording, and cleanup. BeamNG's deterministic speed factor advances `factor × 50 ms` per rendered frame, so effective simulation-time sampling remains capped at `20 / speed` Hz: speed 2 records at 10 Hz, speed 8 at 2.5 Hz. The requested and effective rates are both saved in metadata.

`--speed` sets BeamNG's native integer deterministic speed factor (1–8), not a Python sleep/pacing target. At a 60 FPS limit, the theoretical ceiling is `3 × factor` simulation seconds per wall second; actual throughput depends on rendering and telemetry overhead and is measured for each run. Increase it to 8 for the highest factor, with 2.5 Hz simulation-time samples; use 2 for 10 Hz samples. This direct stepped API recorder cannot provide 60 Hz simulation-time telemetry at these accelerated factors. The script records requested/effective telemetry rates, achieved multiplier and wall time in metadata and the summary. Higher speed trades away sample resolution. The FPS limit remains 60 when the script exits.

## Parameters

```bash
python scripts/fresh_experiment.py --help
python scripts/fresh_experiment.py --trials 100 --duration 25 --seed 1000
python scripts/fresh_experiment.py --trials 1 --duration 1 --output runs/collector-checks
```

`--duration` is the maximum simulation time; the final horizon can differ by at most half a sample interval. `--speed` accepts integer BeamNG factors 1–8. `--telemetry-hz` accepts requested caps of 30, 60 or 120, but the effective rate is `min(requested, 20/speed)`. Graphics FPS is fixed at 60. Optional host, port, output-parent and background-config paths are available. No existing recording directory is reused. The simulator must have its BeamNGpy API enabled; the script connects to an existing instance and does not launch one.

`--ai-aggression` applies BeamNG's native AI aggression setting to all six route-following cars. It accepts the BeamNG UI endpoint names `conservative` (0.3) and `aggressive` (1.0), or any numeric value in the native 0.3–1.0 range; default is `conservative`. The trial summary and telemetry store the selected level/value. The route-following controller uses BeamNG's `manual` AI mode; inactive vehicles are recorded as `disabled`.

## Scene and data

Each trial reloads Small Grid with red/blue default ETK K-Series cars approximately 40 m from a virtual 90-degree crossing. Four background vehicles use the archived configurations in `scenarios/smallgrid_background_configs.json`; the script no longer depends on a temporary `/tmp` snapshot. Geometry and randomization ranges match the earlier fresh trials. Default seeds 903101/903102/903103 recreate their random parameter draws, without guaranteeing bitwise identical physical outcomes.

Every run produces `telemetry.csv`, `events.jsonl`, `metadata.json`, `geometry.json`, and `validation_report.json`. The new experiment UUID directory includes `trial_summary.csv`, exact collector source and background configuration. At speed 2 over 25 s, expect 251 frames per vehicle; at speed 8, expect about 63 frames per vehicle. API/setup failures are retained and reported. Ctrl+C preserves available files and pauses the scene. On exit, the script pauses the scene, disables its vehicle AI, requests brakes and leaves the graphics FPS limit at 60.

Entry and clearance remain world-spawn-bounding-box proxies. Damage can make labels ambiguous. Verified contact is unavailable and stays null. Initial acceleration is null. Commanded AI mode is labelled as commanded. These are BeamNG AI baseline recordings without Uriel coordination or ML training.
