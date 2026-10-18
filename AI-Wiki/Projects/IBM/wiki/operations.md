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

## Grid Plane connection preparation

For the requested U-S01 preparation, live process inspection found native BeamNG.tech running from `/home/vinnavan/BeamNG.tech.v0.39.4.0`. No TCP listener was present on port 64256 at inspection time, and the default `python3` environment could not locate `beamngpy`; other Python environments were not checked. Current workspace inspection confirms that the Python bridge is absent.

The proposed local control path is BeamNG.tech → BeamNGpy Python controller/recorder → existing Rust bridge WebSocket. The official [BeamNGpy Server tool documentation](https://docs.beamng.com/beamng_tech/tools/beamngpyserver/) identifies `Window > Tech > BeamNGpy Server` as the in-game server control. Enable that server before attempting to attach to the running simulator; connection and client/version compatibility remain unverified.

The user proposes Grid Plane, identical vehicle configurations with different colors, perpendicular approaches and equal starting distances. This is an initial controlled setup proposal, not a configured scenario or collected dataset. Explicit crossing paths, measured spawn poses and approach distances are still needed. Later training should vary starting distances, speeds and timing across whole runs and label actual entry/rear-clearance events. No simulator commands, spawning, driving or collection were executed during this connection investigation.

## Executed Grid Plane head-on run

The user's subsequent instruction replaced the crossing setup with an immediate two-car head-on collision and explicitly authorized this simulator run. Attached to the existing localhost:64256 server with BeamNGpy 1.36 (official compatibility table pairs it with BeamNG.tech 0.39), installed in `/tmp/uriel-beamng-venv`. The active map was `/levels/smallgrid/main.level.json`.

Reused the player's Vivace and spawned `uriel_blue` with the same copied parts/configuration, red/blue paint, opposing headings and approximately 100 m separation. Built-in AI followed opposing straight polylines at a requested 50 km/h with car avoidance disabled. This intentionally produces a crash baseline; it does not exercise Uriel coordination or ML. Both damage readings increased during the approach. Afterwards AI was disabled and brakes/parking brakes applied; the crashed cars remain in the running simulator.

Evidence: `runs/headon-d0f1ef6424/{metadata.json,telemetry.jsonl,summary.json,verification.json,controller.py}`. The recording contains 120 samples over approximately 16 wall seconds, individual sensor simulation times, state, damage and electrics. Sampling is sequential and variable-rate; no synchronized contact-event labels, dataset split or training were implemented. The preserved controller is a run artifact, not a reusable project script; see the new standalone runner below.

The client's `vehicles.get_states()` failed with an unhandled `UpdateScenario` request against this installation; per-vehicle state sensor polling worked and was used for the completed run. A successful connection and crash baseline do not close the remaining bridge/controller or acceptance gaps.

## Reusable standalone head-on collision script

The user requested a script they can run themselves. `scripts/beamng_headon_collision.py` is separate from the cooperative `scripts/beamng_headon.py` controller. It attaches only to an already-running BeamNGpy server, accepts either the existing player Vivace alone or the matched `thePlayer`/`uriel_blue` pair, and refuses other maps, extra vehicles, or mismatched car configurations. With `--run`, it positions the cars 100 m apart, sets red/blue colors and opposite straight AI lines at 50 km/h, records state/electrics/damage under `runs/headon-collision-<id>/`, stops on a damage increase above 5 or after 16 seconds, then pauses the scene and disables AI. It does not connect to Rust, apply coordinator advice, train ML, or feed the dashboard. Without `--run` it only prints settings and makes no simulator connection. The run was not executed while preparing this reusable script.

With BeamNG.tech open on `smallgrid`, BeamNGpy Server enabled on localhost:64256, and the existing BeamNG Python environment:

```sh
/tmp/uriel-beamng-venv/bin/python scripts/beamng_headon_collision.py
/tmp/uriel-beamng-venv/bin/python scripts/beamng_headon_collision.py --run
```

Adjust `--separation-m`, `--speed-kmh`, `--duration-s` or `--impact-threshold` as needed; `--help` lists bounds and defaults. An impact is inferred from the damage sensor threshold, not a synchronized contact label. After a run the sim is paused, both AI drivers are disabled and brakes are applied. A 2.5-second launch check aborts if either car has not moved 1 m.

The user's first run, `runs/headon-collision-963b23ac88/`, did not launch: all 121 samples stayed about 100 m apart with zero velocity and zero damage; both electrics readings showed gear `P` and `parkingbrake_input=1`. The first fix queued a brake release but incorrectly checked electrics while physics was paused; the sensor still showed its previous frame. The next user attempt, `runs/headon-collision-c956943971/`, stopped before writing telemetry with `Parking brake did not release`, confirming this stale-readback check blocked the run. Source inspection also found the runner never resumed physics after queuing AI paths. Removed the paused sensor assertion and added an explicit `bng.control.resume()` before live sampling. The 2.5-second/1 m position watchdog is the launch check. Syntax/help/dry-run and unit checks can verify source behavior only; a successful simulator rerun remains pending. The collision baseline is not an avoidance/safety result.

The next user run, `runs/headon-collision-a64c3b9895/`, advanced both simulation clocks by about 2.53 seconds with parking brakes released, throttle rising above 0.51 and engines near 6530 RPM, but both gears stayed in `P`. Installed BeamNG.tech 0.39.4 source confirms `techCore.handleControl` passes `gear` through `drivetrain.shiftToGear` to the controller selector: the DCT `hShifterModeLookup` maps 1 to Park and 2 to Drive. The collision runner now queries the actual gearbox type and selects 2 for DCT, 1 for manual, rejecting unknown types. Both setup and launch use that selection; launch failures record gearbox/brake/throttle/RPM diagnostics. Three regression checks cover selector semantics; all 24 Python tests and the default dry run pass. No additional simulator run was performed, so successful execution of this correction remains pending.

The collision runner now publishes real measured state through `POST /api/collision/telemetry` to `http://127.0.0.1:3001` by default. Use `--dashboard-url` for another HTTP origin or `--no-dashboard` to disable display delivery. The dashboard must be running; delivery errors stop the run through the pause cleanup path. Refresh the page and disable Preview demo. The observation world uses a fixed grid and is labelled intentional collision / observation only. This endpoint returns no control plan, and retains the last positions after completion. A synthetic Python-to-Rust/API check on an isolated test server verified advancing frames and final retained positions; it did not connect to BeamNG.

User run `runs/headon-collision-a5953f0c73/` completed with `impact_detected`, 56 samples, 7.47 seconds elapsed, positive damage increases on both cars and a paused scene. The API contained both measured car positions, but the renderer incorrectly required nonempty road routes and returned before drawing them. Fixed the route-free renderer and added a failing-before/passing-after JavaScript DOM regression for two dots, changing marker positions and retained completed state. The user requested only red/blue dots moving on the grid; head-on icons, visible names and route/plan overlays were removed. The local dashboard was rebuilt and its final recorded positions restored as disconnected after restart; no additional collision was run. Refresh the page to load `collision-dots-v3`.

## Current user-run dodge command

The user requested replacing intentional crashes with dodging in the same script. `scripts/beamng_headon_collision.py --run` now uses the existing Python paired-path planner on an empty Grid Plane, fixed 110 m starts, default 30 km/h (10–36 supported), matched Vivaces and correct DCT/manual forward selectors. It translates the planner’s paths to the current scene centre, applies front-point alignment, and pauses on launch failure, damage, state/predicted-overlap guards or >1.2 m path deviation. `passed_and_returned` requires both measured cars to be past each other and near their original lateral line; time expiry is incomplete. Runs now use `runs/headon-dodge-<id>/`. The default remains a no-connection dry run. The local dashboard continues to show only two measured dots via display-only publishing, now labelled dodge; Rust does not choose this runner’s paths. No obstacles or ML were added. The historical collision command descriptions and evidence above describe the earlier implementation, not the current default. Conversion checks passed; no new BeamNG trial was launched.

## Earlier standalone two-car avoidance on plain Grid Plane

The user subsequently requested cooperative dodging, then explicitly limited the live scene to **two cars, no obstacles for now**. Added `scripts/headon_planner.py`, `scripts/beamng_headon.py` and focused tests. The runner attaches to the existing localhost server and requires exactly `thePlayer` and `uriel_blue`, matching Vivace physical parts/tuning, and `smallgrid`. It repairs/repositions those cars 110 m apart, applies red/blue paint, selects paired paths, unpauses simulation time, drives at a requested 30 km/h and records under `runs/avoidance-<id>/`. The default without `--run` prints a plan and does not connect. With the prepared environment:

```sh
/tmp/uriel-beamng-venv/bin/python scripts/beamng_headon.py --run --standalone
```

This environment is temporary, not a project-wide installed dependency. It contains BeamNGpy 1.36. The standalone mode neither launches nor closes BeamNG, integrates with the Rust server, trains a model nor creates obstacles. It leaves the completed scene paused; unpause in-game to continue manual use. The later integration below changes the default `--run` mode to Rust; `--standalone` explicitly retains this baseline.

Executed evidence: `runs/avoidance-3d366e13bd/` contains before/metadata, 125 sequential telemetry samples, summary, the exact controller/planner source snapshot and a separate post-run pause check. Both cars completed their own-left shifts and returned without reported new damage; closest-approach speeds were approximately 29.85 and 29.92 km/h. Minimum sampled enclosing-circle clearance was 1.557 m; maximum path deviations were about 0.56 m. The later post-run check verified physics paused. The original run's summary recorded nonzero residual speeds after braking, so it is not proof of emergency-stop control. Current controller cleanup now explicitly pauses the completed scene.

Investigation/fixes before the pass:

- Parts trees differed in selection provenance metadata although selected parts and tuning matched. Comparison now ignores paint/UI selection metadata while retaining actual parts and tuning comparisons; regression covered.
- `ai.driveUsingPath` in this BeamNG installation interprets line nodes at the **front point** and places the car at that initial node. Sending reference-origin nodes caused an approximately 1.84 m initial shift and a guard abort. The runner translates the AI line by the measured front/reference offset; regression covered. The bounded deviation guard then passed in the executed run.
- Physics-running and bullettime pause are independent. Readback showed physics enabled but bullettime paused/factor zero; the runner explicitly clears bullettime pause and restores factor one for the authorized run.

Verification: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` passed 14 tests. `cargo test --offline` completed successfully with zero Rust tests. Earlier aborted evidence directories `avoidance-71d4c24aed` and `avoidance-cab0363959` are retained and are not successful trials. No obstacle acceptance or broad safety/training result is claimed.

Final repeat with immediate pause cleanup: **`runs/avoidance-35d4b5dbb9/` is the latest completed evidence**. It contains 128 samples over approximately 13 wall seconds, zero new reported damage, closest-approach speeds 30.01/30.06 km/h and minimum sampled enclosing-circle clearance 1.519 m. The controller now pauses physics immediately on a guard abort and on normal completion, before final snapshots, and pauses again in cleanup. A live independent readback verified physics disabled and both final positions unchanged across two observations, near Y=-33.28/+33.57 m. Source snapshots were copied only after checking their hashes against the run metadata. `verification.json` records the checks. The earlier run's brake-input issue motivated this repeat; physical emergency braking remains unverified and pause is a simulator-specific guard.

## Current Rust-integrated head-on operation

The user explicitly authorized extending the contract and connecting the controller, while obstacles remain deferred. Start the local Rust server once with `cargo run` (an agent-started instance is currently on localhost:3000). With BeamNG's server on localhost:64256 and the two existing matched Vivaces, run:

```sh
/tmp/uriel-beamng-venv/bin/python scripts/beamng_headon.py --run
```

For a reproducible client environment, see the root README and `scripts/requirements-beamng.txt` (BeamNGpy 1.36, websockets 17.2). `--server-url` selects a maneuver-v2 endpoint. There is no automatic fallback to local planning if Rust is unavailable. `--standalone` selects the earlier baseline. Without `--run`, the command only prints a local dry plan.

The bridge validates starts and parts, obtains Rust's origin-based paths while paused, applies them once with front alignment, acknowledges both acceptances, obtains a fresh `execute` lease and unpauses. It streams measured state roughly every 100 ms; Rust renews the same maneuver, monitors actual motion and reports `complete`. On completion or validation/connection failure, cleanup requests an immediate simulator pause. Network receives cannot silently replace an expired prior lease: the client reserves 100 ms of the previous lease for requesting a pause. Blocking simulator calls/process death remain limitations, and this is not proof of physical emergency braking.

Current final evidence: **`runs/avoidance-e8d6280410/`**, with 127 simulator samples, 129 correlated Rust state/plan exchanges, two accepted paths, a stable maneuver ID and server `complete`. Both cars passed and returned with zero new reported damage; closest-approach speeds were 30.10/30.06 km/h and minimum sampled enclosing-circle clearance 1.522 m. Source snapshots/hashes, `bridge-wire.jsonl`, filtered `server-events.jsonl`, API snapshots and independent pause/stable-position verification are preserved there. The full server record directory is `runs/63ecd444-4f4b-4139-9638-57b1485736ef/`. The local Rust instance remains running; BeamNG remains paused after the run.

Checks passed: 9 Rust unit tests, 21 Python unit tests, offline build, Rust formatting, Python syntax and diff whitespace. `tests/check_headon_wire.py` against the local server (no simulator calls) records `runs/protocol-check-fed323c18e/`: v2 prepare/accept/execute, frozen-telemetry pause, active ownership, new reset epoch, legacy crossing-v1 handshake/plan and dashboard world counts. Independent review identified and then confirmed fixes for old-lease renewal and frozen sensor timestamps. The earlier integrated run `avoidance-2af29f8528` predates those fixes and is historical evidence, not the final implementation snapshot.

Only the basic open-map, two-car algorithm/integration slice is demonstrated. No obstacle spawning/testing, ML worker, model training, varied-scenario acceptance, load campaign, LinuxONE deployment, commit or push occurred.
## README documentation handoff

The README overview and local setup now use Uriel naming while identifying the existing Arc Angel prototype and retaining its configuration names. Current defaults, routes, and dashboard demo behaviour were inspected in source. The remaining README sections, starting at `Bridge protocol`, are reserved for a teammate to replace with the second-half Markdown supplied in chat. This is documentation work; no server, simulator, deployment, or behavioural checks were run.

## Sources

## LinuxONE setup — source staged, native build pending

The user explicitly authorized remote setup over SSH. Live inspection confirmed Ubuntu 24.04.5 on s390x, approximately 8 GB RAM and 34 GB available disk. User-local Rust/Cargo are installed under `~/.cargo/bin` but were absent from the noninteractive PATH; no replacement toolchain was installed. Existing `~/uriel-server-tools` and its Python environment were preserved.

Copied a working-source snapshot, including uncommitted head-on changes, into `/home/linux1/uriel`. Excluded private keys, Git internals, local virtual environments, build artifacts and runtime recordings. All 69 transferred source hashes matched `deployment-manifest.json`; 21 Python unit tests passed on LinuxONE. This is source staging, not a Git push or proof of a working Rust deployment.

Installed `~/.config/systemd/user/uriel.service` from `deploy/uriel.service`, binding the service to remote localhost:3000 and recording under `~/.local/state/uriel/runs`. Enabled user lingering for persistence after logout. The unit is deliberately not enabled/started until the native build completes. `systemd-analyze --user verify` reported the expected missing release executable; service runtime validation is pending.

Respecting the user's long-build preference, no native Cargo download/build was launched. Run on LinuxONE:

```sh
bash ~/uriel/deploy/linuxone-build-start.sh
```

It runs locked Rust tests, builds natively with two jobs, enables/starts the user service and checks `/health`. Build log: `~/.local/state/uriel/build.log`. Service logs: `journalctl --user -u uriel.service`. The helper is syntax checked; Rust compilation and health remain pending.

A laptop SSH tunnel forwards localhost:3300 to LinuxONE localhost:3000. The remote service is now running; use `http://127.0.0.1:3300` for its dashboard and `--server-url ws://127.0.0.1:3300/ws/headon` for the local BeamNG bridge. The original local Rust server on port 3000 was preserved. No firewall or public HTTP port was opened and no ML worker was deployed. Private key material was not copied or stored in the project. The later live-controller attempt is recorded below.

## [2026-10-17] Head-on dashboard update and remote latency check

The dashboard now overlays both head-on recommendation paths, current car positions, phase and acceptance state. Its Preview demo animates synthetic coordinates and remains explicitly labelled; it is not telemetry. The three updated frontend files were copied to LinuxONE, rebuilt into the Rust binary, and the user service restarted. `/health` returned `ok`, and checks of the served HTML and JavaScript found the new interface.

The user asked to see the view during a remote-coordinated pass. A BeamNG runner attempt connected to `ws://127.0.0.1:3300/ws/headon`, but its 350 ms hello receive timeout expired before the server acknowledgement. The server recorded hello/disconnect, with no telemetry plan; the simulator was left paused and no cars started moving on the proposed paths. The SSH connection's observed TCP RTT was about 325 ms. The controller's plan window is 500 ms with 100 ms reserved for pause, so do not claim a remote integrated pass or relax that timing guard based on the animated preview. Use the explicit preview button to inspect the 2D UI; resolve low-latency placement/control design before another remote physical run.

## [2026-10-17] simulator and dashboard | Local-coordinator head-on pass

For the user's follow-up request to see a trial, launched a separate optimized local Rust service on `127.0.0.1:3001`; the local port-3000 server and LinuxONE service were left running. The existing two matched Vivaces completed the server-planned pass and return on empty `smallgrid`. Evidence is `runs/avoidance-71873434af/`: 127 samples, 129 plan exchanges, two accepted paths, one maneuver ID, `complete`, zero damage increase, 1.551 m minimum sampled enclosing-circle clearance and paused final physics. Final state remains in the local read-only dashboard at `http://127.0.0.1:3001` after disconnect. No obstacle, ML, or remote LinuxONE control was involved.

The user then reported that the map was not following live motion. Root cause: the frontend retained the previous world selection while that disconnected world remained listed. Updated selection to prefer the newest connected head-on world if the current head-on selection is stale, added an app.js cache-version query, rebuilt and restarted only the isolated local dashboard server, then repeated the requested pass. `runs/avoidance-82ebb49eb5/` completed with 127 samples, 129 plans, both paths accepted, zero damage increase, 1.523 m minimum sampled enclosing-circle clearance and paused final physics. During this run `/api/worlds` showed the selected head-on world connected and advancing from frame 77 to 87 within one second, with both positions changing. The browser was not available for screenshot QA.

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
