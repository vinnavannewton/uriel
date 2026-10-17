# Uriel - Complete Project Context and Handoff

**Purpose:** Self-contained context for teammates, a fresh ChatGPT/Codex conversation, and event preparation.  
**Status:** Planning and submission preparation. A working Uriel codebase, trained model, successful deployment or benchmark has not been demonstrated in this conversation.

## 1. Read this first

- The current project name is **Uriel**. Earlier names were Arc Angel/ArcAngel and Sentinel/SentinelDrive. Do not use those names for the current submission.
- The selected IBM Z Datathon track is **Real-Time AI for Critical Decisions**.
- The core idea is a shared server coordinating connected vehicles approaching an intersection. BeamNG.tech provides the physical simulation and built-in driving AI.
- The selected backend is **Rust + Axum + Tokio**, with Serde/serde_json and tracing.
- Final deployment is planned for **Ubuntu 24.04 on IBM LinuxONE, architecture s390x**. Development machines run Fedora 44 KDE on x86_64.
- Python + BeamNGpy bridges remain on the simulation laptops. BeamNG itself does not move to LinuxONE.
- The user initially wanted no training, but later explicitly changed their mind and accepted training. The proposed first ML task is **predicting arrival time at a conflict-zone entry**. The model family is not yet locked.
- Model inference should run on LinuxONE and feed the Rust coordination decisions. A small Python inference worker on the same instance is the recommended integration approach.
- The first working scenario uses **positions, velocities and intended routes**. This was a user scope choice, not a verified organizer requirement.
- Cameras, LiDAR, unknown-car detection, potholes and rerouting were explored; they are later extensions, not first-version commitments.
- Separate laptops run separate BeamNG worlds. They can share a backend for aggregate load testing but do not automatically share one physical intersection.
- **Correction to earlier planning:** the organizer guidebook prohibits prebuilt continuation projects. Plan/research/setup and required labs beforehand; write Uriel project code in the official event window. An earlier user understanding that working prototypes were allowed was contradicted by the subsequently read guidebook.
- Two organizer AI/ML labs are described as mandatory. The exact assigned notebooks and whether completion is per person or per team remain unconfirmed.
- Do not keep reopening the Rust-versus-Python-versus-C++ debate. The stack decision is made; focus on a small complete implementation and measured results.

## 2. User, team and current preparation

The project lead is Vinnavan Newton E., a CSE AIML student at Global Academy of Technology, Bengaluru, with open-source and Linux experience. Communication should be direct and factual. Avoid exaggerated novelty, success guarantees and generic motivation.

Team: **four people, two experienced and two beginners**. At least one experienced member can build and debug Rust applications. Earlier references to four teammates should not override this later explicit team size.

All four have reportedly installed BeamNG.tech and BeamNGpy on Fedora 44 KDE. Python integration libraries are set up. This establishes installation, not a completed driving/control prototype.

The lead's laptop is a Lenovo Legion with Ryzen 7 7840HS, RTX 4060 Mobile 8 GB VRAM and 16 GB RAM. Available resources on the other laptops are unconfirmed. Do not assume 25 physically simulated cars per laptop will run in real time.

The user has Codex access and wants to use it heavily. Coding assistance may accelerate work, but does not establish correctness, remove integration work or change the event's development-time rules. Any event policy specific to AI coding assistants still needs checking.

## 3. Event facts and compliance

The event is global, with an in-person hub at the user's college; it is not simply an India-only competition. Prize amounts for a specific hub should not be inferred from the global prize pool.

Key organizer requirements reviewed in the Participant Guidebook:

- Event schedule omitted; teams of 4-6 students.
- Abstract deadline omitted for now.
- Build original project code during the event; research, datasets, abstract and architecture preparation are allowed beforehand.
- Complete the two assigned AI/ML prerequisite labs and attend mandatory LinuxONE readiness preparation.
- Final submission includes a video of no more than three minutes, code/repository, resource attribution and a title containing the team name. Show the LinuxONE instance and model.
- Four judging categories receive up to 10 points each: community/theme, originality, technical LinuxONE/AI usage, execution/presentation.
- Direct LinuxONE Community Cloud use is required by Technical FAQ Q16-18. Stack choice is flexible; training can occur elsewhere, per Q21.

**Unresolved organizer details:** exact lab pair; per-person versus team completion; evidence/verification mechanism; precise development start/end times for the hub; AI-assistant policy; acceptance of a simulation-only primary dataset; and final judging instructions.

The guidebook contains inconsistent date references. Use the latest dashboard and official hub announcements for scheduling. In particular, readiness preparation in the main text, while an APAC table contains a conflicting date. Do not silently resolve this by guessing.

### How the two labs relate to Uriel

They are learning prerequisites, not two extra application features. The categories cover predictive/multi-model AI and predictive plus generative AI. The linked learning repository has several notebooks, but it does not establish which exact pair the organizer counts. Completing a generative-AI lab does not by itself require Uriel to contain an LLM.

Until clarified, do not claim that one person's completion covers the team or that any arbitrary two notebooks satisfy the requirement. Save completed notebook outputs and follow the organizer's verification process when provided.

## 4. What Uriel does

### Problem

Vehicles approaching an unsignalized intersection may have conflicting routes and limited shared awareness. Independent decisions can produce abrupt slowing, unnecessary waiting and unsafe overlap. A central planner also needs to handle stale telemetry and uncertain vehicle response.

### Proposed solution

Each connected simulated car reports its observed movement and intended route through a Python bridge. The LinuxONE service predicts when vehicles will occupy shared conflict zones, assigns a crossing sequence and recommends feasible speed caps. It updates plans using actual movement rather than assuming cars obey targets instantly.

A small learned arrival-time predictor supports the scheduler. Explicit geometry, physical feasibility, reservations and conservative margins remain responsible for constraining recommendations. A local vehicle controller handles actuation and rejects stale or invalid advice.

### Honest claims

Cooperative intersection management is established research. Do not claim it was invented by this team. Uriel's contribution must be demonstrated in its actual implementation: integration of measured vehicle-response prediction, explicit scheduling, LinuxONE execution, fault handling and reproducible experiments.

This is a simulation prototype, not a certified autonomous-driving controller. No arbitrary-traffic collision guarantee, city-wide deployment or measured performance gain has been established.

## 5. Scope and priorities

| Priority | Deliverable |
|---|---|
| First vertical slice | Two cars, fixed routes, state exchange, server decision and observed speed response |
| Core coordination | One intersection, conflict zones, crossing order, conservative reservations and headway |
| Core ML | Generated arrival labels, a small predictor, held-out evaluation and inference on LinuxONE |
| Integration | Rust coordinator calls the ML worker; recommendations return to BeamNG |
| Fault behaviour | Advice expiry, stale-state rejection, reset/session handling and tested local fallback |
| Evidence | Paired baseline/coordinated trials plus separately labelled server-load tests |
| UI | Compact operator dashboard for decisions, telemetry and timing |
| Extension | Four cars first; four to six physical cars only if stable |
| Capacity exploration | 100+ aggregate telemetry vehicles, with clear world/source labels |

Keep raw camera perception, dense LiDAR processing, training large neural networks, custom Indian maps and head-on evasive steering out of the initial implementation.

## 6. Architecture and technology

| Location | Component | Responsibility |
|---|---|---|
| Fedora laptop | BeamNG.tech | Physical vehicles, road environment and built-in driving AI |
| Fedora laptop | Python + BeamNGpy bridge | Poll state batches, send telemetry, validate/apply advice and report overrides |
| LinuxONE | Rust + Axum + Tokio | WebSockets, world/session state, conflict checking, reservations and scheduling |
| LinuxONE | Python ML worker | Load a small model and return live arrival predictions |
| LinuxONE or approved training host | Python training notebook/script | Fit and evaluate the arrival model |
| Browser | Dashboard | Inspect vehicles, crossing decisions, prediction errors and timing |

Rust support libraries: Serde/serde_json for structured messages; tracing for logs; optional additional crates only when needed. No database, Kubernetes, Kafka or large infrastructure layer is required for the first version.

### Why a separate Python ML worker

The organizer-linked s390x environment documents familiar ML packages. A local API between Rust and Python avoids custom Rust model bindings and unverified inference-runtime integration during a short event. Both services still run on LinuxONE, so the model and coordination logic genuinely use the platform.

The exact worker framework and model persistence format are not locked. Keep the interface small: batch features in, predictions/status/model version out. Add bounded timeouts. Invalid or unavailable predictions must not block the network loop indefinitely.

### Computation and ownership

One authoritative coordinator owns each simulation world. Run at most one planning calculation in flight per world, with bounded concurrency across worlds. Coalesce complete pending frames to the latest state rather than processing a backlog of obsolete frames. Do not let a heavy calculation block Tokio network processing.

Start with a proposed 10 Hz planning rate; this is an experimental setting, not a demonstrated adequate rate. Keep actual simulation time separate from server wall time.

## 7. ML plan

### Proposed first task: arrival-time prediction

Predict remaining seconds from the current observed state until the vehicle reaches a defined conflict-zone entry boundary. This is more tightly connected to crossing reservations than adding unrelated image detection solely to obtain an AI label.

| Inputs available at prediction time | Meaning |
|---|---|
| Route-relative distance to entry | Remaining path distance |
| Measured current speed | Actual motion, not requested motion |
| Recent speed/acceleration history | Whether the vehicle is speeding up or slowing |
| Current and recent speed advice | Context for control response |
| Relevant route/vehicle characteristics | Differences in approach and vehicle behaviour |
| Label | Actual observed remaining time to entry |

A compact scikit-learn regressor, such as a random forest, is a proposed starting point. No final model family, hyperparameters, sample count or accuracy is confirmed.

### Data generation

During the allowed development period, run repeatable scenarios with varied starting gaps, approach speeds, vehicle responses and possibly vehicle models. Record coherent telemetry and actual boundary-entry events. Earlier frames can be paired retrospectively with their eventual entry time.

Do not use future measurements as input features. Handle stopped/non-arriving vehicles explicitly rather than inventing arrival labels. Many frames from one run are correlated; they do not establish diverse independent training examples.

### Evaluation

Split by complete runs or scenario variants, not adjacent frames. Keep test scenarios out of tuning. Compare:

1. Simple route distance / measured speed prediction, with explicit near-zero-speed handling.
2. A simple adaptive non-ML predictor if time permits.
3. The trained predictor under otherwise equivalent scheduling constraints.

Measure arrival-time mean absolute error and tail error, then evaluate downstream waiting, crossing completion and contact/proximity outcomes. If ML does not help, report that. Do not disguise unchanged or worse results as an improvement.

### Prediction is not a safety certificate

The model estimates timing; it does not directly command brakes or steering. Do not treat arbitrary model confidence or random-forest tree variance as a calibrated safety bound. Preserve conservative physical checks and occupied-zone protection. When predictions are invalid or outside tested conditions, use a defined degraded predictor/yield policy.

### Training location

The easiest compatibility path is generating CSV data on Fedora and training plus serving the small model in the same LinuxONE Python environment. Training elsewhere is permitted in principle; pin dependencies and verify transferred model outputs if doing so. Training time and data diversity within the event remain real feasibility risks.

## 8. Coordination algorithm outline

1. Load a versioned scenario configuration containing known route polylines, speed caps, yield/commit lines, exit boundaries and vehicle dimensions.
2. Precompute route conflicts using swept vehicle footprints and configured margins. Start with straight routes and inspect the geometry manually.
3. Validate a complete telemetry frame and project actual positions/velocities onto routes.
4. Identify approach headway constraints and relevant conflicting vehicles.
5. Estimate buffered entry/exit occupancy, informed by ML timing and conservative motion checks.
6. Preserve occupied and committed reservations until observed clearance.
7. Assign waiting vehicles feasible crossing intervals using a deterministic greedy order, such as first approach arrival with tie-breaking and aging.
8. Derive feasible speed caps; recommend yield/hold if an entry interval is unavailable.
9. Apply advice through the local bridge and observe actual movement.
10. Replan, log deviations and report overrides.

Do not search all permutations of crossing order. With n vehicles, distinct pairs are n(n-1)/2, but full scheduling costs may be higher. Partition by world/intersection and filter by proximity/routes before expensive prediction.

An initial stopping-distance check can consider v^2/(2a) + vL + margin, using measured conservative braking capability a and bounded delay L. This is an engineering approximation, not a safety proof. Calibrate it against the actual selected car and control mode.

If a car can no longer stop before the zone, do not casually reorder it as a waiting car. Preserve its likely occupancy and constrain other vehicles. Missing/stale vehicles cannot simply disappear from collision reasoning.

## 9. BeamNG driving and fallback

BeamNG built-in AI handles route following. BeamNGpy exposes waypoint, lane-driving, avoidance and speed controls. A speed command is a target/cap, not guaranteed precise actuation. Verify installed BeamNG.tech/BeamNGpy version compatibility before using API examples.

Previously discussed APIs include set_waypoint, drive_in_lane, set_avoid_cars and set_speed. The speed unit is metres/second. The limit mode represents an AI speed cap; it does not establish a guaranteed stopping controller.

First measure cruising, slowing and holding before a yield line. If low/zero caps do not hold reliably, reduce approach speeds/move yield lines or implement an explicitly tested AI-to-local-stop handover. Do not assume simultaneous manual braking and AI commands have compatible ownership.

Keep local car avoidance and other control settings identical in baseline and coordinated experiments. Avoid ScriptAI settings that force physically unrealistic tracking.

### Fault behaviour

- Reject old, expired, mismatched or out-of-range advice.
- Before commitment, use a tested local yield/stop policy when feasible.
- Inside or committed to the intersection, use a separately tested clearance policy; blindly stopping inside can introduce another hazard.
- A reconnect/reset invalidates old permissions and reservations until reconciled.
- Maintain conservative occupancy for a missing vehicle until a justified clearance or explicit reset condition.

These are behaviours to implement and test, not completed features.

## 10. Protocol and timing decisions

Use persistent WebSocket connections and JSON for the first version. The following is a design contract, not an implemented API schema.

| Field | Purpose |
|---|---|
| protocol_version | Reject incompatible message definitions |
| world_id | Isolate each physical simulation world |
| world_epoch | Change on reset/reload/trial restart |
| session_id | Distinguish reconnects/server restarts |
| frame_seq | Reject duplicate or out-of-order telemetry |
| sim_time_s | Express this world's simulation clock |
| scenario_config_id | Match route/zone definitions |
| vehicle_id / route_id | Identify vehicles and intentions |
| positions/velocities/dimensions | Inputs in documented units and coordinate conventions |
| based_on_frame_seq / plan_seq | Relate advice to state and reject obsolete plans |
| valid_until_sim_time_s | Bound the simulation-time validity of advice |
| applied/rejected acknowledgement | Distinguish advice issued from actual control application |

Messages: hello/hello_ack, complete state batches, recommendation batches, acknowledgements and explicit error/degraded status. Units: metres, seconds, metres/second, radians. Document whether XY is the map's horizontal plane. Do not assume GPS or geographic coordinates.

Use local monotonic clocks for wall-time freshness and round-trip measurements. Never subtract unrelated laptop/server clocks without synchronization. Simulation pauses must not keep old advice valid indefinitely. A provisional 0.5-second advice horizon was discussed; it is not approved until stopping/control tests justify it.

One bridge owns the coherent vehicle batch for each world. Bound payloads, vehicle counts, accepted rates and compute concurrency. Authenticate sessions; keep secrets out of repositories and logs. Use approved secure transport or an SSH tunnel for remote traffic.

## 11. Shared simulation and capacity testing

The user's ambition is hundreds of cars, potentially around 25 on each laptop. This is a capacity goal, not verified hardware capability.

**Four instances x 25 cars = 100 aggregate telemetry vehicles across four independent worlds.** It does not create one 100-car physically interacting intersection. Cars from separate worlds cannot physically collide or see each other through simulated sensors without additional synchronization infrastructure, which is outside scope.

Use three clearly labelled evidence categories:

1. Real BeamNG interaction trials with cars sharing one world.
2. Multiple independent BeamNG worlds served by the same backend.
3. Synthetic or recorded telemetry for server-load exploration.

Recorded replay that ignores returned advice measures transport/planning throughput, not closed-loop physical safety. Coherent synthetic trajectories are better than identical fake cars, but still must be labelled synthetic.

### Provisional performance goals

- Start at 10 Hz.
- Explore 100 aggregate telemetry vehicles across 10 worlds, then larger loads if stable.
- Earlier proposed goals were per-world compute p95 under 20 ms, server service p95 under 50 ms, and under 1% missed 100 ms service deadlines over five minutes.
- These numbers are proposed targets only; revise them based on actual resources, implementation and control requirements.
- Measure bridge round-trip time separately from server computation. Report p50/p95/p99, drops/coalescing, CPU/memory, world sizes and physics simulation-to-wall-time ratio.
- Multiple small worlds are not equivalent to the same number of vehicles competing within one intersection.

## 12. Dashboard

Build a compact operator dashboard, with the server remaining the main contribution.

Display:

- Top-down routes, vehicle positions/headings and conflict zones.
- Crossing order, reservations and reasons for proceed/yield/hold.
- Actual speed versus advised cap, advice age and local overrides.
- Predicted arrival versus actual arrival and model/version status.
- Connected worlds/vehicles, calculation time, round-trip latency and missed deadlines.
- Trial results: waiting, completed crossings, detected contacts/proximity and minimum separation.

Controls: scenario selection, baseline/coordinated mode, start/pause/reset, approach speeds/starting gaps between trials, and deliberate delay/disconnect injection. Treat requested, acknowledged and observed actions separately. Manual steering is not an initial priority.

The dashboard can be developed from agreed sample messages. Coordinate protocol edits with its owner. Do not spend the event creating an elaborate 3D frontend; BeamNG already supplies physical visuals.

## 13. Four-person work split and collaboration

| Role | Level | Ownership |
|---|---|---|
| A | Experienced, Rust-capable | Rust transport, world/session state, scheduler, compute bounds and server deployment |
| B | Experienced | BeamNG bridge/control, dataset collection, ML integration and physical feedback loop |
| C | Beginner | Dashboard, plots, decision display, logs and demonstration presentation |
| D | Beginner, reviewed | Repeatable scenario QA, load generator, result recording and fault-test checklist |

Roles A/B must coordinate tightly. ML work can bottleneck B; keep it small and have D assist with labelled run collection. C/D need fixed sample messages, bounded tasks and runnable instructions, not open-ended safety-algorithm ownership.

### Development versus integration

Each teammate can run an independent local server while developing during the allowed period. Use synthetic inputs when BeamNG is unnecessary. For joint LAN integration, designate one machine running the merged known-good backend and point the simulation bridges to its LAN address. Later LinuxONE assumes this shared-server role.

One shared repository, short task branches and reviewed merges into main. Keep main runnable, record the tested commit, and integrate after meaningful changes. Avoid everyone simultaneously changing the protocol or coordinator. Codex tasks should have the same module ownership and interface constraints.

Suggested repository areas: server/, bridge/, ml/, dashboard/, scenarios/, load/, tests/, docs/. These are proposed boundaries, not existing files.

## 14. Ubuntu 24.04 / s390x portability

The user confirmed Ubuntu 24 and s390x as the deployment target. No actual successful SSH session, resource allocation, installed package list or complete dependency audit was shown.

### Practical assessment

Portable Rust coordination logic should require a rebuild rather than a rewrite. Native ML dependencies, runtime packaging and model persistence are the larger compatibility risks. Rust's supported target is s390x-unknown-linux-gnu, with host tools.

During the event, transfer source and configuration through Git, install the pinned toolchain, and build/test on LinuxONE:

```bash
cargo build --release --locked
cargo test --locked
```

Commit Cargo.lock and record the Rust toolchain. Do not copy the Fedora target/ directory, laptop executable, Python virtual environment or x86 native libraries. A Docker image must also have a linux/s390x build; Docker does not erase architecture differences.

JSON/CSV transfer normally across architectures. s390x has different native byte ordering from x86; avoid sending memory dumps or undocumented native binary layouts. Test boundary conditions and numerical tolerances on the target.

Python source usually transfers, but compiled packages need s390x-compatible builds. Start from the supplied ML container, inspect installed versions and prefer a small CPU model. Do not assume CUDA-only research models or any arbitrary ONNX runtime package will work. A portable model format still requires an available compatible runtime.

For a small model, train and serve on the same LinuxONE Python environment to reduce compatibility issues. If transferring a persisted model, verify versions, feature ordering, preprocessing and numerical predictions on known inputs.

The laptop RTX GPU is not available to the remote server. Do not attribute Telum/Spyre acceleration to Uriel without verifying actual access and integration. LinuxONE is not universally faster than x86; benchmark the actual workload and allocation.

## 15. LinuxONE access and lab preparation

Use the event's instructions and latest mentor announcements. The official learning repository is linked in Section 20.

Preparation sequence:

1. Register on LinuxONE Community Cloud with event code SSF2026.
2. Activate the account and provision the event's Ubuntu instance.
3. Create/import an SSH key; keep its private half on the workstation.
4. Connect from Fedora, confirm architecture/resources and verify supplied tools.
5. Start the official s390x JupyterLab environment as instructed.
6. Open it through an approved connection method, such as an SSH tunnel.
7. Execute the exact assigned notebooks in order and fix failures before dependent cells.
8. Save notebooks with outputs and completion evidence according to organizer directions.

Examples listed in the repository include Churn_Scikit_PyTorch.ipynb, Fraud_LSTM_Keras_TF.ipynb, Digit_Class_TensorFlow.ipynb and Loan_Approval_Demo.ipynb. The loan example combines predictive/generative techniques. This listing is not proof of which pair satisfies the prerequisite.

Do not expose a public Jupyter instance using a published default token. Keep execution on the remote host distinguishable from a local notebook; platform.machine() in Python can verify s390x. Download finished notebooks as backups. No completed lab verification is recorded here.

## 16. Experimental acceptance and evidence

### Physical scenarios

- Two cars with separated arrivals.
- Two cars with near-simultaneous conflicting arrivals.
- Four approaches, if the two-car case is reliable.
- A car reacting slower than the predictor expects.
- Delayed/duplicate/out-of-order state and advice.
- Connection loss before commitment and during committed passage.
- Simulator pause, reset and reconnect.

Use a reasonable local stop-and-yield baseline with the same vehicles, routes, speeds and local avoidance. Do not manufacture benefit by disabling baseline avoidance or forcing unrealistic trajectory tracking.

Verify contact instrumentation with a controlled case. Damage changes alone do not detect every contact. Use available contact signals and geometric proximity/overlap, and label detector limitations. Zero detected contacts in a declared suite does not imply universal collision prevention.

Pair baseline/coordinated trials with the same initial conditions. Report actual results even when the baseline is already safe, ML adds no benefit or a target fails. Show how predictions influenced decisions, not just a screenshot of an unused model.

Save configuration, commit hash, model version, platform/resource details, timestamps and run IDs. Capture LinuxONE process/model execution and platform-feature evidence. A prediction computed on a laptop and merely displayed by LinuxONE is not LinuxONE inference.

## 17. Event-time plan

Earlier plans assumed prototypes could be built beforehand. That assumption is superseded. With custom data collection, training and deployment all in 24 hours, scope and integration discipline are critical.

Before the event: infrastructure readiness, required labs, research, dataset exploration, architecture, role allocation and submission preparation. Do not treat the planning documents as authorization to prebuild Uriel code.

Proposed event sequence, to adapt after the official schedule:

| Approximate hours | Objective |
|---|---|
| 0-3 | Small server/bridge vertical slice, first LinuxONE build and connection |
| 3-7 | Two-car deterministic coordination and reliable control/expiry |
| 7-11 | Parallel varied-run collection and compact ML training/evaluation |
| 11-15 | LinuxONE inference integration and actual-state feedback |
| 15-19 | Paired/fault trials, dashboard and modest load testing |
| 19-24 | Freeze scope, fix failures, capture evidence and prepare final video/submission |

If early gates fail, cut physical car count and interface complexity first. Do not defer the first remote build or ML integration until the final hours. No guarantee of completion or winning has been made.

## 18. Submission wording and existing artifacts

### Current selected track

Real-Time AI for Critical Decisions. Wildcard was considered, but its organizer description also expects AI/data innovation; it is not established as an exemption from AI requirements.

### Short proposed-solution field

The form enforces 200 characters despite its solution label saying less than 200 words. The latest accepted draft in this conversation is:

> Uriel will use AI and coordination algorithms on IBM LinuxONE to predict vehicle conflicts and recommend safer crossing speeds and order, tested in BeamNG.tech.

For a tiny summary, Rust and the word pretrained are unnecessary. Technical material must still honestly identify models, training and reused resources. Never imply the team invented an externally sourced model.

### Audience

Connected/autonomous-driving developers; traffic-management and smart-city evaluators; mobility researchers/safety engineers; connected-fleet operators; road users as potential long-term beneficiaries.

### Datasets - latest correction

Use generated BeamNG telemetry, road/scenario geometry, arrival labels, experimental outcomes and labelled synthetic/replay capacity streams. Camera/depth samples belong to a later perception extension unless the scope changes explicitly.

An earlier form draft ended by saying training a new model was not planned. **That sentence is now obsolete.** If the editable submission still contains it, update it to reflect planned arrival-time training and held-out evaluation. The exact submitted contents/status are not known.

A mandatory dataset field does not itself make training mandatory. The user's later training decision and the event's AI/ML evaluation expectations are separate considerations.

### Optional comments

Most useful unresolved questions now concern exact lab requirements, completion verification, runtime/network access and event-specific rules. Ubuntu/s390x has been confirmed by the user, so do not keep asking the architecture as though no information exists.

### Existing deliverables from this conversation

- Uriel_Solution_Proposal.pdf: three pages, approximately 52 KB, prepared for the optional attachment. It proposes arrival-time ML training, LinuxONE inference, coordination, datasets and evaluation. Creating this planning document is not a completed project implementation.
- Arc_Angel_PRD_and_Implementation_Plan.md: older detailed planning document. Its old name, pre-event prototype allowance and telemetry-only emphasis are superseded where they conflict with this handoff.
- SentinelDrive_Review-1.docx: an earlier independent review of a previous concept, not the authoritative current implementation plan.

Do not assume a file has been uploaded or a form submitted merely because a draft was created. Verify current contents before editing an existing artifact.

## 19. Extensions discussed, not initial commitments

| Extension | Potential implementation | Current status |
|---|---|---|
| Unconnected vehicle awareness | Pretrained camera detector, depth/calibration, tracking, then conflict reasoning | Later; generic detector is not a complete safety pipeline |
| Road blockage reports | Detect obstacle, establish actual route obstruction, share time/confidence and recompute routes | Later |
| Pothole map/severity | Sensor detection, geometry/vehicle response and corroborated reports | Later; requires real simulated defect geometry for physical impact |
| Arrival uncertainty / unreliable intention detection | Learned deviation prediction and conservative reservations | Possible refinement after basic arrival model |
| Direct V2V | Vehicle-to-vehicle communication | Not required; server-mediated sharing is sufficient initially |
| Head-on evasive steering | Coordinated local manoeuvres with feasible trajectories | Excluded from the first version |

Pretrained YOLO detection models were researched, as were research trajectory models such as MTR. Neither was selected for the current core. MTR's CUDA dependencies make it unsuitable as an assumed easy LinuxONE deployment. No LLM is needed for the chosen arrival-time predictor.

## 20. Primary references

Organizer materials were read during this conversation during the earlier review. Recheck them if they change; current organizer instructions outrank prior assumptions.

### Event and rules

- Participant Guidebook (also duplicated under the Xplore label in the user's resource list): https://docs.google.com/document/d/1tt0ZhUyirXDtHIEum3JhG-ZIj6y-YpUc5e15mPT78w4/edit
- Technical FAQ: https://docs.google.com/document/d/1O1SAvK4Box5FDAxaYg2cIeJ0qi7Q3bozWq32BIPYi50/edit

### Infrastructure and ML environment

- LinuxONE Community Cloud: https://linuxone.cloud.marist.edu/
- Official lab environment/setup: https://github.com/linuxone-community-cloud/jupyter-lab-ml
- Rust target support: https://doc.rust-lang.org/rustc/platform-support/s390x-unknown-linux-gnu.html
- Scikit-learn model persistence: https://scikit-learn.org/stable/model_persistence.html
- Axum: https://docs.rs/axum/latest/axum/
- Tokio CPU/blocking tasks: https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html

### Simulation

- BeamNGpy introduction/multi-client support: https://documentation.beamng.com/api/beamngpy/master/readme.html
- BeamNGpy API, including vehicle AI: https://documentation.beamng.com/api/beamngpy/master/beamngpy.html
- BeamNG.tech requirements: https://docs.beamng.com/beamng_tech/requirements/
- Sensors: https://documentation.beamng.com/beamng_tech/sensors/
- ScriptAI modes: https://docs.beamng.com/beamng_tech/tools/scriptaieditor/scriptai_modes/

### IBM learning/product references

- AI overview: https://www.ibm.com/products/z/artificial-intelligence
- Machine Learning for z/OS: https://www.ibm.com/products/machine-learning-for-zos
- IBM Z security: https://www.ibm.com/products/z/security
- Quantum-safe security: https://www.ibm.com/products/z/quantum-safe
- Actual IBM Z Xplore learning page: https://www.ibm.com/products/z/resources/zxplore

These product links are resources, not a mandate to use every product. z/OS is different from Ubuntu Linux. Platform security/accelerator features require actual access and configuration; their existence is not evidence that Uriel uses them.

## 21. Immediate next actions

1. Confirm LinuxONE account provisioning, Ubuntu 24.04/s390x access, allocated resources and SSH connectivity.
2. Obtain the exact mandatory lab pair, individual/team completion rule and verification instructions.
3. Complete required preparation and attend the readiness session at the officially confirmed time.
4. Confirm the final abstract contents, especially the change from no-training to planned training.
5. Assign named owners to roles A-D; freeze the small message contract and scenario design on paper.
6. Select the map/car and study the relevant AI-control APIs without prebuilding the Uriel submission.
7. Plan the CSV features, actual entry-time labels and held-out run split.
8. During the event, establish the first local/remote vertical slice before expanding scope.

## 22. Fresh-session handoff prompt

Read this document as the current authoritative conversational context for Uriel. Preserve the Rust/Axum/Tokio backend, Python BeamNG bridges, Ubuntu 24.04/s390x deployment, four-person team and proposed arrival-time ML worker on LinuxONE. Separate confirmed decisions from proposed details and unverified results. Respect the organizer's rule against continuation projects. Do not claim mandatory labs are completed, that code exists, that the model is trained, that 25 cars per laptop are feasible, or that any benchmark/safety result has been achieved. Continue from the actual current stage and ask only for information necessary for the next concrete task.
