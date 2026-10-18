---
title: "Running and deployment"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Running and deployment

## Current IBM server and laptop BeamNG status

The hybrid Rust service and portable ML worker were deployed and exercised on IBM LinuxONE. Ten HTTP conflict-evaluation calls returned accepted results, `/health` returned `ok`, and both services were active. The user reports that a teammate also ran the IBM-hosted server version successfully. Our laptop-controlled BeamNG trials used local coordination because SSH-tunnel latency exceeded controller deadlines. Earlier failed tunneled BeamNG attempts document that network limitation; they do not mean IBM was untested. They also do not claim that the laptop completed a live BeamNG vehicle trial through the tunnel.

## Saved user-placed West Coast crossing

[Two-car placement snapshot](../../../../scenarios/west-coast-user-crossing-two-car.json) stores the live `clone12` and `clone13` Vivaces on `west_coast_usa`, including measured origin positions, forward/up vectors, orientation quaternions and full vehicle configurations/paints. The user identifies these curved approaches as meeting at a 90-degree intersection; current headings alone do not establish the junction angle. The distant `thePlayer` and walking avatar `clone11` are excluded. Traffic-disabled state is user-reported. Capture was read-only, JSON readback confirmed both cars/configurations, and no reset, route calibration or driving trial was performed. This is a placement snapshot, not a Rust `Scenario` configuration.

### User-requested recovery after deleting a car

On 2026-10-17, live inventory contained only `clone12`. At the user's request, recreated `clone13` from the full saved configuration and restored both cars to their saved positions. Applied the collector's documented 180-degree quaternion correction; readback position error rounded to 0.0000 m and forward-vector dot product to 1.00000 for both cars. AI was disabled, service/parking brakes applied and physics left paused. No driving trial was run. The user now wants to select destination points manually; recorded trajectories are an option, not the current required approach. BeamNG's documented Drive Path Editor NavGraph mode supports road-node selection and per-vehicle path links, but availability in this installed build was not inspected.

### Three user-requested editor-route trials

On 2026-10-18, after the user restarted the blocked BeamNG API, saved the live native editor session plus all three scene vehicle configurations/poses to `scenarios/extended-90-degree-data-collection/extended-90-degree-data-collection.json`. This completes the previously blocked named save; the snapshot includes `clone11` but only `clone12` and `clone13` were controlled. Both existing NavGraph routes, lane following, car avoidance and aggression 0.3 were preserved. Speed limits were independently randomized over 20–40 km/h for three user-authorized trials: (27.2,33.9), (28.7,34.0), (32.9,32.3), in clone12/clone13 order. Evidence: `runs/extended-90-three-f94a7eda46/` (scene, schedule, runner source, JSONL telemetry, summaries and final readback).

Each trial ran approximately 50 simulation seconds. `clone13` reached within 10 m of its destination in all three; `clone12` did not. All damage-sensor increases were zero. Trial 1 measured clone12 peak speed approximately 6.7 km/h and only local motion near its start; root cause was not established and paths were not altered. These are incomplete crossing runs, not successful two-car crossing acceptance or training-eligible labels. The cars were reset after the third trial, AI disabled, brakes held and physics paused. Deterministic physics was configured to 60 with speed factor 1; wall-time loops did not establish exact realtime pacing or fixed sample frequency.

### Randomized collection implementation

On 2026-10-18, the offline arrival collector was updated to read the linked paths from the named saved editor session, draw independent bounded speed/delay settings per subject and use the linked graph nodes for BeamNG AI. Pose restoration now uses a live heading check before changing the saved quaternion. A GE Lua vehicle inventory query replaces the slow configuration query. Syntax compilation and CLI help succeeded; no simulation was run as part of this code change. The collector still has no traffic spawn or background-vehicle telemetry, and arrival labels remain provisional. Usage is documented in [[recording]].

### Live editor route assignment check

A subsequent user-requested read-only check found two enabled NavGraph routes, correctly linked to `clone12` and `clone13`, with lane following, car avoidance and aggression 0.3. Route 1 selects `DR360_2` → `junction1_wp19`; a read-only road-graph query connects them through `junction1_wp12` over approximately 140.6 m. Route 2 selects `tunnel_city_A_57` → `DR323_2`, also through `junction1_wp12`, approximately 203.8 m. Both starts are close to their respective live car positions. Route 1 has a 6.02 m/s limit (21.7 km/h). Route 2 stores 31.3 m/s but its route speed mode is `off`, so the editor playback implementation omits that speed from the AI command; no explicit speed profile is enabled either. Physics was running at readback. No settings were changed or playback started. Evidence: `runs/editor-route-inspection/latest.json` and `graph-check.json`; this verifies assignments/connectivity, not actual driven paths or physical acceptance.

### Updated user-edited editor route snapshot

On 2026-10-18, captured the live Drive Path Editor state after the user changed the graph routes and updated `scenarios/extended-90-degree-data-collection/extended-90-degree-data-collection.json`. The saved enabled route for `clone12` is `junction1_wp3` → `junction1_wp19`; `clone13` is `tunnel_city_A_58` → `Bridge13_A` → `DR323_2`. The snapshot includes all three scene vehicles and their configurations/poses. A direct game-side file load was unavailable, so the editor state was returned over BeamNGpy and written locally after checking the map, cars and route links. This is the current named snapshot; prior route nodes in the previous snapshot are superseded.

### Read-only live route check

On 2026-10-17, BeamNGpy connected to the already-running local GE Lua server on port 25252. The level was still `west_coast_usa`; `clone12` and `clone13` matched their saved positions, while `thePlayer` and `clone11` remained separate. The live road graph gives `clone12` a heading-aligned route beginning near `junction1_wp3` and `clone13` a route beginning at `tunnel_city_A_57`; both graph paths reach `junction1_wp12` near `(-363.98, 612.70, 74.90)`. Their route lengths from those graph nodes are approximately 168 m and 147 m. The last graph segments into that node (`junction1_wp33` to `junction1_wp12`, and `tunnel_city_A_63` to `junction1_wp12`) form an approximately 54-degree acute road-axis angle. This is a candidate only: the map graph does not prove it is the user's intended visible junction or its measured pavement boundaries. Do not feed this candidate into the existing Small Grid square-zone trainer.

### West Coast pilot collection and straight-through route investigation

The user authorized live trials. `scripts/collect_west_coast_arrival_trials.py` attached to the running West Coast scene, used only the two saved Vivaces, disabled traffic was user-reported, and kept other scene vehicles uncontrolled. A road-AI pilot at deterministic speed factor 4 completed 30.8 simulation seconds in 14.7 wall seconds, recorded 155 samples per car at approximately 5 Hz, both provisional zone-entry/clearance events, and zero damage increase. Evidence: `runs/west-coast-arrival-a0d9d53e60/`. Factor 4 advances four times as much simulation per rendered frame; the collector steps once per sample to retain the 5 Hz target.

The user clarified that both cars should continue straight through. Inspection of the clean pilot's headings showed `clone12` turned substantially across the candidate zone even though its road-AI route reached the node. A coordinate-line experiment attempted to force a straight path, but `clone12` immediately took 4,059.64 damage units and rose to z≈91 m; collection stopped at 4 simulated seconds. Both cars were then teleported to their saved positions and verified at zero damage, with physics paused. Evidence: `runs/west-coast-arrival-28480d61e2/`. The coordinate-line controller was removed from the reusable collector. More trials are paused until a road-following straight exit through the user's intended junction is identified; the junction remains a provisional 54-degree graph candidate and labels remain training-ineligible.

## Earlier deployment planning (superseded by verified deployment below)

S5 reports user-confirmed **Ubuntu 24.04 / IBM LinuxONE / s390x**; Fedora 44 KDE/x86_64 remains development context. The SSH-key failure described in this earlier ML integration attempt was later resolved; the subsequent deployment and remote worker checks below succeeded. This older failure should not be read as current IBM server status.

The project subsequently built the Rust service natively and deployed a portable Python model worker on the same LinuxONE instance. The SSH-tunnel latency issue applies to laptop BeamNG control; it does not invalidate the server-side deployment or inference checks documented below.

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

At the time this earlier status note was written, it reported only the basic open-map, two-car algorithm/integration slice. Its statement that there had been no ML worker or LinuxONE deployment is superseded by the later model integration and successful IBM deployment recorded below. Obstacle, varied-scenario and load acceptance remain open.
## Historical README documentation handoff

At that point the README overview and local setup used Uriel naming while the remaining sections were reserved for teammate-supplied content. This handoff note is historical; the README has since been updated with the Rust, GPU-trained ML, BeamNG and IBM LinuxONE server-run information.

## Sources

## [Historical setup stage] LinuxONE source staging — later completed

The user explicitly authorized remote setup over SSH. Live inspection confirmed Ubuntu 24.04.5 on s390x, approximately 8 GB RAM and 34 GB available disk. User-local Rust/Cargo are installed under `~/.cargo/bin` but were absent from the noninteractive PATH; no replacement toolchain was installed. Existing `~/uriel-server-tools` and its Python environment were preserved.

At this staging point, a working-source snapshot, including uncommitted head-on changes, was copied into `/home/linux1/uriel`. Excluded private keys, Git internals, local virtual environments, build artifacts and runtime recordings. All 69 transferred source hashes matched `deployment-manifest.json`; 21 Python unit tests passed on LinuxONE. This is a historical milestone; later native deployment and inference checks are summarized at the top of this page.

Installed `~/.config/systemd/user/uriel.service` from `deploy/uriel.service`, binding the service to remote localhost:3000 and recording under `~/.local/state/uriel/runs`. Enabled user lingering for persistence after logout. The unit is deliberately not enabled/started until the native build completes. `systemd-analyze --user verify` reported the expected missing release executable; service runtime validation is pending.

Respecting the user's long-build preference, no native Cargo download/build was launched. Run on LinuxONE:

```sh
bash ~/uriel/deploy/linuxone-build-start.sh
```

It runs locked Rust tests, builds natively with two jobs, enables/starts the user service and checks `/health`. Build log: `~/.local/state/uriel/build.log`. Service logs: `journalctl --user -u uriel.service`. The helper is syntax checked; Rust compilation and health remain pending.

A laptop SSH tunnel forwards localhost:3300 to LinuxONE localhost:3000. The remote Rust service was subsequently run; the laptop-to-server tunnel proved too slow for the BeamNG controller deadlines. At this staging milestone the ML worker had not yet been deployed, which was superseded by the later hybrid deployment recorded below. No firewall or public HTTP port was opened and private key material was not copied or stored in the project.

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

## [2026-10-17] Rust/ML integration attempt

Added optional crossing-v1 observe-only predictions. Rust derives the training feature vector, calls a same-host Python worker over loopback JSON lines, enforces a 40 ms timeout and includes validated predictions in `recommendation_batch.ml_predictions`. The worker is defined by `scripts/ml_worker.py`; its user service is `deploy/uriel-ml-worker.service`. Install the complete model run directory as `~/.local/share/uriel/ml/current`, then install the ML Python requirements before starting that unit. The existing Rust service reads `ARC_ML_ADDR=127.0.0.1:3100`. Missing/slow predictions do not affect the Rust plan.

At that time, no model artifacts were available in this checkout. The local pilot accepted only two trials in one scenario group and returned `insufficient_data`; that result applied to this dataset and training invocation. The SSH attempt using the then-available key failed before any remote change. The user later located the authorized key, and subsequent deployment and server inference succeeded as recorded below. The laptop BeamNG controller still used local coordination because of tunnel latency; the head-on maneuver-v2 controller remains separate from the ML path.

- [[protocol]], [[ml-arrival-prediction]], [[implementation-status]].

## [2026-10-17] verification | LinuxONE key and current ML readiness

At that check, the Rust service was active, but the joblib-format pilot models were absent and the then-configured worker was inactive. The later combined XGBoost models were exported to a portable format and deployed through a different worker setup; see the successful LinuxONE hybrid deployment below. The local pilot's one-group limitation remains specific to that training run.


A one-trial run on the refreshed graph routes (`runs/west-coast-arrival-00e9ea6f19/`) stopped on the 5 s no-motion watchdog after 12 simulated seconds; clone13 had not moved 0.5 m. No junction entries or damage increase were recorded. A subsequent requested relaunch could not connect because the BeamNG API was offline on port 25252; no vehicle commands were sent in that attempt.


### Restored named scene in BeamNG

On 2026-10-18, after the user asked to load the saved scene, loaded `west_coast_usa` and restored all three saved vehicles from `scenarios/extended-90-degree-data-collection/extended-90-degree-data-collection.json`. Rebuilt both enabled linked Drive Path Editor routes from the saved graph nodes and verified the live vehicle inventory and route links. Removed the temporary `thePlayer` car created by loading the map from the menu, and switched the camera to `clone12`. No trial was started during restoration.


### Corrected tipped clone13 restoration

The saved clone13 orientation was already tipped (forward Z 0.923). Live road-graph inspection found Bridge13_A at Z 96.328 m versus tunnel_city_A_58 at Z 74.799 m; native editor relinking aims the car along that steep segment. Repaired clone13 with an upright horizontal road heading, advanced 60 paused physics steps and verified up Z 1.0, forward Z 0.0 and damage 0.0. Saved its corrected pose and a restoration warning in the named snapshot. Retained the user-selected route nodes; Bridge13_A remains an elevated waypoint requiring review before driving. Left physics paused. Future restoration must apply saved poses after native editor relinking.


### Interrupted three-trial telemetry batch

Requested three randomized telemetry trials on the saved routes (seed 45, physics factor 4). The first attempt `runs/west-coast-arrival-0e2395a651/` had a frozen state clock and was interrupted; a brief resume/pause check restored advancing physics time. The restarted batch `runs/west-coast-arrival-60a81eea32/` recorded 189 samples per vehicle over 37.6 simulated seconds (22.31 wall seconds), then stopped on clone12 damage increase 3445.848. Clone13 damage increase was zero; neither car entered the provisional junction zone. Trials 2 and 3 were cancelled by the damage guard. Left the damaged scene paused for inspection; labels remain training-ineligible.


### Latest route refresh and mixed-model pilot

The model pilot helper scripts/collect_west_coast_vehicle_pilot.py reuses the recorder with explicit Vivace/ETK 800/Covet configurations and records model/configuration identity. The first requested three-run pilot (runs/west-coast-model-pilot-1db31df233/) stopped after one Vivace/ETK run at 33.0 simulated seconds on clone12 damage increase 3428.493; clone13 entered/cleared the provisional zone with zero damage increase. No second or third vehicle combination was executed. The helper preserves the exact user editor save separately from its audited ground-route overrides. Python syntax checks passed before the live pilot. The recorder now supports automaticGearbox Drive selection, model/configuration fields in group metadata, vehicle_model in CSV, and aborts after five frozen-clock samples. Its original command-line main still requires Vivaces; mixed-model operation uses the helper.

Refreshed the named scene snapshot from the latest live editor state: clone12 now uses junction1_wp3 to junction1_wp19; clone13 still uses tunnel_city_A_58, Bridge13_A, DR323_2, tunnel_city_A_59, Bridge13_B. Preserved the exact selected route order and actual Vivace/ETK 800 configurations. Upright starts now use the first connected road segment rather than aiming directly at elevated selected waypoints. The requested single run is runs/west-coast-live-route-7978196760/: 165 samples per car, 32.8 simulated seconds, 32.53 wall seconds, clone12 damage increase 2711.938, clone13 zero damage increase and no provisional junction entries. The damage guard stopped the run; cleanup reported no errors and left physics paused. Telemetry effective sampling was 5 Hz at speed factor 2; nominal launch schedule times differ from measured simulation time, so they are not calibrated event labels.

All listed West Coast labels remain provisional and training-ineligible.


### Verified correction: exact editor paths

Diagnosed the route-following failure against installed BeamNG source and a live graph comparison in `runs/route-diagnosis-f9b79fe438/path-comparison.json`: the editor expands nodes with direction penalties disabled, while waypoint AI with lane following enabled chooses legal-direction detours. The blue start-to-end path was five nodes in the editor but nineteen in the lane-aware planner. The selected node order also doubled back and included bridge detours. Updated the recorder to expand the editor road graph once and pass native `ai.driveUsingPath{path=...}` with lane replanning off and car avoidance on. It reads back and checks the actual AI path, uses measured simulation time for launch scheduling, and accepts the model stored in the scene instead of requiring Vivaces. Corrected both live editor routes to one ordered ground-level crossing, populated their visible geometry, and saved both the project snapshot and BeamNG `/gameplay/data.json`. Earlier route definitions are preserved with the run evidence. This chosen closed crossing traverses the blue road contrary to its legal one-way metadata; ordinary traffic-aware routing remains separate work.

Live verification `runs/west-coast-exact-path-b9530c2a1b/` recorded 131 samples per car over 26.0 simulation seconds / 17.0 wall seconds. Both AI path readbacks exactly matched their expanded graph paths. Clone12 entered/cleared the provisional zone at 12.8/14.8 s and clone13 at 23.6/26.0 s, with zero new damage for both. Maximum sampled 3D reference-point distance from each graph polyline was 0.422/1.475 m. Final independent readback confirmed both cars upright at their reset starts and zero damage; physics is paused. Eight focused Python checks passed, including a regression that forbids waypoint replanning in the exact-path command. This is a single successful two-car baseline, with provisional zone/body proxies and no training eligibility or general traffic acceptance.


### LiDAR trial and saved reboot state

Implemented scripts/collect_west_coast_lidar_trial.py: a seeded truck/commercial-vehicle draw on clone12 and passenger-car draw on clone13, 16-channel 360-degree roof LiDARs (70 m range), raw XYZ/RGB compressed NPZ frames, and an index linking polling times to vehicle telemetry. Acquisition timestamps are unavailable; repeated/empty readings are counted rather than presented as independent synchronized scans. Sensor mount heights are calibrated against reported world positions to clear each roof. Nine focused checks passed, including point-cloud round-trip and repeated-reading accounting. The first mount attempt runs/west-coast-lidar-55fb08fcf3/ stopped before launch; the corrected live run runs/west-coast-lidar-24a6633931/ used a delivery truck at target 21.575 km/h and a Covet at target 23.013 km/h (+10% over its random base). Both exact paths were verified, both cars cleared the provisional zone, and damage increase was zero. Recorded 134 telemetry samples per vehicle and 67 distinct nonempty LiDAR scans per vehicle: 1,734,442 truck points and 2,077,838 Covet points, approximately 38.3 MiB total evidence. All 134 NPZ scans were read back with finite XYZ and matching RGB counts. Sensors were removed after recording; their mount/configuration definitions are saved and will be recreated on the next collection run. Physics is paused and the vehicles were reset; cleanup reported no errors.

The user subsequently requested a 35% increase from the latest black-route trial speed, followed by saving for a PC restart. Set the black editor route limit to 31.067 km/h (previous 23.013), wrote and read back BeamNG /gameplay/data.json, and refreshed scenarios/extended-90-degree-data-collection/extended-90-degree-data-collection.json with the current delivery-truck/Covet configurations, poses, graph links, LiDAR definitions and persistent collection settings. The cumulative random-base multiplier is 1.485; the next default seed is 9304. The LiDAR runner now reads and preserves those saved settings, instead of reverting to its earlier 1.1 multiplier. Syntax compilation succeeded. Save backup/readback/manifest are in runs/scene-save-d450b277b6/. No additional trial or collection was started after this speed change. The 31.067 km/h setting has not yet been physically verified; the user intends to resume after reboot.


### Post-reboot collection and telemetry-only switch

Restored West Coast USA, both saved subject poses and enabled native graph links, then collected at user-requested deterministic factor 2. The user subsequently disabled LiDAR. Added `--no-lidar` and `--speed-factor` to the truck/car trial runner, and completed ten further telemetry-only runs plus the initial telemetry-only switch run. All eleven reported both provisional junction clearances and zero damage. `runs/west-coast-telemetry-first-batch-manifest.json` accounts for at least three clean telemetry-bearing trials in each of eight truck/car pairs (some preceding runs also contain LiDAR). Recorded counts include four pickup/ETK and four van/Covet runs. The final scene was reset to saved starts; collection cleanup paused physics. The black-route saved limit remains 31.067 km/h and randomized collection uses multiplier 1.485 over its base draw. These recordings remain provisional for model evaluation; no calibrated training eligibility is inferred from crossing completion.


## Local XGBoost and Rust hybrid integration

On 2026-10-18, branch `vinn` fast-forwarded to `origin/main` commit `f36d049`, then its prior staged/unstaged/untracked work was restored. Four wiki conflicts were resolved by preserving both upstream and local content. The recovery stash `codex-preserve-vinn-before-main-ml-integration` is retained; no commit or push was performed.

`scripts/ml_worker.py` now loads the trained combined XGBoost UBJ models, validates schema/evaluation/version/model hashes, selects two-thread CPU inference and warms both predictors. Rust still has the 40 ms worker bound and five-second failure cooldown. `ARC_ML_MODE=hybrid` opts into learned timing in both `/ws/bridge` reservations and `/api/conflicts/evaluate`; default crossing behavior remains observe-only. Valid model estimates can widen the physical/input occupancy window (earlier entry, later clearance), with an experimental two-second allowance. Invalid or reversed timing and unavailable inference fall back to physics/input timing. Occupancy, braking feasibility and measured rear-clearance logic are retained. The new HTTP response includes additive `ml_predictions` and `ml_mode` fields. HTTP observations lack history, height and nearest-vehicle measurements; those model features remain missing. Rust nearest-relative-speed now uses radial velocity, matching the recorder feature convention.

A saved West Coast route export is `scenarios/extended-90-degree-data-collection/rust-crossing.json`. `scripts/run_arrival_hybrid.py` starts a worker and Rust process on unoccupied local ports, and stops its children on Ctrl+C. Commands, artifact contract and limitations are in `scripts/ARRIVAL_HYBRID.md`. It starts services, not simulator driving.

Validation at this stage: 38 Rust tests and four Python worker tests passed. An isolated socket integration loaded the actual combined models and obtained ten model-bearing Rust crossing responses (maximum local round trip 2.20 ms); it also exercised the HTTP conflict evaluator and worker-unavailable fallback. No live BeamNG hybrid trial or remote deployment had yet been executed at that point; the subsequent LinuxONE deployment and local hybrid BeamNG trial are recorded below. The two-second allowance is not a calibrated prediction interval, West Coast labels remain provisional, and missing-feature behavior/geometry reference alignment require physical validation before acceptance.


## LinuxONE hybrid deployment and network blocker

On 2026-10-18, explicitly authorized SSH deployment to `linux1@148.100.77.240` succeeded using the existing Documents key; private key content was not transferred. The host is s390x with Python 3.12.3 and no XGBoost package. `scripts/export_portable_eta.py` exports regression trees and validates `scripts/portable_eta.py` inference against native XGBoost, including float32 comparisons/accumulation and missing branches. Both targets matched exactly on 500 mixed finite/missing test inputs. Portable model SHA256 and the same prediction fixtures are checked at worker load on LinuxONE. Inference needs NumPy and the existing Python dependencies, without XGBoost or a GPU on the target.

Source and portable models were staged in `~/uriel-releases/hybrid-cf2bc118ec/`, built natively with the existing Rust cache, and activated through the `uriel.service` hybrid drop-in plus `uriel-ml-worker.service`. The server loads the saved West Coast Rust route export and `ARC_ML_MODE=hybrid`; both listeners stay on remote loopback. Old service configuration and the running old executable were saved under the release's `rollback/`; `rollback/rollback.sh` restores the old executable/configuration and stops the new worker. No firewall or public port was opened.

Remote verification made ten actual HTTP conflict-evaluation calls through Rust to model `combined-gpu-cf2bc118ec`, all with accepted monitor results; maximum remote-local elapsed time was 4.97 ms. `/health` returned `ok`, and both systemd user services were active. Evidence was copied to `runs/ml-arrival/combined-gpu-cf2bc118ec/integration/linuxone-verification.json`. Four Python worker checks also passed after adding the portable loader. Deployment is verified, not a BeamNG physical pass.

A laptop SSH tunnel now exposes the remote dashboard at `http://127.0.0.1:3300`. Three measured HTTP health round trips took 1952.2, 2298.4 and 2806.1 ms. This exceeds the bridge's 350 ms request and 500 ms plan lease limits; a remote live-control run is blocked by current latency. Do not relax those guards merely to start cars. Resolve connectivity/control placement before a guarded two-car hybrid trial. Route geometry, braking, provisional labels and model uncertainty still require physical validation; deployment does not establish collision avoidance.


## Local matched-car perpendicular hybrid pass

On 2026-10-18, persistent remote WebSocket ping timings through the existing LinuxONE SSH tunnel were 316.9, 381.9, 298.9, 321.9 and 339.0 ms. This is much faster than new HTTP connection setup, but still crosses the bridge's 350 ms request limit; the user explicitly authorized running locally instead. The remote services were preserved.

`scripts/run_grid_hybrid_crossing.py` loads a fresh Small Grid scene with two matching Vivace 160 DCT configurations, red/blue paint, equal initial rest state and equal 8 m/s route targets on perpendicular approaches. It runs a separate local Rust hybrid server and portable-model worker, sends measured state, applies Rust speed caps, logs the full wire/state/control history, and pauses/brakes the cars on completion or a guard. Native AI car avoidance is disabled so its own avoidance does not substitute for Rust yielding.

The first attempt, `runs/grid-hybrid-8e53dbe9ae/`, was aborted by `conflict_braking_infeasible` before crossing. Recorded red speed kept increasing despite a falling Rust cap. Installed BeamNG Lua showed `set_line` inserts a fixed per-node manual speed (`manSpeed`), which takes precedence over the route speed limit. The runner now supplies native coordinate script points without per-node speeds, allowing the live global cap to control speed. Failed evidence is retained.

The corrected pass is `runs/grid-hybrid-49835329e2/`: both cars cleared after 14.4 simulation seconds, 145 frames / 290 vehicle rows, with zero reported damage for both. Rust yielded red while blue proceeded. At 4 s, red measured 2.22 m/s against a 2.22 m/s cap while blue measured 6.88 m/s; at 8 s, red was 2.23 m/s and blue 7.98 m/s. Red was released after blue clearance and reached 7.79 m/s at 14 s. Minimum sampled reference-point distance was 25.32 m. Telemetry, advice, wire timing, model versions, initial state and source scenario are retained in the run directory. This is one successful local hybrid demonstration, not a remote pass or general collision guarantee. Runtime test services were stopped; the final Grid Plane scene is paused with both cars beyond the crossing.


## Repeatable uncoordinated versus local hybrid comparison

`scripts/run_grid_crossing_comparison.py` runs two fresh matched Small Grid trials in order, using the calling BeamNG Python environment. First it passes `--baseline` to `scripts/run_grid_hybrid_crossing.py`, creating no Rust or model-worker process and commanding both perpendicular cars to 8 m/s without native AI car avoidance. The scene pauses on a damage threshold, is displayed for five wall seconds by default (`--pause-between`), then resets both configurations/poses into a fresh scenario for local Rust hybrid control. Both use matching Vivace 160 DCT configurations, different colors and equal initial rest/target settings. Each trial saves telemetry and a summary, and the wrapper writes a comparison manifest. Errors and controller fallback stop the sequence; the final scene is paused.

User-authorized execution on 2026-10-18 produced `runs/grid-comparison-01f1eced05/`. Baseline `runs/grid-baseline-7ba0f1d1c8/` stopped after 7.4 simulation seconds with red damage 4349.547 and blue damage 4449.945, minimum sampled reference separation 2.899 m and neither car cleared. Hybrid `runs/grid-hybrid-89803b0cbb/` yielded red and cleared both after 14.4 simulation seconds, with zero damage for both and minimum sampled reference separation 25.193 m. Damage is measured; verified contact attribution remains unavailable. This paired comparison supports this specific local configuration, not general collision prevention or a LinuxONE physical pass. Both trial sources were copied into the comparison directory.

Run again with `/home/vinnavan/Projects/beamng-autonomous/.venv/bin/python scripts/run_grid_crossing_comparison.py` while BeamNG's API is listening on port 25252. This loads fresh Small Grid scenes and intentionally runs the uncoordinated impact comparison before resetting for the controlled trial.

The paired runner now streams both trials to the local display-only observer. Keep the dashboard Rust process listening on `127.0.0.1:3000` and open `http://127.0.0.1:3000/`; the runner checks `/health` before connecting to BeamNG and accepts `--dashboard-url` to override the origin. On this host the dashboard currently returns `ok`, but the BeamNG API is not listening on port 25252, so the comparison cannot start until BeamNG's server is enabled.
