# Local Rust + ETA model integration

Build `cargo build --offline`, then use the Python environment that has XGBoost 3.4.1:

```bash
/home/vinnavan/Projects/beamng-autonomous/.venv/bin/python scripts/run_arrival_hybrid.py \
  --models runs/ml-arrival/combined-gpu-cf2bc118ec \
  --scenario scenarios/extended-90-degree-data-collection/rust-crossing.json \
  --bind 127.0.0.1:3000 --worker-port 3100
```

The launcher refuses occupied ports, warms the model worker, runs Rust with `ARC_ML_MODE=hybrid`, and stops both children on Ctrl+C. Use `--scenario /path/to/exported-scenario.json` for the actual BeamNG route export. The default scenario is schematic. Starting these services does not start BeamNG or a driving trial.

Both `/ws/bridge` crossing reservations and `/api/conflicts/evaluate` can consume model timing. Hybrid mode only widens timing estimates: the earliest physical entry can move earlier, and physical clearance can move later. A fixed two-second allowance is experimental, not a calibrated prediction interval. Measured occupancy, rear clearance, braking checks and existing priority logic remain authoritative. Invalid timing, reversed ETA ordering, worker failure or the 40 ms timeout retains physical/input timing. Prediction failures trigger a five-second retry cooldown. The HTTP evaluator preserves a baseline safe hold before inference and exposes additive `ml_predictions` and `ml_mode` fields.

The HTTP observations omit speed history, body height and nearest-vehicle features; those inputs remain missing rather than fabricated. `/ws/bridge` supplies available speed history, projected dimensions and radial relative speed. Exact reference point and zone calibration remain outstanding for these exploratory models. Native tree training used the GPU; serving uses two CPU threads for small predictable batches and portability.

The worker supports both the existing sklearn/joblib artifact contract and these XGBoost UBJ artifacts. UBJ load checks the ordered feature names, completed exploratory evaluation status, XGBoost version and model SHA256, then warms both models. No models or services are deployed remotely by this launcher.

Local evidence: `runs/ml-arrival/combined-gpu-cf2bc118ec/integration/` contains socket wire records, HTTP evaluator output, worker-down fallback and service logs. The recorded packets are synthetic integration inputs; a live BeamNG hybrid drive remains unverified.


## LinuxONE hybrid deployment and network blocker

On 2026-10-18, explicitly authorized SSH deployment to `linux1@148.100.77.240` succeeded using the existing Documents key; private key content was not transferred. The host is s390x with Python 3.12.3 and no XGBoost package. `scripts/export_portable_eta.py` exports regression trees and validates `scripts/portable_eta.py` inference against native XGBoost, including float32 comparisons/accumulation and missing branches. Both targets matched exactly on 500 mixed finite/missing test inputs. Portable model SHA256 and the same prediction fixtures are checked at worker load on LinuxONE. Inference needs NumPy and the existing Python dependencies, without XGBoost or a GPU on the target.

Source and portable models were staged in `~/uriel-releases/hybrid-cf2bc118ec/`, built natively with the existing Rust cache, and activated through the `uriel.service` hybrid drop-in plus `uriel-ml-worker.service`. The server loads the saved West Coast Rust route export and `ARC_ML_MODE=hybrid`; both listeners stay on remote loopback. Old service configuration and the running old executable were saved under the release's `rollback/`; `rollback/rollback.sh` restores the old executable/configuration and stops the new worker. No firewall or public port was opened.

Remote verification made ten actual HTTP conflict-evaluation calls through Rust to model `combined-gpu-cf2bc118ec`, all with accepted monitor results; maximum remote-local elapsed time was 4.97 ms. `/health` returned `ok`, and both systemd user services were active. Evidence was copied to `runs/ml-arrival/combined-gpu-cf2bc118ec/integration/linuxone-verification.json`. Four Python worker checks also passed after adding the portable loader. Deployment is verified, not a BeamNG physical pass.

A laptop SSH tunnel now exposes the remote dashboard at `http://127.0.0.1:3300`. Three measured HTTP health round trips took 1952.2, 2298.4 and 2806.1 ms. This exceeds the bridge's 350 ms request and 500 ms plan lease limits; a remote live-control run is blocked by current latency. Do not relax those guards merely to start cars. Resolve connectivity/control placement before a guarded two-car hybrid trial. Route geometry, braking, provisional labels and model uncertainty still require physical validation; deployment does not establish collision avoidance.


## Repeatable uncoordinated versus local hybrid comparison

`scripts/run_grid_crossing_comparison.py` runs two fresh matched Small Grid trials in order, using the calling BeamNG Python environment. First it passes `--baseline` to `scripts/run_grid_hybrid_crossing.py`, creating no Rust or model-worker process and commanding both perpendicular cars to 8 m/s without native AI car avoidance. The scene pauses on a damage threshold, is displayed for five wall seconds by default (`--pause-between`), then resets both configurations/poses into a fresh scenario for local Rust hybrid control. Both use matching Vivace 160 DCT configurations, different colors and equal initial rest/target settings. Each trial saves telemetry and a summary, and the wrapper writes a comparison manifest. Errors and controller fallback stop the sequence; the final scene is paused.

User-authorized execution on 2026-10-18 produced `runs/grid-comparison-01f1eced05/`. Baseline `runs/grid-baseline-7ba0f1d1c8/` stopped after 7.4 simulation seconds with red damage 4349.547 and blue damage 4449.945, minimum sampled reference separation 2.899 m and neither car cleared. Hybrid `runs/grid-hybrid-89803b0cbb/` yielded red and cleared both after 14.4 simulation seconds, with zero damage for both and minimum sampled reference separation 25.193 m. Damage is measured; verified contact attribution remains unavailable. This paired comparison supports this specific local configuration, not general collision prevention or a LinuxONE physical pass. Both trial sources were copied into the comparison directory.

Run again with `/home/vinnavan/Projects/beamng-autonomous/.venv/bin/python scripts/run_grid_crossing_comparison.py` while BeamNG's API is listening on port 25252. This loads fresh Small Grid scenes and intentionally runs the uncoordinated impact comparison before resetting for the controlled trial.
