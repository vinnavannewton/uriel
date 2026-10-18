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

## [2026-10-17] implementation | Configurable BeamNG AI aggression

User requested a recorder flag for AI aggressiveness and BeamNG's own AI naming. Added `--ai-aggression` with BeamNG endpoint names `conservative` (0.3) and `aggressive` (1.0), plus custom numeric values in the supported 0.3–1.0 range. The selected value is applied after each car's AI route is set and recorded in per-sample telemetry, trial summary and experiment metadata. Telemetry now records BeamNG's built-in `manual` mode for route-following AI and `disabled` after/for inactive vehicles. BeamNG.tech 0.39.4 supports the `SetAiAggression` vehicle API message; a compatibility fallback handles the installed BeamNGpy 1.36 package, which does not expose its newer public wrapper. Updated [[recording]] and the recording instructions.

Static syntax, CLI parsing, numeric/name mappings and the BeamNGpy 1.36 message fallback passed checks. No simulator trial was run, in line with the deferred behavioral-testing constraint. Two local experiment output folders appeared during this edit and were left out of the code commit.

## [2026-10-17] implementation | Offline arrival and clearance ML pilot

Acting as Manikantan, the user asked to implement the approved offline `HistGradientBoostingRegressor` plan. Fast-forwarded local `mani` to `main` at `62f423b`, preserving ignored telemetry. Added `scripts/train_arrival.py`, a separate pinned `requirements-ml.txt` environment and `.venv-ml`/`runs/` ignore coverage. The pipeline audits each trial independently, recomputes spawn-OOBB entry/clearance labels, verifies saved timestamps, preserves censored/excluded outcomes, removes target events affected by prior damage/route deviation, samples causal features at up to 5 Hz, groups repeated seeds/configurations, tunes four candidates on validation, and evaluates once on held-out groups against distance/speed.

Ran `.venv-ml/bin/python scripts/train_arrival.py --data-root uriel_experiment --output runs/ml-arrival --seed 42`. It found 58 trial folders, accepted 48, excluded 10 failed/interrupted trials and found no exact duplicates. Entry used 3,150 samples/48 trials/11 groups; clearance used 2,000/26/7. Held-out entry MAE/p95 was 0.398/1.157 s across 3 independent groups; clearance was 0.470/1.670 s across 2 groups. On common moving test rows the models scored 0.363/1.086 s and 0.381/1.484 s, respectively, versus distance/speed at 5.357/19.169 s and 6.196/20.751 s. Many clearance labels were excluded for damage; the small number of independent test groups limits the conclusion. The exact report and artifacts are local at `runs/ml-arrival/pilot-20261017T140717Z-b91ffe98/`; raw telemetry and models remain ignored by Git. Updated [[ml-arrival-prediction]], [[recording]], [[implementation-status]], [[open-questions]] and this catalog via [[sources]]. The offline training run completed; no simulator, live inference, Rust integration, commit or push was performed.

## [2026-10-17] verification | Recheck offline ML completion

At the user’s request, checked accepted data counts, repeated seed/configuration split isolation, simulation-time sampling, elapsed-time target labels, target-specific damage exclusions/censoring, causal speed history, stopped baseline handling and reproduction of every saved held-out prediction after model reload. All passed. Confirmed 48 valid trials across 8 batches. Found and fixed audit serialization rereading malformed validation JSON; a temporary malformed-input check now records an exclusion and returns insufficient data without crashing. Repeated offline training in `runs/ml-arrival/pilot-20261017T141915Z-48132635/`; metrics and held-out predictions match the earlier verified run exactly, and the source hash matches the final environment artifact. `verification.json` records checks. Dependency consistency and whitespace checks passed; model artifacts, environment and raw telemetry are ignored. Corrected a stale trained-ML status sentence and refreshed current evidence links. No simulator execution, live integration, commit or push.

## [2026-10-17] investigation | Sensor-based 90-degree crossing proposal

Explained a proposed RGB/LiDAR perception pipeline in response to the user's request to avoid direct vehicle locations. Checked official BeamNG sensor capabilities and recorded input/ground-truth separation, relative-coordinate tracking, timestamp/calibration requirements, marked-road geometry, occlusion handling, model reevaluation and the distinction between AI route scaffolding and sensor-driven steering in [[ml-arrival-prediction]]. This is a proposal; no new sensor implementation, simulator execution, commit or push was performed.

## [2026-10-17] implementation | West Coast sensor crossing collector

Added `scripts/collect_sensor_crossing.py` for three AI-driven West Coast crossing recordings using the currently loaded `thePlayer` and `clone` vehicles and the existing perpendicular waypoint pair. It records three ego RGB camera views, a 360-degree LiDAR point cloud, ego wheel speed and Advanced IMU data at up to 5 Hz. Sensor files/index and exact simulator ground truth are written to separate ignored `runs/sensor-crossing/` paths; the unknown car's simulator state, model and identity are not part of sensor input records. Updated [[sensor-crossing]], [[recording]], [[implementation-status]], [[sources]] and the index. Syntax/CLI help and whitespace checks passed. No live BeamNG trial or Rust/server integration was run. The loaded clone model, start poses, camera mount directions and route directions still require an in-simulator preflight; no detector/tracker or sensor-track server protocol is implemented.

## [2026-10-17] fix | Allow sensor collector to handle an unloaded clone

The user's startup output showed only `thePlayer` loaded, so the collector's required `clone` lookup stopped before recording. Updated vehicle selection to reuse `clone` when present, otherwise reuse the first non-ego vehicle, and request one BeamNG traffic vehicle when the ego is the only loaded car. The traffic controller is stopped after it spawns, then the selected vehicle is assigned the existing perpendicular AI waypoint for the trials. Run metadata records the selected vehicle ID, model and spawn source; sensor-input files remain separated from ground truth. Updated [[sensor-crossing]], [[recording]], [[implementation-status]], [[open-questions]] and removed a duplicate index link. Static validation passed; no simulator was launched, so random-spawn position, model and route completion remain unverified.

## [2026-10-17] fix | Remove duplicate sensor attachment in crossing collector

The user ran `scripts/collect_sensor_crossing.py`; BeamNG loaded the spawned/selected vehicle, but startup failed while attaching sensors because the ego's `Damage` sensor was attached once before `attach_sensors()` and again inside it under the same name. Removed the second attachment. The failed run is `runs/sensor-crossing/run-0e7c2f415312/`; it did not produce trial telemetry. Python syntax/CLI and diff checks passed after the fix. No simulator rerun was performed; the three trials and random-vehicle route remain unverified. Updated [[sensor-crossing]], [[recording]] and [[implementation-status]].

## [2026-10-17] run | Sensor crossing retry stopped during reset

The user positioned a red ego and black unknown car and explicitly asked to start the scenario. Run `runs/sensor-crossing/run-321cd0c9bcbd/` correctly identified loaded `thePlayer` and `clone` (both `etkc`) and attached the three cameras, LiDAR and IMU. It initially exposed that BeamNGpy's `Vehicle.state` must be polled, so state polling was added before pose capture and per sample. On retry, the 60-step reset call ended with `BNGDisconnectedError`; metadata is `failed`, `trials` is empty, and there are no trial frames. BeamNG's process was no longer running after the disconnect. Updated [[sensor-crossing]] and [[implementation-status]]. Reopen the simulator in Freeroam, verify its API before another attempt.

## [2026-10-17] inspection | Save live West Coast vehicle positions

At the user's request, inspected the active BeamNG map and both loaded vehicles through a read-only API connection. The scene was West Coast USA; `thePlayer` (user-identified red ego) and `clone` (user-identified black unknown) were both ETK K-Series vehicles. Their centers were 174.998 m apart, path directions differed by 0.487° as unoriented lines, and lateral offset was -12.435 m. The current poses therefore do not identify the intended 90-degree crossing; no crossing point was fabricated. Saved both states and the geometry assessment in `runs/sensor-crossing/scene-snapshots/west-coast-live-20261017T154736Z.json`. Updated [[sensor-crossing]] and [[implementation-status]]. No vehicles were moved and no trials were started.

## [2026-10-17] setup | Restore saved West Coast vehicle poses

At the user's request, restored `thePlayer` (red ego) and `clone` (black unknown) from `runs/sensor-crossing/scene-snapshots/west-coast-live-20261017T154736Z.json` in the active West Coast USA scene. Live state readback matched both saved positions within 0.1 mm; the simulator was left paused. The restored positions retain the earlier geometry finding: nearly collinear paths, roughly 175 m apart, with no identified 90-degree crossing. No trials were started. Updated [[sensor-crossing]] and [[implementation-status]].

## [2026-10-17] setup | Load saved poses as a BeamNG scene

The user repeated the request to put the saved positions into BeamNG after the simulator had exited. Launched BeamNG.tech through BeamNGpy, created and loaded `saved_west_coast_poses_20261017` on West Coast USA, and recreated `thePlayer` and `clone` as red/black ETK K-Series vehicles using the saved position and rotation quaternions. Readback was within 8.6 mm for both positions. Physics is paused and the API-owning process remains open so the scene stays loaded. The vehicles still do not form a 90-degree crossing; no trials were started. Updated [[sensor-crossing]] and [[implementation-status]].

## [2026-10-17] run and recovery | Crossing collector disconnected; restore saved poses

The user requested that the scenario run. Starting the existing three-trial sensor collector created `runs/sensor-crossing/run-30da5758e95b/`, but BeamNG disconnected during setup before trial 1; no frames or trials were recorded, and the simulator generated a crash dump. The user then requested the saved positions. Reloaded the West Coast saved-pose scenario with both ETK cars; readback matched the saved coordinates at displayed precision. Scene left paused, with the BeamNGpy API process held open. This setup is still not a 90-degree crossing and does not constitute a trial result. Updated [[sensor-crossing]] and [[implementation-status]].

## [2026-10-17] simulator tooling | Remove camera from sensor crossing collector

At the user's request, changed the West Coast collector to LiDAR-only perception. It attaches no camera and writes no images; ego wheel speed and IMU remain auxiliary motion inputs, while simulator ground truth stays in a separate scoring stream. Changed manual advancement to individually acknowledged one-frame calls, including traffic-spawn waiting, after earlier disconnects on larger step batches. Python syntax compilation passed. No BeamNG API listener was available at the time of verification, and the saved poses remain nearly collinear rather than a verified 90-degree crossing, so no new trial was run. Updated [[sensor-crossing]] and [[implementation-status]].

## [2026-10-17] implementation | State-aware multi-vehicle conflict evaluator

User supplied the Safe Multi-Vehicle Conflict Resolution requirements. Added `src/conflict_resolution.rs` with freshness-aware vehicle classification, conservative stopping feasibility requiring an explicitly validated braking envelope, occupancy-first reservation retention, rear-clearance release, one conflicting reservation at a time with waiting-age priority, an independent proposal monitor, and command/response verification records. Exposed bounded JSON endpoints `POST /api/conflicts/evaluate` and `/api/conflicts/command-result`; both honor `ARC_TOKEN` when configured. Added `examples/conflict-evaluate.json` and preserved the user request at `raw/safe-multi-vehicle-conflict-resolution-20261017.txt` (SHA-256 in [[sources]] S12).

Verification: all 22 Rust unit tests passed; `cargo fmt`, `cargo build`, and a sample HTTP request against an isolated local server passed. The evaluation released only the oldest waiter on one of two conflicting routes, with both monitor decisions accepted. No BeamNG behavioral run was performed. The API does not yet command vehicles or connect to `/ws/bridge`; caller-supplied braking validation, conflict route pairs and prior reservations remain external. LiDAR point-track/ground-truth cross-checks and timed swept footprints are still absent. Updated [[conflict-resolution]], [[coordination]], [[protocol]], [[implementation-status]], [[open-questions]], [[sources]] and the index. No commit or push.

## [2026-10-17] verification | Enforce one-at-a-time and verify command response logging

Extended the evaluator so it grants at most one reservation per managed zone per assessment, including route pairs absent from the supplied conflict table; added a test for that conservative rule. A vehicle already inside receives `continue_to_clear` only when the caller explicitly verifies its continuation path; otherwise it is kept reserved in `SAFE_HOLD`. The latest run passed all 23 Rust tests, formatting, build, JSON parsing and whitespace checks. A fresh isolated HTTP check passed both endpoints and confirmed that command acknowledgement without measured speed remains `response_verified: null`. No BeamNG trial was run. Updated [[conflict-resolution]], [[coordination]] and [[implementation-status]].

## [2026-10-17] evidence | Complete randomized Small Grid LiDAR batch and audit braking run

Completed the previously authorized `uriel_lidar_experiment/experiment_20261017T180027Z_e64db751/` batch after a three-second `PASS_WITH_LIMITATIONS` preflight. Three seeded 25-second trials (781003–781005) each recorded 751 frames × 6 vehicles at 29.9999986 Hz and 500 LiDAR reads per red/blue subject at 20 Hz target. Both subjects entered and cleared the virtual zone in all trials. Trial 3 subject damage increased (red 2,784.127; blue 7,224.108), so its proxy labels are ambiguous; damage/contact remains unverified. The output is about 1.54 GiB, remains in the project folder and is ignored by Git. Small Grid crossing/lane geometry is virtual, and the run did not test the Rust coordinator.

Audited the existing West Coast LiDAR braking run `runs/sensor-crossing/lidar-brake-4bd3f2c95a84/`: its three trials used red target 35 km/h and black target 60 km/h, but red ground-truth speed reached 82.3 km/h and damage readings increased in both cars in trials 1–2, and black in trial 3. This is not verified contact, but it fails safe-controller acceptance; the runner is not calibrated and its target speed behavior needs correction before reuse. Updated [[sensor-crossing]], [[recording]], [[implementation-status]], [[sources]] and the index. No new BeamNG trial, commit or push.

## [2026-10-17] verification | Replay safe conflict sequence; live BeamNG unavailable

The user requested running the scenario. BeamNG.tech remained as a process, but its API port 25252 refused connections; no Rust server was listening on 3000, and the alternate head-on port 64256 was also closed. Because the simulator had a recent crash history, did not restart or alter its process. Fixed the evaluator so a tentative reservation becomes committed when its vehicle is observed occupying the zone. `cargo fmt --check`, all 23 Rust tests, `cargo build` and `git diff --check` passed. Ran a five-frame two-car sequence against a temporary isolated Rust HTTP server: red released/black yielded; red occupied and continued/black yielded; red rear-cleared and black released; black occupied and continued; black rear-cleared and reservation emptied. Every safety-monitor verdict was accepted. This is an API replay only: no simulator commands or vehicle movement occurred. Updated [[conflict-resolution]] and this status. No commit or push.

## [2026-10-17] run attempt | Standalone ML data collection blocked by BeamNG API

The user clarified that the requested data run should not use the Rust server. Rechecked the BeamNG.tech process and both `127.0.0.1` and `localhost` port 25252; both refused the connection, so the existing standalone BeamNGpy collector cannot attach (`launch=False`). Did not start a second BeamNG process or create a failed empty collection: the current simulator instance is still running but its API listener is unavailable, and earlier collector attempts crashed the simulator. No new trial data were collected. The previous randomized Small Grid LiDAR dataset remains available at `uriel_lidar_experiment/experiment_20261017T180027Z_e64db751/`; it is prior data, not a result of this request.


## [2026-10-18] scenario | Save and recheck user-placed West Coast cars

Saved the live red `thePlayer` ETK K-Series and black `clone0` midsize placements/configuration in `scenarios/west_coast_adjacent_navgraph_20261018/`, with native scenario files also installed in BeamNG's West Coast USA user folder. The manifest is the capture/provenance record. A later live recheck differed from saved positions by 0.000127 m and 0.000364 m respectively. No reload or trial was performed. Navigation graph endpoints remain uncaptured: the installed BeamNGpy interface exposes route setters but no route readback, and the inspected recent user-folder files did not contain a corresponding route/session export. The saved layout must not be described as a saved AI route.

## [2026-10-18] correction | Capture live Drive Path Editor routes

The user clarified that the routes were created in the Free Roam editor. Read the installed editor source, then inspected live Lua closure state without invoking the destructive editor onSerialize callback. Found two Drive Path splines linked to the two current cars and exported them using the native Save Session format. Saved `drive-path-session.json` in the project scenario directory and the BeamNG user scenario folder; updated the manifest with stable vehicle names, full node sequences and node coordinates. All referenced navgraph nodes exist. This corrects the prior incomplete capture: the routes are now saved. No AI start, movement command, reload or behavioural trial occurred; numeric vehicle links require relinking after respawn.


## [2026-10-18] Live saved-route trial

User authorized one trial on the saved West Coast Drive Path node sequences. `scripts/run_saved_navgraph_trial.py` connected to the placed cars, used native waypoint AI with the saved 0.3 aggression, lane driving/avoid-cars flags and per-node speeds, and recorded red LiDAR + wheel speed/IMU without cameras or Rust. A ground-truth damage/proximity guard is separate from perception; this is not LiDAR-driven stopping. Run `runs/sensor-crossing/navgraph-trial-5a063eb59f06/` stopped on the damage guard at 22.7165 simulation seconds: 182 paired state frames, 91 LiDAR frames, red damage increase 0 and black increase 6.58238. Minimum sampled reference separation was 72.2499 m; verified contacts remain unavailable, so damage cause is unclassified. Neither car reached its endpoint proximity condition. Cleanup paused physics, disabled AI and applied brakes. This is an incomplete route trial, not collision-free acceptance or a completed arrival-training group.


## [2026-10-18] repeat | Native AI saved-route trial

At the user's request, restored both cars to the saved transforms with reset and ran the saved navgraph waypoint sequences with BeamNG native AI, without Rust or cameras. Run `runs/sensor-crossing/navgraph-trial-69e3eabd7217/` reached its 45.1165-second time limit, recording 424 paired state frames and 178 red LiDAR frames plus wheel-speed/IMU. Minimum sampled car-reference separation was 44.9211 m. Damage increases were red 0 and black 0.971509, below the 1.0 guard threshold but not zero; verified contact/cause remains unavailable. Neither endpoint proximity condition was observed. Cleanup paused physics and disabled/braked both AIs. This is a full recording horizon with unfinished routes, not a collision-free or completed-route acceptance result.


## [2026-10-18] trial | Saved West Coast routes with four traffic cars

Added `--traffic` and `--reset-start` to `scripts/run_saved_navgraph_trial.py`, then executed the user-authorized repeat with four background cars (`clone1`–`clone4`). The traffic manager was explicitly restricted to background cars; both subjects kept their saved waypoint AI routes. Run `runs/sensor-crossing/navgraph-trial-0aa71001e54c/` recorded 204 paired state/traffic samples and 204 red LiDAR frames plus wheel speed/IMU over 45.1500 simulation seconds. Minimum subject-to-subject reference separation was 48.0147 m; minimum sampled subject-to-traffic reference separation was 4.8906 m. Subject damage increases: red 0, black 0.242175 (below guard threshold); background damage was not monitored and verified contacts remain unavailable. Both endpoints were unfinished at timeout. Cleanup paused physics, stopped background traffic and disabled/braked subject AIs. No cameras or Rust were used. Syntax and whitespace checks passed. Traffic spawn is unseeded; this is not a collision-free acceptance result.


## [2026-10-18] implementation | Configurable saved-route trial batches

`scripts/run_saved_navgraph_trial.py` now accepts positive `--trials N` (default 1). Every trial resets subject cars by default, reconnects after cleanup, and saves separate trial directories plus a batch summary under ignored `runs/sensor-crossing/navgraph-batch-<id>/`. `--traffic 4` retains the optional background traffic mode; existing background cars are reused, participants restricted to the requested count, and traffic reset between trials. Guard-stopped attempts remain recorded; setup/API errors stop the batch with partial failure reports. `finished` is an attempt-count status, not a safety or endpoint pass. Offline mocked orchestration checked three-trial execution, reset/traffic arguments, fail-fast reporting and invalid inputs; syntax/help/whitespace checks passed. No live BeamNG trial was run for this change. Repeated fixed configurations must stay grouped for ML evaluation.


## [2026-10-18] trial | Reload saved scene and run with traffic

The user requested another scenario run. First attempt `navgraph-batch-73f9c68a87ea` stopped with zero frames because BeamNG was at the menu (empty mission filename). Loaded the saved native West Coast scenario and verified `thePlayer`/`clone0` present. Retried with `--trials 1 --traffic 4`: `runs/sensor-crossing/navgraph-batch-1fa2070b1469/trial-001/` stopped on the damage guard at 24.1135 simulation seconds, recording 112 paired subject/traffic state frames and 111 red LiDAR frames plus wheel speed/IMU. Red damage increase was 0, black 9.37181; minimum subject reference separation was 53.7534 m. Verified contacts/cause are unavailable; neither endpoint was observed. Four background traffic IDs were clone/clone1/clone2/clone3. Cleanup paused physics, stopped traffic and disabled/braked subject AIs. No Rust or cameras used; this is an incomplete trial, not collision-free acceptance.


## [2026-10-18] repeat | Saved AI routes with traffic

User-authorized one-trial repeat using `--trials 1 --traffic 4` recorded `runs/sensor-crossing/navgraph-batch-b6038d1d7356/trial-001/`: 45.0480 simulation seconds, 208 paired subject/traffic state frames and 207 red LiDAR frames plus wheel-speed/IMU. Minimum subject reference separation was 47.3101 m. Damage increases were red 0 and black 0.233165; verified contacts/cause remain unavailable. Neither endpoint proximity condition was reached. Cleanup paused physics, stopped traffic and disabled/braked both subject AIs. This is a completed recording horizon with unfinished routes, not collision-free acceptance. No Rust or cameras were used.


## [2026-10-18] repeat | Saved AI routes stopped on damage guard

The requested one-trial repeat with four background traffic cars saved `runs/sensor-crossing/navgraph-batch-179ddcaa2152/trial-001/`. It stopped at 22.6665 simulation seconds on black damage increase 5.16970; red damage increase was 0. Recorded 105 paired subject/traffic state frames and 104 red LiDAR frames plus wheel-speed/IMU. Minimum sampled subject reference separation was 68.4933 m; verified contact/cause remains unavailable and neither endpoint was reached. Cleanup paused physics, stopped traffic and disabled/braked subject AI. No Rust or cameras used. This incomplete attempt is not collision-free acceptance.


## [2026-10-18] repeat | Saved-route traffic recording horizon

User-requested single-trial repeat with four AI traffic cars saved `runs/sensor-crossing/navgraph-batch-b1eaa8a831c5/trial-001/`: 45.1510 simulation seconds, 204 paired subject/traffic state frames and 204 red LiDAR frames plus wheel-speed/IMU. Minimum sampled subject reference separation was 47.2709 m; damage increases were red 0 and black 0.0509927. Verified contact/cause remains unavailable; neither endpoint proximity condition was reached. Cleanup paused physics, stopped traffic and disabled/braked the subject AIs. No Rust or cameras used. This completed recording horizon is not completed-route or collision-free acceptance.


## [2026-10-18] scenario and trials | Updated two-car-only editor routes

The user requested saving the newly positioned red/black cars and current graph routes, then three trials without the extra cars. Captured live poses/configuration and two linked editor splines (`red`: junction1_wp25 → junction1_wp3; `bllck`: tunnel_city_A_59 → DR323_3) into `scenarios/west_coast_red_black_20261018/`, installed its native scenario, and verified all node IDs. Preserved the earlier scenario separately. Removed the four previously generated traffic cars and verified only `thePlayer`/`clone0` remained. Added `--scene` to the runner and made the new saved scene its default; syntax/whitespace checks passed.

Executed `--scene scenarios/west_coast_red_black_20261018 --trials 3 --traffic 0`, saving `runs/sensor-crossing/navgraph-batch-fc0e932f6981/`. Trial 1: 45.1015 s, 308 state frames/181 LiDAR frames, red endpoint observed/black not, minimum subject reference separation 29.5698 m, red damage increase 0/black 0.368478. Trial 2: 15.0590 s, 121/61 frames, both endpoint proximity conditions observed, separation 28.4645 m, damage 0/0.372699. Trial 3: 14.9510 s, 120/60 frames, both endpoint proximity conditions observed, separation 29.4206 m, damage 0/0.321626. Total: 302 red LiDAR frames with wheel-speed/IMU and separate simulator ground truth. These are endpoint proximity results, not verified route compliance or collision-free acceptance; verified contacts remain unavailable. Cleanup paused physics and disabled/braked both AIs. No Rust, cameras or background traffic were used.


## [2026-10-18] attempt | Red ETK speed increase for ETK/MD70 impact

The user requested higher red-car speed for an impact trial. Added red/black speed-cap and collision-delay flags to `scripts/run_saved_navgraph_trial.py` and ran the saved ETK/MD70 scene at red 60 km/h, black 25 km/h, 12.5 s truck lead-in. The first attempt had an unstable damage baseline; after adding a parked warm-up the next attempt began telemetry with the red about 180 m from its saved position, a large damage delta and 282 m car separation, so it does not prove a pair impact. Three additional pre-release guards found red drift exceeding 3 m and aborted before data collection, even after switching red AI to `stopping`. The runner does not establish a valid speed-limited impact yet. Static Python compile/help and `git diff --check` passed; the invalid/aborted records are preserved and must be excluded from ML training.


## [2026-10-18] training | Bounded offline arrival-model retraining

At the user's request, ran the existing offline grouped training pipeline with a nine-minute process timeout; it completed in about seven seconds. `runs/ml-arrival/pilot-20261018T023331Z-1b27bbac/` audited 61 Small Grid trial folders (50 accepted, zero exact telemetry duplicates). The entry model evaluated on 1,069 held-out rows across 16 trials/3 independent groups: MAE/p95 0.375/1.211 s overall, and 0.307/1.052 s on 941 common moving rows versus the distance/speed baseline's 4.343/18.967 s. The entry estimator is saved as `models/entry.joblib`. No new clearance model was fitted: only one clearance-bearing group landed in validation, so the report is `insufficient_data` and process exit code 2. The currently running West Coast LiDAR/JSONL collection is not consumed by this CSV-based trainer. No Rust/live inference integration occurred.


## [2026-10-18] check | Red car appears blocked in active traffic run

Checked live saved-route run `runs/sensor-crossing/navgraph-hour-d50474577c27/`. At the latest telemetry sample (frame 1067, 940.4 sim seconds), red remained near its saved start with speed below 0.3 km/h across recent samples. Background `clone2` was 1.8 m from the red car and `clone1` 11.4 m forward on its heading, suggesting a traffic blockage without proving causality. The run remains active; stalled-red samples are not route-progress evidence. No controls or simulator state were changed.


## [2026-10-18] follow-up | Red stall persists

A follow-up read of the active run reached frame 1193 at 1,052.8 simulated seconds. Red remained at its saved start position and below 0.3 km/h; the recorder was still running. This confirms the prolonged stall, while the exact mechanical/traffic cause remains unverified.


## [2026-10-18] intervention | Clear traffic from red start and continue collection

Following the user's instruction, called BeamNG `traffic.reset()` through a second BeamNGpy connection while the 30-minute recorder remained active. The API moved the six traffic participants away from the player; no vehicles were deleted and no scenario restart was needed. The intervention is recorded in the run metadata. Red resumed movement; legs 28 and 29 reported both endpoints observed, with maximum red speeds 59.51 and 59.22 km/h and recorded damage deltas 0.0349 and 0.0. At the latest summary read, `navgraph-hour-d50474577c27` remained active at 1,372.9/1,800 sim seconds with 1,557 paired state/LiDAR samples. Earlier stalled-red frames remain in the run and should be excluded from route-progress learning. This current LiDAR JSONL/NPZ format is not accepted by the existing Small Grid CSV trainer.


## [2026-10-18] complete | 30-minute West Coast LiDAR collection

The six-traffic run `runs/sensor-crossing/navgraph-hour-d50474577c27/` completed at 1,800.6 simulated seconds in 681.2 wall seconds (2.64x observed average). Final data: 2,047 paired state/LiDAR frames, 2,047 red and 2,047 black point-cloud files (4,094 clouds total), 2,047 ground-truth rows, and 44 legs. Leg results: 20 both-endpoints observed, 15 time-limited with an endpoint unreached, 8 damage-guard stops, and one completion leg. Folder size is 4,454,620,388 bytes (~4.15 GiB), including 2.12 GB red LiDAR and 2.24 GB black LiDAR. The user-requested traffic reset is in metadata; pre-reset stalled-red data and post-reset intervention-conditioned data must remain distinguishable. This West Coast JSONL/NPZ data has not been trained by the existing Small Grid CSV trainer.


## [2026-10-18] fix | Saved-route participant ID preflight

The user's three-trial command failed before collecting frames with `KeyError('clone0')` because that saved ID was absent from the live BeamNG vehicle map. Updated `scripts/run_saved_navgraph_trial.py` to resolve saved red/black roles, allow live-ID overrides via `--red-id` and `--black-id`, report loaded IDs when a participant is missing, and store the selected IDs in metadata. Four offline tests passed for defaults, overrides, missing-participant diagnostics and duplicate IDs; Python compilation, CLI help and whitespace checks passed. No BeamNG behavioral retest was run, so rerun only after loading both saved participants or supplying their live IDs.


## [2026-10-18] trial | Three saved-route runs after participant reload

The user asked to run the saved West Coast scenario after a three-trial attempt had failed because `clone0` was absent. BeamNG's scenario catalog contained the installed `west_coast_red_black_20261018` scenario. Loading it timed out waiting for the API `MapLoaded` acknowledgement, but a fresh read confirmed both expected cars were present at their saved positions, so the requested three-trial native-AI batch proceeded with zero background traffic. Batch `runs/sensor-crossing/navgraph-batch-6b833c216195/` finished: state/LiDAR frames 130/65, 152/64 and 125/63; both cars met endpoint-proximity checks in all trials. Minimum sampled center-reference separations were 14.21, 31.95 and 30.15 m. Red damage deltas were 0; black deltas were 0.642, 0.644 and 0.676. Verified contact data remains unavailable, so collision-free behavior is not established. Data totals 201,238,938 bytes under ignored `runs/`; no traffic, cameras, Rust or LiDAR-driven controller was used. The scenario was left paused by runner cleanup.


## [2026-10-18] trial | Saved routes with four traffic vehicles

The user requested repeating the saved West Coast route trial with background traffic. Ran `scripts/run_saved_navgraph_trial.py --trials 3 --traffic 4` using traffic IDs `clone`, `clone1`, `clone2`, and `clone3`. Batch `runs/sensor-crossing/navgraph-batch-6e0faed50d53/` completed all three endpoint-proximity checks, with 84/83, 82/81 and 74/74 state/LiDAR frames. Minimum subject center-reference separations were 33.98, 34.37 and 31.91 m; nearest sampled traffic-to-subject center separations were 8.41, 8.24 and 60.02 m. Red damage deltas were 0; black deltas were 0.635, 0.675 and 0.638. Verified contacts are unavailable. The run collected 252,855,432 bytes (~241 MiB) under ignored `runs/`; it used native waypoint AI and red LiDAR capture, without cameras, Rust or LiDAR-derived decisions. After recording, the four traffic cars were re-enabled and left moving for the user's submission video.
