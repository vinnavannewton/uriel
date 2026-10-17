---
title: "Running and deployment"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Running and deployment

## Deployment target update

S5 reports user-confirmed **Ubuntu 24.04 / IBM LinuxONE / s390x**; Fedora 44 KDE/x86_64 remains development context. Actual SSH access, allocation, installed packages and deployment are unverified. This supersedes earlier target-unknown wording; it does not prove the remote service exists.

Plan native locked release builds on the target during the permitted event window and validate Python native packages in the supplied s390x environment. Transfer source, JSON/CSV and configuration, not Fedora executables, `target/`, Python virtual environments or undocumented native memory dumps. Model transfer needs compatible versions and numerical verification. The proposed Python inference worker runs on the same LinuxONE instance; laptop inference merely displayed remotely is not platform inference.

S5's account/lab steps and build/test commands are preparation guidance, not instructions executed during this wiki update. Source: [[sources]] S5 sections 14–15. Related: [[ml-arrival-prediction]], [[event-preparation]].

Run from the IBM workspace:

```sh
cargo run
```

Open [local dashboard](http://127.0.0.1:3000). Builds require a suitable Rust toolchain and Cargo dependencies. The lockfile exists. Reported performance must eventually use a release build on the actual destination; no performance result is established now.

| Variable | Default |
|---|---|
| `ARC_BIND` | `127.0.0.1:3000` |
| `ARC_SCENARIO` | `scenarios/crossing-v1.json` |
| `ARC_RUN_DIR` | `runs` |
| `ARC_TOKEN` | Unset; optional bridge token |
| `RUST_LOG` | `arc_angel=info` |

The Rust process can run headlessly. A browser on an operator laptop displays its dashboard. No GTK/Qt desktop is required on the remote machine.

Earlier planning left the target unknown; S5 now specifies Ubuntu 24.04/s390x. Access and permitted ports remain unknown. An x86 Fedora executable cannot substitute for the target build.

The implementation has no TLS termination or supervisor unit. HTTP observation endpoints are unauthenticated; optional token validation protects only the bridge upgrade. Keep the localhost default until the remote access method is explicitly configured. Remote deployment needs authenticated access and encrypted transport or an agreed secure tunnel.

The previous local server launch was previously reported. Current process availability was not checked during wiki creation.

## Sources

## Local BeamNG connection helper

The repository root now contains [connect_beamng.py](../../../../connect_beamng.py). With the local Python environment activated, install `beamngpy` and run `python connect_beamng.py --home /absolute/path/to/BeamNG.tech`. Alternatively, `--existing` connects to an API-enabled local instance on port 25252; `--port` overrides the port. `BNG_HOME` can supply the installation directory. The helper disconnects after connecting and does not configure a scenario or control vehicles. It is not the Uriel telemetry/control bridge. Python AST syntax validation passed; simulator connectivity was not tested.

- [[sources]]: S1 PRD section 11, S2 decisions, S3 current code; [README](../../../../README.md).
- Related: [[protocol]], [[recording]], [[open-questions]].

### Live U-S01 placement

User-authorized local scene setup loaded `smallgrid` with red and blue `etkc` vehicles (`uriel_red`, `uriel_blue`). Live positions are approximately (-40,0,0.15) and (0,-40,0.15); measured horizontal headings are +X and +Y toward virtual centre (0,0). Simulation was paused with brakes applied and AI disabled. The generated `uriel_crossing_setup` scene needed a live red-heading correction; do not treat its saved initial rotation as a validated reset. This placement verifies API setup only, not coordination, data recording or training. See [[log]].

### Configurable crossing recorder

The reusable [fresh experiment script](../../../../scripts/fresh_experiment.py) accepts `--trials N`, BeamNG deterministic speed factor 1–8 and a requested telemetry cap. From an activated environment with BeamNG.tech already API-enabled on localhost:25252:

```sh
.venv/bin/python scripts/fresh_experiment.py --trials 10 --speed 2 --telemetry-hz 60
```

It reloads the same seeded six-vehicle Small Grid scene each trial. Background configurations are now project-local in `scenarios/smallgrid_background_configs.json`; no temporary snapshot is needed. Dependencies are in `requirements-beamng.txt`. See [recording instructions](../../../../scripts/BEAMNG_RECORDING.md) for options, outputs and limits.

Use the project's `.venv/bin/python` (or activate `.venv`) so BeamNGpy is available. Graphics FPS stays set to 60 throughout and after collection. `--speed 2` uses BeamNG's native factor 2 and captures at 10 Hz simulation time; `--speed 8` captures at 2.5 Hz. Requested and actual sample rates are stored separately. The earlier 60 Hz paced batch `uriel_experiment/experiment_c03ce1dbb91143a4b66cdb7f56c7fbef` ran at 0.333x because the value only paced the Python loop. Higher native factors accelerate simulation but reduce temporal detail; see [[recording]] and [[log]].
