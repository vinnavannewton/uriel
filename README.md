# Uriel

Cooperative vehicle conflict and road-hazard coordination for the IBM datathon project.

Uriel aims to combine a Rust coordination server, BeamNG simulation, arrival-time machine learning, and an operator dashboard. This repository currently contains the **historical Arc Angel prototype**: a Rust server and a read-only browser dashboard. BeamNG bridge integration, ML inference, and LinuxONE deployment remain planned work.

The Cargo package, environment variables, and parts of the UI still use the Arc Angel name.

## At a glance

| Component | Current status |
| --- | --- |
| Coordination server | Rust with Axum and Tokio; simplified route projection, reservations, and headway logic |
| Dashboard | Plain HTML, CSS, and JavaScript; read-only live view and labelled demo data |
| Bridge interface | WebSocket protocol and example messages; Python BeamNG bridge not included |
| Scenario | Schematic crossing; not calibrated to West Coast USA |
| Arrival-time ML | Planned; no trained model or evaluation results established |
| LinuxONE deployment | Planned; deployment and remote access not verified |

## Quick start

### Prerequisites

- A Rust toolchain with Cargo and support for Rust edition 2021.
- Access to the dependencies declared in `Cargo.toml`, or an existing local cache.
- A browser to view the dashboard.

### Start the server

Run from the repository root:

```sh
cargo run
```

Open [the local dashboard](http://127.0.0.1:3000). The bridge connects at `ws://127.0.0.1:3000/ws/bridge`.

Select **Preview demo** to explore labelled example data without a connected bridge. Turn it off to view live worlds supplied to the server. Demo data does not demonstrate simulator integration or coordination correctness.

### Configure the environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `ARC_BIND` | `127.0.0.1:3000` | HTTP and WebSocket listen address |
| `ARC_SCENARIO` | `scenarios/crossing-v1.json` | Scenario configuration file |
| `ARC_RUN_DIR` | `runs` | Experiment record directory |
| `ARC_TOKEN` | Unset | Optional bridge Bearer token |
| `RUST_LOG` | `arc_angel=info` | Log filter |

Keep the default localhost binding for local development. The optional token protects the bridge connection; browser observation endpoints are unauthenticated.

The default scenario is a **schematic crossing**. Before using a BeamNG scenario, measure and configure its route geometry, conflict-zone size, and controller limits. West Coast USA is the intended map, but the included coordinates are not calibrated to it.

## Bridge integration

Connect the simulator bridge to:

```text
ws://127.0.0.1:3000/ws/bridge
```

1. Send `hello` as the first WebSocket message.
2. Use the returned `session_id` in subsequent messages.
3. Send each state batch with all vehicles in the world at one simulator frame.
4. Handle the server's `recommendation_batch`, including its simulation-time expiry.

The bridge must also enforce wall-time expiry and local fallback behaviour.

Example payloads:

- [Hello message](examples/hello.json)
- [Vehicle state batch](examples/state_batch.json)

When `ARC_TOKEN` is configured, include it in the WebSocket upgrade request:

```text
Authorization: Bearer <token>
```

Do not include the token in JSON payloads.

## Dashboard and API

The dashboard polls every 500 ms and provides a read-only view of server state.

| Endpoint | Purpose |
| --- | --- |
| `/health` | Basic service health response |
| `/api/status` | Server status |
| `/api/worlds` | Available worlds |
| `/api/worlds/{id}` | Details for a world |
| `/api/scenarios/{id}` | Scenario details |

Dashboard files live in `web/` and use plain HTML, CSS, and JavaScript.

## Experiment records

Each server startup creates a run directory under `ARC_RUN_DIR`.

| File | Contents |
| --- | --- |
| `metadata.json` | Scenario, protocol version, and build version |
| `events.jsonl` | Accepted telemetry, plans, acknowledgements, removals, rejected messages, and disconnects |

Recording has known reliability and metadata gaps. See the [recording notes](AI-Wiki/Projects/IBM/wiki/recording.md) before relying on logs as complete experiment evidence.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | Rust service, protocol, world state, and coordination logic |
| `web/` | Browser dashboard |
| `scenarios/` | Scenario configuration |
| `examples/` | Bridge message examples |
| `AI-Wiki/` | Requirements, architecture, team workflow, and implementation evidence |
| `.agents/skills/uriel/` | Shared project guidance for AI assistants |

## Validation and limitations

Earlier work reported successful compilation and basic dashboard checks. These do not establish physical coordination correctness.

The following remain unvalidated or incomplete:

- BeamNG bridge integration and controller calibration.
- Physical acceptance, fault trials, and load measurements.
- Arrival-time ML training, inference integration, and evaluation.
- LinuxONE deployment and performance.

Speed recommendations are advisory. Collision prevention has not been demonstrated, and stop/hold behaviour for a zero speed cap depends on the installed BeamNG AI controller.

Behavioural testing is deferred to hackathon day unless separately authorized.

## Project documentation and collaboration

Start with the [project wiki](AI-Wiki/Projects/IBM/wiki/index.md).

- [Latest requirements](AI-Wiki/Projects/IBM/wiki/latest-prd-context.md)
- [Implementation status and evidence](AI-Wiki/Projects/IBM/wiki/implementation-status.md)
- [Team ownership and workflow](AI-Wiki/Projects/IBM/wiki/team-workflow.md)
- [Local operations and deployment context](AI-Wiki/Projects/IBM/wiki/operations.md)

Open `AI-Wiki/` as an Obsidian vault for linked navigation.

AI assistants should read `AGENTS.md` and the repo-local Uriel skill before working, then update relevant wiki pages and the chronological log after meaningful changes.
