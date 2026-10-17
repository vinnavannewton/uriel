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
