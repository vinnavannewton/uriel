---
title: "Wiki history"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Wiki history

## ingest | Initialize IBM / Arc Angel wiki

Created an Obsidian-compatible project wiki using the original Karpathy LLM Wiki structure. Preserved the PRD, recorded user decisions, and captured a static source inspection with file hashes. Added architecture, protocol, coordination, dashboard, operations, recording, decisions, status and open-input pages.

Distinguished the PRD's complete-backend goal from the current prototype. Recorded source-derived reservation/freshness/recording concerns without modifying executable code or running deferred behavioural tests. Added agent entry instructions and checked internal links and local source references.

## ingest | Uriel complete project context

Preserved the supplied Uriel handoff and hash/provenance. Updated current naming, arrival-time ML scope, Ubuntu 24.04/s390x target, team/event preparation and submission context. Added ML, event preparation and source-reconciliation pages; updated index and topic summaries.

Recorded the handoff's reported prohibition on continuation projects as superseding the older prototype allowance in planning. Preserved the factual existence and historical checks of the earlier prototype without declaring submission eligibility. No embedded commands were executed, no external form/artifact was modified, and no application code or behavioural tests were changed/run. Wiki links and source snapshot integrity were checked.

## maintenance | Remove displayed project dates

Removed calendar dates from current project documentation at the user’s request. Preserved immutable raw snapshots and date-bearing source paths and external URLs so provenance links remain usable. No executable code changed or behavioural tests ran.

## maintenance | Remove remaining project dates

User explicitly extended date removal to the entire folder, overriding raw snapshot preservation for this edit. Removed remaining calendar dates and year-bearing event URLs, renamed raw files, updated references, and refreshed the edited handoff hash. Original source hash retained. Application code and behavioural tests unchanged.

## [2026-10-16] workflow | Shared Uriel skill and named team ownership

Created repo-local `.agents/skills/uriel` with automatic selection enabled, a concise project workflow, and a detailed contract for writing manual scenario guides. Recorded Vinnavan as lead/server/BeamNG/integration owner, Manikantan as ML worker/dataset/labels/evaluation owner and server contributor, Ankita as dashboard owner, and Ananya as guided testing/evidence owner.

Added teammate usage instructions and a labelled summary of the latest PRD from its earlier reading because the original Downloads path is no longer available. Recorded the user's report that reuse is allowed without presenting independent organizer verification. Maintained source/implementation/result distinctions. No application code, simulator tests, shared server deployment, Git initialization, commit or push was part of this task.

## [2026-10-16] ingest | Preserve complete Uriel PRD v1.0

The lead supplied the complete PRD from Documents. Preserved an exact project-local copy and SHA-256 provenance, replaced the summary's missing-original note, and updated source navigation and teammate instructions. The previously approved named team roles take precedence over the generic PRD table. No application implementation, deployment or behavioural testing was performed.

## [2026-10-17] investigation | Grid Plane BeamNG connection preparation

Confirmed a running native BeamNG.tech process, no listener on the proposed port 64256 and no BeamNGpy in the default Python environment. Verified that the workspace still lacks the Python bridge. Consulted official documentation for the in-game BeamNGpy Server control and recorded the proposed two-car perpendicular Grid Plane setup in [[operations]]. No simulator connection, spawning, driving, dataset collection or application changes were performed.

## [2026-10-17] simulator | Authorized two-car head-on baseline

The user replaced the crossing with an immediate head-on collision and reported the server enabled. Connected with BeamNGpy 1.36, reused the player's Vivace configuration for matching red/blue cars, placed them approximately 100 m apart and drove opposing explicit AI lines at a requested 50 km/h with avoidance disabled. Both damage sensors increased; saved 120 samples plus configuration, summary, verification and controller under `runs/headon-d0f1ef6424/`. Disabled AI and applied brakes after recording. Documented the unsupported bulk-state request and working per-vehicle sensor polling. No Uriel coordinator/ML integration, training, deployment, commit or push occurred.

## [2026-10-17] implementation and simulator | Plain Grid Plane cooperative pass

User authorized coordinated dodging, then explicitly deferred live obstacles. Added a bounded Python paired-path planner/controller and tests. Open-space plan shifts both cars to their own left, holds through passing and returns to the original line; geometry fixtures cover known static circles and no-feasible-plan braking, but no obstacles were spawned or tested physically. Diagnosed parts-selection provenance mismatch, BeamNG AI front/reference alignment and independent bullettime pause before a completed live pass.

Run `runs/avoidance-3d366e13bd/`: 125 samples, zero new damage, closest-approach speeds about 29.85/29.92 km/h, minimum sampled enclosing-circle clearance 1.557 m. Verified a later physics pause and changed future controller cleanup to pause rather than assume brake acknowledgements prove a stop. Fourteen Python tests passed; offline Cargo tests completed with zero tests. Updated [[operations]], [[coordination]], [[recording]] and [[implementation-status]]. Preserved aborted attempts and exact executed-source snapshots. No trained model, integrated Rust bridge, obstacle acceptance, deployment, commit or push.

Repeated the live pass after fixing cleanup to pause immediately on normal completion or guard abort. Final run `runs/avoidance-35d4b5dbb9/` recorded 128 samples, zero new damage, closest-approach speeds 30.01/30.06 km/h and 1.519 m minimum sampled circle clearance. Verified source hashes, physics paused and both final poses stable across independent live observations. The earlier brake inputs had not held the cars stationary, so the simulator pause is recorded explicitly rather than claimed as emergency braking. Final Python suite: 14 passing tests; syntax and diff whitespace checks passed. Still no spawned obstacles or training.

## [2026-10-17] integration | Rust maneuver-v2 and live BeamNG controller

User authorized extending the speed-only contract and connecting Python, asking whether that completes head-on coverage. Implemented separate `/ws/headon` maneuver-v2 messages, Rust-authoritative origin paths, strict two-car/identity/epoch/frame/state validation, prepare/accept/execute/pause/complete lifecycle, fixed maneuver geometry and telemetry lease renewal. Python now uses Rust by default, applies both paths once, applies server speed caps, validates responses, records correlated wire/telemetry and pauses the simulator on completion/failure. Explicit standalone baseline remains available. Legacy v1 `/ws/bridge` remains compatible; head-on snapshots join the existing read-only dashboard APIs.

Independent code review found a receive wait could conceal old-lease expiry and frozen sensor times could renew execution. Added failing regressions, bounded receives by the previous lease with 100 ms pause margin, required advancing execution timestamps in Rust, and obtained a follow-up review with no new actionable findings. Blocking simulator calls and process-death watchdogs remain limitations. Synthetic protocol evidence `runs/protocol-check-fed323c18e/` verifies ownership/reset protection, frozen-state pause, v1 compatibility and world counts without simulator commands.

Final live run `runs/avoidance-e8d6280410/`: 127 simulator samples, 129 correlated Rust telemetry/plan exchanges, two path acceptances, stable maneuver ID, measured pass/return and server `complete`. Zero new damage, closest speeds 30.10/30.06 km/h and minimum sampled enclosing-circle clearance 1.522 m. Independent readback verified physics paused and final poses stable. Preserved executed sources, hashes, filtered server events, API snapshots and new immutable S8 provenance. Nine Rust tests, 21 Python tests, offline build, formatting/syntax/whitespace checks passed. Updated README, contract examples/dependency pinning and relevant wiki pages/index. Local server remains running. This completes the basic plain-map algorithm/integration demonstration; ML, full U-S03 obstacle coverage, varied physical/fault/load acceptance and LinuxONE deployment remain unverified. No commit or push.

## [2026-10-17] deployment preparation | LinuxONE source and service staging

User authorized SSH setup. Verified Ubuntu 24.04.5/s390x, existing Rust toolchain and available resources. Copied 69 working-source files into `/home/linux1/uriel`; all hashes matched and 21 Python tests passed remotely. Installed a localhost-only user-service unit and enabled lingering, preserving existing server tools. Added `deploy/linuxone-build-start.sh` and `deploy/uriel.service`; helper syntax passes. Native Cargo build/start is pending the user-run command under the existing long-build preference, so no remote Rust health or integrated simulator success is claimed. Prepared laptop localhost:3300 SSH forwarding; local port-3000 service preserved. No keys, runtime bulk data, public HTTP exposure, ML worker, commit or push. Updated [[operations]] and [[implementation-status]].

## [2026-10-17] dashboard | Head-on 2D monitor and preview

Added a head-on-specific live view that plots the two server paths, current car positions, maneuver phase and path acknowledgements. The explicit Preview demo animates synthetic example data and says it is not BeamNG telemetry. Rebuilt/restarted the remote LinuxONE service with the changed embedded frontend; `/health` and served-page checks passed. A live run attempt exceeded the 350 ms handshake wait over the SSH tunnel before receiving a plan; TCP RTT was about 325 ms and no path was applied. The simulator remained paused. Keep the 500 ms coordinator lease and 100 ms pause margin; remote physical acceptance remains unverified. [[dashboard]], [[operations]]

## [2026-10-17] simulator and dashboard | Local-coordinator head-on pass

After the remote timing limit, the user authorized one trial. Built an isolated local release server on port 3001 and ran the two-car empty-grid avoidance bridge against it; the port-3000 service and LinuxONE service were preserved. The run completed and returned both cars to the center line: 127 samples, 129 Rust plans, two accepted paths, 1.551 m minimum sampled enclosing-circle clearance, zero damage increase and paused final physics. Dashboard API at `http://127.0.0.1:3001` retains the final disconnected world and plan. Evidence is `runs/avoidance-71873434af/`; no obstacles, ML or remote server coordination. [[dashboard]], [[operations]]

## [2026-10-17] dashboard and simulator | Follow active head-on world

The user reported the live map was not following vehicle movement. Fixed stale selection so a disconnected head-on world yields to the newest connected head-on world, added an app.js cache version, and rebuilt/restarted only the isolated local dashboard server. During the repeat `runs/avoidance-82ebb49eb5/`, the selected API world was connected, frames 77→87 advanced in one second and both car positions changed. The run completed in 12.9 seconds with 127 samples, 129 plans, both paths accepted, zero damage increase, 1.523 m minimum sampled enclosing-circle clearance and physics paused. Browser visual screenshot QA was unavailable. [[dashboard]], [[operations]]

## [2026-10-17] simulator | User-requested head-on dashboard repeat

Ran `runs/avoidance-5eaceb9726/` against the isolated local Rust coordinator on port 3001. The maneuver passed and returned, with 129 BeamNG samples over 13.1 seconds, 131 server plans, zero damage increase, 1.540 m minimum sampled enclosing-circle clearance, and the scene paused after completion. A post-run `/api/worlds` read showed the latest head-on world and both vehicle positions. The browser was not visually inspected, and this was not a LinuxONE or ML run. [[dashboard]], [[implementation-status]]

## [2026-10-17] dashboard | Proportional Grid Plane and live car motion

Changed the head-on 2D map from a laterally stretched lane view to a proportional XY Grid Plane with 10 m grid squares and coordinate labels. Vehicle icons now interpolate over each 500 ms telemetry interval and stop when frames stop advancing. Rebuilt the optimized local Rust dashboard, restarted only `uriel-dashboard-demo.service` on port 3001, and verified `/health` plus the served cache-versioned HTML/JavaScript markers. Browser visual QA and a new simulator trial were not performed. [[dashboard]], [[implementation-status]]

The restart cleared the previous head-on world from the in-memory `/api/worlds` list; the browser needs a refresh and a new connected run for live telemetry. The Preview demo is synthetic only. [[dashboard]]

## [2026-10-17] simulator tooling | Reusable intentional head-on baseline

Added `scripts/beamng_headon_collision.py` so the user can run the collision baseline themselves. It defaults to a no-connection dry run; `--run` validates `smallgrid` and an allowed Vivace setup, positions two opposing cars, records state/electrics/damage telemetry, stops at a configurable damage threshold or time limit, and pauses/disables AI during cleanup. `--help`, syntax compilation and the default dry run passed; no simulator connection or collision was run. Documented invocation and the limitation that this standalone baseline does not stream to the Rust dashboard. [[operations]], [[implementation-status]]

The user's first execution, `runs/headon-collision-963b23ac88/`, stayed stationary for all 121 samples: both velocities were zero, damage stayed at zero and both `parkingbrake_input` values remained 1. The runner had asserted parking brakes during setup but not released them before starting AI. Explicitly release/check the brake before launch and add a 2.5-second/1 m no-motion guard. Rechecked Python syntax, help and dry run only; no BeamNG rerun was performed. [[operations]], [[implementation-status]]

## [2026-10-17] simulator tooling | Fix paused launch verification

The user's next run `runs/headon-collision-c956943971/` stopped before telemetry because the runner checked `parkingbrake_input` immediately after queuing a release while physics was paused; electrics remained on the previous frame. Source inspection also found physics was never resumed after AI paths were queued. Removed the stale paused sensor assertion and explicitly resumed the scene before live telemetry. The position-based launch watchdog remains. Python source and unit checks passed; no BeamNG simulation was started, so successful collision execution is still unverified. [[operations]], [[implementation-status]]

## [2026-10-17] simulator tooling | Correct Vivace DCT Drive selection

User run `runs/headon-collision-a64c3b9895/` recorded advancing simulation time, released parking brakes and engines revving near 6530 RPM while both DCTs stayed in Park. Inspected installed BeamNG.tech control handler and DCT selector mapping: `gear=1` is Park, `gear=2` is Drive. Updated only the standalone collision runner to query gearbox type, choose the correct forward selector and record launch-failure diagnostics. Added three selector regression tests; all 24 Python tests, default dry run and whitespace checks passed. No simulator execution, service restart, deployment or commit. Updated [[operations]] and [[implementation-status]]; physical verification remains pending.

## [2026-10-17] dashboard integration | Display the intentional collision runner

User reported a blank dashboard during the collision trial. The runner previously bypassed Rust entirely, so it sent no vehicle state to the map. Added a separate authenticated display-only HTTP contract, bounded latest-world storage, input/sequence checks, measured state publishing from Python and a collision-specific UI label with fixed grid bounds. Defaults to localhost:3001; `--no-dashboard` preserves independent operation. Synthetic initial/moving/final frame roundtrip passed on a separate Rust process without BeamNG. All 11 Rust tests, 24 Python tests, debug/release build and JavaScript/whitespace checks passed. Local port-3001 service updated; no collision was launched and browser automation was unavailable. Updated [[protocol]], [[dashboard]], [[operations]] and [[implementation-status]].

## [2026-10-17] dashboard | Render route-free Grid Plane with two measured dots

Screenshot showed a blank grid. Live API inspection found both cars from user run `headon-collision-a5953f0c73`; its runner summary records impact and paused physics. Root cause: the renderer returned for empty scenario routes, though collision observation intentionally has none. A DOM regression failed with zero markers before the fix, then passed with two finite markers, motion updates and completed-run retention. User clarified the desired view is just two moving dots, so removed head-on car icons, visible marker names and route/path overlays. Rebuilt/restarted only the local port-3001 dashboard and restored its actual recorded final measurements as disconnected. No simulator run or browser automation was performed. Updated [[dashboard]], [[operations]] and [[implementation-status]].

## [2026-10-17] simulator tooling | Convert the user-run script to cooperative dodging

User requested dodging instead of crashing in the same script. Reused the Python paired-path planner with translated 110 m starts, front alignment, 30 km/h default and measured pass/return completion; retained DCT selector corrections and live two-dot telemetry. Added state/predicted-overlap and path-deviation pause guards, incomplete timeout outcome and source regression coverage for translated shared-dodge paths and speed envelope. Observation contract accepts dodge mode and labels the UI accordingly, without requesting a Rust maneuver. All 12 Rust tests, 26 Python tests and the map DOM regression passed; release build/JavaScript/whitespace checks passed. Updated local dashboard service only; no new BeamNG execution, obstacles, ML, remote deployment or commit. Updated README, [[operations]], [[protocol]], [[dashboard]] and [[implementation-status]].

## [2026-10-17] dashboard | Minimal live car icons

At user request, replaced the two map dots with compact red/blue car silhouettes, small wheels and a cabin. Existing measured-position interpolation and heading rotation remain; no labels or path overlays were added. JavaScript syntax, route-free DOM motion/retention regression and whitespace checks passed. Rebuilt the embedded UI and refreshed only the local dashboard service, retaining the latest recorded completed observation. No simulator trial was started. Updated [[dashboard]] and [[implementation-status]].

## [2026-10-17] dashboard | Make car direction visible

User could not distinguish front from rear on symmetric markers. Changed the car body to a tapered nose and square rear, with pale headlights, red tail lights and a directional windshield. Local +X remains forward and measured-heading rotation is unchanged. JavaScript syntax, existing DOM motion/retention regression and whitespace checks passed; refreshed the local embedded dashboard and retained completed observations. No simulator run. Updated [[dashboard]].

## [2026-10-17] fix | Add missing BeamNG connection helper

Added root-level `connect_beamng.py` after the user reported the suggested file did not exist. Supports an explicit installation path, BNG_HOME, port selection and connecting to an existing local instance. AST syntax validation passed. No dependency installation, simulator launch, behavioural testing, deployment, commit or push performed. This helper does not implement the Uriel bridge; documented its scope in [[operations]].

## [2026-10-17] setup | User-authorized two-car crossing placement

User authorized starting U-S01 and requested two matching cars with different colours at 90 degrees. Connected to the local BeamNG API; existing vehicles were both `etkc` on uneven terrain. Prepared a `smallgrid` scenario named `uriel_crossing_setup`, with red/blue `etkc` cars at (-40,0,0.5) and (0,-40,0.5), aimed toward a virtual crossing at (0,0). Requested AI disabled, brakes applied and simulation paused. This is scene setup, not a training dataset or a crossing acceptance run. Execution outcome is recorded below after API verification.

API execution completed. Initial sensor inspection found the red car facing away; corrected its rotation by teleport while paused. Final measured forward directions: red (1,0,0), blue approximately (0,1,-0.011), confirming perpendicular horizontal approaches toward (0,0). Both are about 40 metres from that centre. No automated driving, collision experiment or training performed. Scenario file's original red rotation is not a verified reusable reset; live corrected state is authoritative.

## [2026-10-17] verification | Three AI-driven Small Grid collection trials

User explicitly requested AI driving, three trials and immediate data collection, overriding the earlier test deferral for this task. Added `collect_crossing_trials.py` and ran it against the existing local BeamNG.tech connection. Three fresh `smallgrid` scenes used matching red/blue `etkc` cars on perpendicular approaches. BeamNG scripted AI drove both; no Rust coordination or ML model controlled them. Nominal target speeds were 8/8, 8/8 with blue delayed three seconds, and 10/6 m/s. Actual timing differed from those requested schedules.

Evidence: `runs/crossing-dd9a98dfb090402eb71b3eed34c6661c/` contains batch metadata, exact collector source/hash and per-trial telemetry, arrival labels and summaries. Each trial records 20 simulation seconds at measured 0.1-second intervals, 201 samples per vehicle: 1,206 telemetry rows total. All six front-point zone arrivals were observed. Trial 1 red/blue arrivals: 9.4/9.4 s, with damage increases on both cars. Trial 2: 9.4/10.2 s, no recorded damage increase. Trial 3: 8.3/11.3 s, no recorded damage increase. Damage readings are not a complete contact detector; zero-contact or body-clearance acceptance is not established.

Verified all three completion states, sample counts, finite position/speed/damage values, monotonic 10 Hz simulator timestamps, label/time consistency and archived source hash. BeamNGpy version 1.36 recorded. Final scene was paused, both AI controllers disabled and brakes requested. No model training, held-out evaluation, LinuxONE deployment, commit or push. Updated [[recording]], [[ml-arrival-prediction]] and [[implementation-status]]; the coordinator bridge remains unimplemented.

## [2026-10-17] investigation | Current-intersection traffic trial reset defect

User explicitly authorized three trials with traffic at the two-car West Coast USA scene shown in screenshots. API confirmed `thePlayer` and `clone`, both `etkc`, on West Coast USA. Added standalone `collect_traffic_trials.py`; selected existing road-node targets DR193_2 and DR602_5 and an explicitly approximate front-reference arrival disk centred at (-454,146,100), radius 8 m, height tolerance 4 m.

Initial batch `runs/traffic-614f63ac95a94d16834ec4a42be6c6b0` completed three attempts but is marked INVALID_FOR_COMPARABLE_TRIALS: starting poses drifted between runs, trial 2 clone started inside the arrival zone and trial 3 clone started damaged. Only the first of four asynchronously spawning background cars was attached to telemetry. Preserved all attempts and marked their manifest/README invalid; do not use their apparent arrivals as comparable training evidence.

Corrected recorder to wait for four background vehicles, restrict traffic participants to background vehicles, reset traffic before subject teleport, omit separate recovery, and verify subject position drift below 1 m and initial damage at most 1 before starting. Replacement batch `runs/traffic-3ab480e0a6234b60ad33b982849b74af` is underway with all four background vehicles attached. Actual execution results will follow. No Rust coordinator or trained model is involved.

## [2026-10-17] verification | Corrected West Coast traffic collection completed

Replacement batch `runs/traffic-3ab480e0a6234b60ad33b982849b74af` completed all three 30-second trials, each with two subjects and four recorded background cars. Verified 1,806 rows per trial (5,418 total), 301 samples per vehicle with consistent 0.1-second simulator intervals, and archived collector source hash. Subject starting poses were checked and damage was zero at the start of every trial.

Approximate front-reference zone arrival times for thePlayer/clone: trial 1 6.8/16.6 s; trial 2 8.3/16.4 s; trial 3 6.6/20.0 s. No subject damage increase in trials 1 and 3; trial 2 clone increased by about 0.29848 simulator damage units. These are not collision detector results. Trial 3 thePlayer had no recorded background reference within 50 m; all other subject/trial combinations did. Traffic distribution was unseeded. The road scene is not a verified exact 90-degree crossing and arrival gaps do not establish a conflict challenge. Final collector cleanup requested pause; subjects had AI disabled and brakes applied. No Uriel controller or ML training was used. Earlier invalid attempts remain preserved separately.

## [2026-10-17] experiment | Fresh randomized experiment setup and preserved failures

User supplied a detailed specification and explicitly requested immediate execution of three new seeded Small Grid AI trials at 30 Hz. Inspected the prior recorder and live West Coast scene; archived the four existing simple_traffic configurations. Added `scripts/fresh_experiment.py` with separate seeds, immutable batch directories, six-vehicle telemetry, spawn-OOBB-based event proxies, explicit unknown contact evidence and per-run quality reports. Source inspection confirmed installed BeamNGpy speed-polyline AI, set_velocity and bounding-box methods. Synthetic seed reproducibility and entry/clearance detector checks passed; syntax passed.

First batch `uriel_experiment/experiment_a972954ae237434f8d60ee1900441d55` preserved fresh_001, fresh_002 and fresh_003 as failed setup attempts: subject cars rolled backward roughly 8.8 m during the braking hold and failed position validation, so no driving trial began. A subsequent diagnostic setting realistic_automatic shifting and drive gear held the red car within about 1 mm horizontally over one simulation second. Added the explicit shift setting and setup-state evidence. The user was told about the failures and the separate retry; they are not silently replaced. Retry batch `uriel_experiment/experiment_631bf60975d24a4fa44631ff23cf58b6` is running with the same three recorded seeds. Requested-experiment text and executed source are preserved per batch. Results follow after verification.

## [2026-10-17] verification | Fresh randomized six-vehicle pilots completed

Retry batch `uriel_experiment/experiment_631bf60975d24a4fa44631ff23cf58b6` completed fresh_001/002/003 with seeds 903101/903102/903103. Each run recorded six stable vehicle IDs for 25 simulator seconds: 751 samples per vehicle, 4,506 rows per run, 13,518 total. All subject initial damage readings were zero. Both subject entries and downstream rear-proxy clearances were observed in all runs. All background configurations, randomized values, measured initial speeds, geometry, exact executed collector source and request text are archived with the batch. Final simulation was paused and AI disabled with brakes requested for all six cars.

Subject front-entry/rear-clearance seconds: fresh_001 red 6.967/8.367, blue 9.334/10.900; fresh_002 red 7.800/9.533, blue 7.067/8.300; fresh_003 red 6.600/10.734, blue 6.934/9.367. Damage increases: fresh_001 blue about 6301.63; fresh_002 neither subject; fresh_003 red about 3346.73 and blue about 7581.03. Red deviated from its route in fresh_003. Damaged-body labels remain ambiguous spawn-OOBB proxies. Damage is not verified contact evidence; contact fields remain null. No Uriel control or ML training/safety result is claimed.

The initial exact 1/30-second validation falsely flagged actual 33.0/33.5 ms intervals produced by the simulator's 0.5 ms physics quantization. Added `scripts/validate_fresh_experiment.py` to verify <=0.51 ms interval/phase variation, the 25-second horizon, 751 frames/vehicle, frame synchronization, stable IDs, finite values, bbox-derived labels, recorded event agreement and dimension consistency. All three revalidated as PASS_WITH_LIMITATIONS with zero issues. Preserved original strict reports as `validation_report_initial.json`; telemetry and events were not changed. Validator source is archived. Fixed the recorder's future timing tolerance; a quantized-timing check passed and an intentionally missing frame was rejected.

Known missing values are the first sample's acceleration and every verified-contact field; gear and control readings were present. Geometry is configured virtual geometry with uncalibrated spawn-body proxies, not road or deforming-body acceptance. Combined randomized settings/outcomes are in `trial_summary.csv`, with a human-readable README. Updated [[recording]], [[implementation-status]], [[ml-arrival-prediction]] and [[sources]]. Earlier failed experiment and its three failed setup runs remain separate and preserved. No deployment, commit or push.

## [2026-10-17] implementation | Parameterized crossing recorder and 60 Hz collection

User requested a reusable script for the same scenario, configurable trial count and 2x speed with 60 Hz telemetry. Updated `scripts/fresh_experiment.py` with argparse options for trials, duration, requested multiplier, simulation-time telemetry Hz, seed, host/port, output and background config. Preserved the scenario's fixed geometry/models and seeded randomization. Copied exact prior background configurations into a project asset; removed the ephemeral /tmp dependency. Added pinned `requirements-beamng.txt` and `scripts/BEAMNG_RECORDING.md`.

Corrected stopped-before-entry detection to use a half-second time window at all supported Hz, timestamped AI launch commands against actual sampled frames, and added actual wall/simulation duration and speed-target measurements to metadata and summary CSV. The speed setting paces fixed-step recording toward the requested multiplier without skipping samples; it does not guarantee actual 2x throughput. Installed API probes confirmed positive BeamNG speed_factor=1 advances 50 ms per step, which cannot provide 60 Hz direct observations. Time scale changes did not double explicit physicsStep advancement. Frame-limiter removal caused manual-step timing drift and was reverted.

First short CLI check `runs/collector-checks/experiment_645bfc0a1b654e42a3be7d9bd5d80302` preserved a failed validation and a summary metadata-key error. Corrected the sampling/speed metadata and retained the deterministic limiter. Final live check `runs/collector-checks/experiment_a0577f3a98994491ad8c99ebfef03849` exited successfully: one simulated second, 61 samples per vehicle (366 rows), measured 59.999997 Hz, PASS_WITH_LIMITATIONS. It took 3.1339 wall seconds, achieving 0.3191x, so requested 2x was NOT achieved. All scene/label/contact limitations remain; this short check does not validate complete crossings at 60 Hz. Synthetic checks accepted quantized timing at 30/60/120 Hz, rejected a missing frame and checked time-based stop detection and CLI defaults. Simulator left paused; saved frame-limit settings restored. Updated [[operations]] and [[recording]]. No deployment, commit or push.

## [2026-10-17] verification | Ten randomized 60 Hz trials; Python environment correction

The user ran `python scripts/fresh_experiment.py --trials 10 --speed 2 --telemetry-hz 60`; system Python did not have BeamNGpy. Confirmed BeamNGpy 1.36 in `.venv` and used `.venv/bin/python`. The first live attempt created `uriel_experiment/experiment_aae76144cd1a4556bf2b1737253a6035`: runs 001–004 completed, 005–006 encountered equal consecutive simulator timestamps and division by zero in finite-difference acceleration, and 007 was interrupted. All partial/failed files remain preserved. Changed the acceleration calculation to leave that sample null when elapsed time is not positive, syntax-checked the script, then reran the full requested ten trials in `uriel_experiment/experiment_c03ce1dbb91143a4b66cdb7f56c7fbef` with seeds 903101–903110.

The completed batch contains ten 25-second simulator runs, six stable vehicle IDs per run, 1,501 samples per vehicle and 9,006 rows per run (90,060 total). All ten reports are PASS_WITH_LIMITATIONS with no validation issues; all subject entry and rear-proxy clearance events were recorded. Per-run entry/clearance, damage and route-deviation observations are in [[recording]] and `trial_summary.csv`. Mean achieved wall-clock speed was 0.333x versus requested 2x; measured telemetry rate was 60 Hz. Damage is not contact proof, and geometry remains virtual with uncalibrated spawn-OOBB event proxies. No Uriel coordinator, ML training, safety acceptance, deployment, commit or push. Updated the run instructions to call the project interpreter directly and updated [[operations]], [[recording]], [[ml-arrival-prediction]] and [[implementation-status]]. Simulator cleanup paused the scene and disabled AI/braked vehicles; saved frame limiter settings were restored.

## [2026-10-17] implementation and verification | Keep BeamNG graphics FPS at 60

User requested that the frame rate be set to 60 and left unchanged. Updated `scripts/fresh_experiment.py` to set the BeamNG graphics FPS limit to 60 for setup, recording and cleanup, and to leave it at 60 on exit instead of restoring prior settings. The `--speed` value remains BeamNG's deterministic physics factor (1–8); at the 60 FPS cap its theoretical wall-clock ceiling is `3 × factor`, but measured throughput depends on simulator and telemetry overhead. Per-frame sampling remains capped at `20/factor` Hz, so factor 8 records 2.5 Hz rather than 60 Hz. Updated [[recording]], [[operations]] and [[implementation-status]].

Syntax check passed. Live short check `runs/collector-checks/experiment_1da459559d8d4cc5b2253412a99490e2` completed one 4-second factor-8 trial: 11 samples per vehicle at 2.5 Hz and 2.586x measured wall-clock speed (24x theoretical ceiling); validation completed with PASS_WITH_LIMITATIONS. Four seconds was too short for either subject to reach the virtual crossing, so arrival/clearance labels are censored. This validates recorder execution and sampled timing, not full crossings or 8x throughput. The simulator was paused and AI disabled/brakes requested; FPS limit is intentionally left at 60. No model training, deployment, commit or push.

## [2026-10-17] repository | Keep raw BeamNG recordings local and ignore them

User requested that collected telemetry remain in the project folder, while all non-telemetry project changes are pushed. Existing recordings are already stored under `runs/` and `uriel_experiment/`; none were moved. `.gitignore` now excludes raw `telemetry.csv`, `arrival_labels.csv` and `events.jsonl` files plus Python bytecode, while leaving code, configs, documentation, experiment metadata and summary files eligible for Git. This preserves local recordings and avoids committing large frame-level datasets. Updated [[recording]].

## [2026-10-17] repository integration | Combine crossing collectors and head-on work

User authorized checking teammate main and pushing this work. Fetched teammate commit `d5038e6`, which adds standalone 90-degree/traffic collectors, seeded six-vehicle experiments, validator, dependency/configuration files and small evidence artifacts. Preserved those files and combined shared wiki/ignore changes with local head-on coordination, dodge runner, telemetry-only dashboard and directional car markers. Source IDs conflicted: S8 remains the teammate fresh-experiment request; the head-on provenance entry is now S9 (earlier log references to head-on S8 predate this reconciliation). Kept crossing baseline collection separate from actual Rust integration and documented different vehicle IDs/ports and one scenario owner per simulator. No simulator run or remote service deployment was performed for this merge.

Merge validation: 12 Rust tests, 26 Python tests, 26 tracked Python AST syntax checks, map DOM regression, JavaScript syntax, Cargo formatting/check/build, shell syntax and both collector/help and dodge/dry-run checks passed. The isolated localhost protocol checker verified maneuver-v2 and legacy crossing-v1 without simulator calls. All files added by teammate commit `d5038e6` match that commit byte-for-byte; private-key blocks are absent from outgoing files and telemetry/build/virtualenv ignore checks passed.
