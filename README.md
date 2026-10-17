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

The source has been checked for compilation. Behavioural tests, BeamNG control calibration, fault trials, load measurements and LinuxONE deployment are deferred. The speed recommendations are advisory and must not be treated as collision prevention until the physical acceptance suite is run. In particular, stop/hold behaviour for a zero cap depends on the installed BeamNG AI controller.

## Project knowledge wiki

Open `AI-Wiki` as an Obsidian vault. Start at [the IBM / Arc Angel index](AI-Wiki/Projects/IBM/wiki/index.md). AI agents should read the root `AGENTS.md` and keep the wiki current after meaningful project work.
