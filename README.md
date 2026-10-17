# Arc Angel server

Rust coordination server and a read-only dashboard template for the Arc Angel PRD.

## Run locally

```sh
cargo run
```

Open `http://127.0.0.1:3000`. The bridge WebSocket is `ws://127.0.0.1:3000/ws/bridge`.

The dashboard's **Preview demo** button displays labelled example data without a connected bridge. Turn it off to view live worlds from the server. The frontend template is in `web/`.

The default scenario in `scenarios/crossing-v1.json` is a **schematic crossing**. Its coordinates are not calibrated to West Coast USA. Replace the route geometry, conflict-zone size and control limits after measuring a BeamNG scenario.

Configuration:

| Variable | Default | Purpose |
|---|---|---|
| `ARC_BIND` | `127.0.0.1:3000` | HTTP/WebSocket listen address |
| `ARC_SCENARIO` | `scenarios/crossing-v1.json` | Scenario file |
| `ARC_RUN_DIR` | `runs` | Experiment record directory |
| `ARC_TOKEN` | unset | Optional bridge Bearer token |
| `RUST_LOG` | `arc_angel=info` | Log level |

Each startup creates a run directory with `metadata.json` and `events.jsonl`. The latter records accepted telemetry, plans, acknowledgements, removals, rejected messages and disconnects. Do not send the token in JSON; when configured, pass it as an `Authorization: Bearer ...` header on the WebSocket upgrade.

## Bridge protocol

The first WebSocket message must be `hello`. Use the returned `session_id` in later messages. Every state batch contains all cars in the world at one simulator frame. See `examples/hello.json` and `examples/state_batch.json`. The server returns a `recommendation_batch` with simulation-time expiry. The bridge must also enforce its own wall-time expiry and local fallback.

The browser dashboard uses `/api/status`, `/api/worlds`, `/api/worlds/{id}` and `/api/scenarios/{id}`. It polls every 500 ms. Its `web/` files are intentionally plain HTML, CSS and JavaScript for the frontend team to replace.

## Current validation boundary

The source compiles; 9 Rust tests and 21 Python tests pass. A scoped, algorithm-only two-car Grid Plane head-on pass has been exercised through the Rust server. Broad physical acceptance, control calibration, fault/load suites, obstacle handling, ML and LinuxONE deployment remain unverified. In particular, brake acknowledgements did not prove a stop in the installed BeamNG arcade controller; the bounded demo pauses simulator physics on completion or failure.

## Integrated two-car Grid Plane demo

Rust's maneuver-v2 endpoint is `ws://127.0.0.1:3000/ws/headon`. The legacy crossing endpoint above remains version 1. V2 prepares fixed paired paths, waits for both controller acknowledgements and renews a 500 ms execution lease from fresh measured telemetry. Acknowledgements mean path commands were accepted; subsequent telemetry establishes motion.

With BeamNG.tech 0.39 running **Grid Plane / `smallgrid`**, its BeamNGpy server enabled on localhost:64256, and exactly the existing Vivaces `thePlayer` and `uriel_blue`, run:

```sh
python3 -m venv .venv-beamng
.venv-beamng/bin/pip install -r scripts/requirements-beamng.txt
```

Start `cargo run` in one terminal, then:

```sh
.venv-beamng/bin/python scripts/beamng_headon.py --run
```

This repairs and repositions those two cars, colors them red/blue, and executes Rust's paths at a target 30 km/h. Each moves to its own left, passes, and returns to the original line. The script applies paths once; subsequent plans renew the same maneuver rather than restarting BeamNG AI. It leaves the game paused. `--server-url` selects the server; `--standalone` explicitly selects the earlier Python-only baseline. Without `--run`, the script only prints that local baseline plan. There is no silent local fallback when Rust is unavailable.

## Two-car dodge with live dashboard

The historical filename `scripts/beamng_headon_collision.py` now runs a cooperative dodge rather than an intentional crash. With BeamNG.tech open on Grid Plane (`smallgrid`) and its server on localhost:64256:

```sh
.venv-beamng/bin/python scripts/beamng_headon_collision.py
.venv-beamng/bin/python scripts/beamng_headon_collision.py --run
```

The default command is a no-connection dry run. `--run` repositions the two matching red/blue Vivaces 110 m apart and selects paired open-grid paths using the existing Python planner. At the default 30 km/h both move to their own left, pass, and return to the original line. This prepared geometry requires 110 m separation and supports 10–36 km/h. It selects the correct DCT Drive/manual first-gear input and releases parking brakes before resuming physics. A failed launch, path deviation, predicted overlap, damage or completion stops the trial through simulator-pause cleanup. A timeout is recorded as incomplete; completion requires measured passing and return.

Measured state streams to `http://127.0.0.1:3001` by default. Refresh the dashboard with Preview demo off to see two red/blue dots on the grid. `--dashboard-url` selects another HTTP dashboard; `--no-dashboard` disables display delivery. Dashboard delivery errors abort the trial and pause the simulator. Rust displays observations only for this runner; Python plans the dodge and no ML model is involved. Run metadata, telemetry and summary are written under `runs/headon-dodge-<id>/`. The converted runner has source/protocol tests but has not yet been exercised in a new live trial.

Samples: [hello](examples/headon-hello.json), [state](examples/headon-state.json), [plan](examples/headon-plan.json). Full contract and limitations are in the [project protocol wiki](AI-Wiki/Projects/IBM/wiki/protocol.md). Bridge logs and Rust records remain under `runs/`; they are not yet a labelled ML dataset. Keep the localhost bind for this local-first demo. No remote deployment is configured.

Checks:

```sh
cargo test --offline
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
.venv-beamng/bin/python tests/check_headon_wire.py
```

The last command needs the local Rust server and exercises synthetic protocol messages, including legacy-v1 compatibility; it does not control BeamNG. The simulator bridge assumes empty, flat space, two matched cars and calibrated starting poses. It is not a general obstacle or late-emergency dodge controller, and has no simulator-side watchdog for Python process death.

## Project knowledge wiki

Open `AI-Wiki` as an Obsidian vault. Start at [the IBM / Arc Angel index](AI-Wiki/Projects/IBM/wiki/index.md). AI agents should read the root `AGENTS.md` and keep the wiki current after meaningful project work.
