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
