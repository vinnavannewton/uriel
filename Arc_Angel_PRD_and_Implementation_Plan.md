# Arc Angel — PRD and Implementation Plan

Version: 0.1 · Status: implementation-ready draft, with environment and control calibration gates

## 1. Product decision

Arc Angel is a shared vehicle-coordination service that predicts conflicts between known vehicle routes and recommends feasible crossing speeds and crossing order. BeamNG.tech provides the vehicle physics and built-in driving AI. Rust runs both the coordination calculations and the server on Fedora during development, then on the provided Ubuntu/LinuxONE environment.

The first product is a simulation demonstrator for one unsignalized intersection. It is not a road-deployable autonomous-driving system or a guarantee of collision prevention in arbitrary traffic.

### Confirmed decisions

| Item | Decision |
|---|---|
| Project name | Arc Angel |
| Team | Four people: two experienced, two beginners |
| Event | 24 hours; working prototypes are allowed before the event |
| Rust experience | At least one experienced teammate can build and debug Rust applications |
| Server stack | Rust, Axum, Tokio, Serde/serde_json, tracing |
| Simulation bridge | Python and BeamNGpy on each simulation laptop |
| Simulation host OS | Fedora KDE; BeamNG.tech and Python libraries already installed |
| First input data | Vehicle positions, velocities, intended routes and timestamps |
| Initial local server host | Fedora directly |
| Final target | Organizer-provided Ubuntu/LinuxONE environment; actual details unconfirmed |
| Driving | BeamNG built-in AI, with tested route and speed-advice integration |
| Preparation | Build and validate a working prototype before the event |

### Open facts, not blockers for local implementation

Record the exact event problem statement and scoring rubric; Ubuntu version; `uname -m`; available vCPUs and memory; shell/build permissions; package-download access; allowed inbound ports; and access start time. Ubuntu alone does not identify the processor architecture. Actual LinuxONE commonly uses `s390x` [S5].

Map, waypoint IDs and car model are implementation choices. Choose them during the first integration session and record them in versioned scenario configuration.

## 2. Problem and users

Independent autonomous vehicles may approach a crossing with competing intentions. A shared coordinator can use their reported states and known routes to anticipate overlapping occupancy and recommend an orderly crossing sequence. The demonstrator investigates whether that coordination improves passage under explicitly tested conditions.

Primary users are the team operating simulation experiments and judges inspecting the resulting decisions, latency and outcomes. The long-term application is coordination across multiple road intersections; that is a motivation, not an implemented city-wide safety claim.

The project builds on established cooperative intersection-management concepts. Its hackathon contribution is the implemented Rust service, LinuxONE deployment, physically simulated feedback loop, multi-scenario load testing and reproducible evidence—not a claim that cooperative driving is a new invention.

## 3. Scope and milestones

| Priority | Deliverable |
|---|---|
| P0: first vertical slice | Two cars, fixed straight crossing routes, one world, one server and a working speed recommendation |
| P0: reliable demonstrator | Two to four cars; actual-state feedback; expiring advice; world isolation; coherent logs |
| P0: deployment | Coordination decisions computed on the provided server, with the bridge remaining on Fedora |
| P0: evidence | Paired baseline/coordinated runs plus separate latency/load measurements |
| P1: extension | Four to six physical cars if performance and controller behaviour permit |
| P1: capacity | Concurrent independent worlds and synthetic/recorded telemetry, increasing measured load |
| Later | Unknown-car perception, camera/LiDAR fusion, merges, emergency priority, curved routes, head-on evasive steering |

Raw cameras, LiDAR point clouds, ML training, custom Indian road maps, distributed shared BeamNG physics and comprehensive road safety are outside the first version.

### Two distinct test systems

**Interaction test:** cars share one running BeamNG simulation and can physically interact.

**Capacity test:** multiple independent BeamNG instances send data to the same backend. Each has a separate `world_id`. Four laptops with 25 cars each would be 100 aggregate telemetry vehicles across four worlds—not 100 interacting cars at one intersection.

BeamNGpy supports multiple clients connected to one simulation, but this does not partition that simulation's vehicle physics across laptops [S1]. Whether a laptop can simulate 25 cars in real time must be measured. Cameras and LiDAR increase simulation hardware requirements [S2].

## 4. Architecture

| Component | Responsibility |
|---|---|
| BeamNG.tech | Vehicle physics, road environment, AI route following and local avoidance |
| Python bridge | Poll coherent states; identify routes; send batches; validate advice; apply speed caps; execute local fallback |
| Axum transport | WebSocket sessions, message validation, health and status endpoints |
| Per-world coordinator | Own latest state and reservations; predict occupancy; assign crossing order; emit recommendations |
| Bounded compute worker | Run substantial calculations without blocking network processing |
| Metrics/logging | Decision history, rejected data, command acknowledgement, outcomes and timing |
| Simple dashboard | Inspect connection state, cars, crossing order, advice and measured latency |

Use one Rust application with modules for protocol, world state, prediction, scheduler, transport and metrics. The bridge communicates over a persistent WebSocket using JSON. Axum is designed to work with Tokio [S3].

Each world has one authoritative bridge owner and coordinator. Reject a second owner for an active world/session rather than merging incompatible clocks or vehicle lists. Different worlds can compute concurrently within a bounded worker limit; each individual world's updates remain ordered.

For the MVP, maintain current state and reservations in memory and write experiment logs to files. A restart invalidates sessions and recommendations. The bridge falls back and performs a fresh handshake; surviving reservations cannot be assumed.

Substantial CPU work runs outside the asynchronous networking tasks. Tokio's blocking worker facility requires an explicit concurrency bound for CPU-intensive work [S4]. Allow at most one calculation in flight per world. Coalesce newer telemetry instead of building a queue of old frames. Discard results that belong to an old session, reset or expired prediction horizon.

## 5. Functional requirements

| ID | Requirement | Observable acceptance condition |
|---|---|---|
| FR-01 | Register a world, session and versioned road configuration | Unknown versions/configurations are rejected explicitly |
| FR-02 | Receive complete vehicle-state batches | State from one frame is not mixed with another frame |
| FR-03 | Validate finite values, units, IDs, routes and bounds | Malformed, duplicate or impossible data is rejected and logged |
| FR-04 | Reject old/duplicate sequence numbers | Old frames never roll back world state |
| FR-05 | Isolate worlds and reset epochs | Overlapping coordinates in different worlds never create conflicts |
| FR-06 | Project vehicles onto known routes | Large route deviations produce a degraded result, not confident advice |
| FR-07 | Predict buffered conflict-zone occupancy | Predictions and reasons are available in logs |
| FR-08 | Produce deterministic crossing order | Identical inputs/configuration produce identical plans |
| FR-09 | Maintain reservations using actual progress | An occupied zone is not freed merely because its predicted exit passed |
| FR-10 | Return bounded speed caps with expiry | Bridge rejects stale, mismatched and out-of-range advice |
| FR-11 | Maintain approach headway | A following vehicle is not advised beyond its route/headway constraints |
| FR-12 | Handle stale telemetry and unavailable planning | No new crossing permission is issued from stale state |
| FR-13 | Support acknowledgement and override reporting | Server can distinguish advice from advice actually applied |
| FR-14 | Export health, latency and result summaries | Judges can see where decisions were computed and their measured timing |
| FR-15 | Reset cleanly between trials | No reservation, sequence or advice leaks into the next experiment |

## 6. Initial coordination algorithm

### Road model

Configure a small set of fixed routes with polylines in BeamNG's horizontal map coordinates, approach direction, speed cap, yield line, commitment line and exit boundary. Record the map's coordinate convention. Positions/velocities in the protocol use the horizontal `x/y` components; altitude is not needed for a single-level intersection.

For each route pair, precompute where swept vehicle footprints can overlap. Conflict zones must account for vehicle length and width plus a calibrated margin. Same-lane following requires a separate headway constraint.

Start with straight routes. For the first build, a route-pair conflict table and manually inspected zone configuration are acceptable; dynamic road reconstruction is unnecessary.

### Prediction

Project observed position and velocity onto the declared route. Compute distance to zone entry/exit and conservative arrival intervals over a short horizon. Treat stopped vehicles explicitly; do not divide by a near-zero speed. Constant-speed extrapolation is only an initial predictor, with buffers for measurement age, acceleration uncertainty and controller response.

Use vehicle dimensions, plausible acceleration/deceleration, route alignment and actual velocity. A configured AI target is not a measurement of the car's movement.

### Scheduling

1. Validate a coherent state snapshot and its freshness.
2. Retain occupied and committed reservations until actual clearance.
3. Group candidates by intersection, approach and relevant conflict zone.
4. Order waiting vehicles using recorded first arrival at the approach, with deterministic tie-breaking. Test whether waiting age prevents starvation.
5. Assign the earliest feasible buffered crossing interval that does not overlap incompatible reservations and respects headway.
6. Derive a feasible target speed cap for reaching that interval.
7. If no feasible interval exists, recommend yielding before the conflict zone.
8. Replan using observed movement and report prediction/command deviations.

Do not enumerate all permutations of vehicle order. A deterministic greedy reservation scheduler is the starting implementation. All-pairs checks have `n(n-1)/2` candidate pairs, but a naive scheduler's total cost can be much greater. Partitioning by world and intersection and filtering by proximity matter more than language choice alone.

### Feasibility and commitment

Validate slowing advice against stopping distance. An initial engineering check is `d_stop ≈ v²/(2a) + vL + margin`, where `a` is a conservative measured braking capability and `L` covers advice age and actuation delay. This approximation is not a safety proof and must be checked against the selected simulated car/controller.

A car that cannot stop before a conflict zone must not be treated as an ordinary waiting car. Preserve its near-term occupancy and constrain others. Once committed or physically inside, do not reorder it as though it can safely yield outside the zone.

When measured response disagrees with predictions, enlarge margins or reduce operating speeds and log the deviation. A collision or overlapping occupancy is a failed trial, not a successful plan merely because the server emitted a command.

## 7. BeamNG control and local fallback

The bridge sets fixed AI routes and applies bounded speed advice. BeamNGpy exposes AI waypoint, lane-driving, car-avoidance and speed controls [S1, S7]. `set_speed(..., mode="limit")` expresses a cap; actual speed still depends on the AI, road and vehicle dynamics.

Before integration, measure three control responses: normal cruise, controlled slowing, and a stop before the configured yield line. Verify how zero/low speed caps behave in the installed version. Never assume that setting a target immediately changes vehicle velocity.

If AI speed advice alone cannot produce a reliable hold, either lower the demonstration's approach speeds/move the yield line or implement a tested, explicit AI-to-local-stop handover. Do not send competing manual brake commands and AI commands without verifying ownership and behaviour.

Keep local avoidance settings identical in baseline and coordinated runs. Do not turn off local avoidance merely to manufacture a baseline collision. Avoid ScriptAI configurations that force physically unrealistic tracking; its modes have different realism implications [S8].

### Fallback policy

The local bridge/controller owns immediate actuation. It rejects expired advice, detects telemetry/connection problems and performs a tested local yield policy. Before commitment, this should bring the car to the yield line when physically feasible. For a vehicle already committed, define and test clearance behaviour; a blind stop in the crossing can create another hazard.

Stale or disappeared vehicles retain conservative occupancy until an explicit, justified clearance/reset condition. Do not delete them from collision reasoning solely because their connection disappeared.

Any reconnect or reset requires a new session and state reconciliation before new coordinated entry. These are simulated fault-handling requirements; they do not establish real-world safety certification.

## 8. Message contract — protocol version 1

### Identity, units and timing

| Field/convention | Meaning |
|---|---|
| `world_id` | Distinct physical simulation world |
| `world_epoch` | New value for every reset/reload; invalidates old frames/plans |
| `session_id` | Server-issued connection incarnation; changes on reconnect/restart |
| `frame_seq` | Strictly increasing state sequence within session and epoch |
| `vehicle_id` | Unique within the world |
| `route_id` | Versioned route declared in scenario configuration |
| Distances/dimensions | Metres |
| Velocities/speed caps | Metres per second |
| Simulation timestamps | Seconds from this world's simulator clock |
| Wall-clock durations | Local monotonic durations; never subtract unrelated host clocks |

### Handshake

Bridge sends `hello` with `protocol_version`, `world_id`, `world_epoch`, `scenario_config_id` and bridge identity. Server validates ownership/configuration and returns `hello_ack` with `session_id`, supported settings and status. Use an environment-supplied access token in the connection handshake; do not hard-code secrets or log them. Use authenticated encrypted transport or an approved secure tunnel for remote deployment.

### State batch example

```json
{
  "type": "state_batch",
  "protocol_version": 1,
  "world_id": "laptop-a-world",
  "world_epoch": "trial-003",
  "session_id": "server-issued-session",
  "frame_seq": 42,
  "sim_time_s": 12.4,
  "scenario_config_id": "crossing-v1",
  "vehicles": [
    {
      "vehicle_id": "car-1",
      "route_id": "west-east",
      "position_xy_m": [120.0, 80.0],
      "velocity_xy_mps": [8.0, 0.0],
      "heading_rad": 0.0,
      "length_m": 4.5,
      "width_m": 1.8
    }
  ]
}
```

Coordinates, dimensions and IDs above are illustrative, not calibrated map values. Batches cover all registered vehicles for that world's frame. An unexpectedly omitted car is marked missing and conservatively retained; explicit lifecycle messages/configuration changes handle legitimate removals.

### Recommendation example

```json
{
  "type": "recommendation_batch",
  "protocol_version": 1,
  "world_id": "laptop-a-world",
  "world_epoch": "trial-003",
  "session_id": "server-issued-session",
  "based_on_frame_seq": 42,
  "plan_seq": 18,
  "issued_sim_time_s": 12.4,
  "valid_until_sim_time_s": 12.9,
  "status": "coordinated",
  "recommendations": [
    {
      "vehicle_id": "car-1",
      "speed_cap_mps": 4.0,
      "action": "yield",
      "reason": "conflicting_reservation",
      "reservation_id": "reservation-18-car-1",
      "entry_window_sim_s": [15.0, 15.5]
    }
  ]
}
```

Allowed actions initially: `proceed`, `yield`, `hold`, `fallback`. They are semantic advice; the speed cap and tested local control determine actuation. An entry window is an estimate/assigned reservation window, not a promise of precise physical arrival. Top-level status: `coordinated`, `degraded`, `unavailable`. No feasible plan produces explicit degraded/fallback advice rather than silently reusing an old proceed command.

### Applied-result acknowledgement

Bridge reports `world_id`, epoch, session, `plan_seq`, `vehicle_id`, applied/rejected status, applied speed cap and rejection reason. Reasons include expired advice, wrong session, old plan, invalid bound, local hazard, or control failure.

### Freshness and queue rules

Start with a 10 Hz wall-time coordination target and a configurable 0.5 simulation-second advice horizon. Also require a wall-time freshness check; simulation pauses must not preserve old advice forever. Initial 0.5-second wall freshness thresholds are provisional and must pass controller/stopping-distance tests, otherwise tighten them or reduce speed.

The bridge records local monotonic send times per frame and uses echoed `based_on_frame_seq` to check response age. It rejects advice after simulation expiry, after its wall-age limit, from old sessions/epochs, or based on an excessively old state. The server separately uses its own monotonic receive time for telemetry freshness. No synchronized laptop/server wall clocks are assumed.

Store the latest complete pending frame per world. Bound payload size, registered vehicles, accepted update rate and in-flight computation. Expose rejection/coalescing counters. A slow simulation is not sped up by relabelling its telemetry as real time.

## 9. Performance and acceptance targets

These are proposed engineering targets to validate, not existing results or capacity guarantees. Timing must be measured in release builds on the actual allocated environment.

| Level | Target |
|---|---|
| First gate | Two-car loop works locally with correct route IDs, units and observed slowing |
| Physical MVP | Two to four cars in one world, without contact in the defined repeatable acceptance suite |
| Control rate | Start at 10 Hz; adapt based on measured timing and vehicle response |
| Initial server load | 100 aggregate telemetry vehicles across 10 independent worlds at 10 batches/world/second |
| Compute target | Per-world coordination p95 under 20 ms at the defined initial load |
| Service target | Receive-to-response-send p95 under 50 ms at the defined initial load |
| Deadline target | Under 1% missed 100 ms service deadlines during a five-minute initial-load run |
| Network measurement | Report bridge-observed round-trip p50/p95/p99 separately; remote RTT has no guaranteed target yet |
| Scale exploration | Test 250, 500 and 1,000 telemetry vehicles, reporting actual limits and world partitioning |
| Recovery | Expired advice rejected; reconnect/reset never reactivates an old plan |

A missed deadline includes rejected/unanswered eligible frames beyond the service deadline; report load shedding separately. Coalescing frames must not conceal overload. Report achieved simulation-to-wall-time ratio for physics runs.

Also run a single-world synthetic stress case with 100 candidates to explore scheduler complexity. It is a capacity/algorithm test, not evidence of 100 interacting BeamNG vehicles. A 1,000-vehicle result across 100 small worlds does not establish the same capacity for one 1,000-car intersection.

If targets fail, record the failure and reduce load or improve measured bottlenecks. No fabricated speedup, reliability or LinuxONE advantage is acceptable.

## 10. Evaluation design

### Physical acceptance suite

| Case | Purpose |
|---|---|
| Two vehicles with comfortably separated arrival | Verify unnecessary slowing is limited |
| Two vehicles with near-simultaneous conflicting arrival | Verify yielding/order and actual clearance |
| Four vehicles from opposing approaches | Verify waiting order, headway and reservation progress |
| One vehicle responding slower than predicted | Verify replanning and conservative occupancy |
| Server disconnect before commitment | Verify local yield/freshness handling |
| Server disconnect while a vehicle is committed | Verify the configured clearance policy |
| Delayed/duplicate/out-of-order messages | Verify rejection and bounded queue behaviour |
| Pause/reset/reconnect | Verify clock/epoch/session invalidation |

For the three normal-flow cases, use at least five predeclared initial-condition variants and pair each baseline run with a coordinated run using the same setup. Fault trials are separately reported. Expand repetitions if time permits.

### Baseline

Use the same vehicles, map, routes, approach speeds and local avoidance settings. Implement a reasonable local stop-and-yield/fixed-priority policy. In coordinated mode, the server may schedule earlier slowing/progression; in baseline mode, the tested local crossing policy governs. Avoid comparing against deliberately blind driving.

### Metrics

Record contacts using a verified BeamNG contact/collision signal where available, and validate that detector with a controlled test. Supplement it with vehicle damage changes and geometric overlap/proximity; damage alone is not a complete collision detector. If direct contact instrumentation is unavailable, label the metric accurately as detected overlap/damage events and disclose its limits.

Record intersection traversal time, waiting time, completed crossings, minimum separation, speed profiles, control overrides, expired plans, calculation time, server service time, round-trip time, deadline misses and CPU/memory usage. Define waiting consistently, e.g. time below a configured low-speed threshold inside the approach region. Report median and tail latency, not just an average.

Acceptance is zero detected contacts in the defined physical suite plus correct expiry/isolation behaviour. Report baseline comparisons honestly; improved flow is a hypothesis, not a result guaranteed in advance. Local avoidance preventing a crash does not by itself demonstrate server collision prevention—show the issued plan and resulting trajectories.

Capacity tests use coherent synthetic trajectories or explicitly labelled recorded replay. Replaying packets tests transport/calculation, not closed-loop physical safety. State whether the generator adapts to returned advice or ignores it.

## 11. Deployment and LinuxONE evidence

### Local development

Run BeamNG and its bridge on Fedora. Run the Rust server separately with localhost addressing. Maintain a configurable server URL, shared protocol types, versioned scenario data and a committed `Cargo.lock`. Use `cargo build --release` for reported performance; debug builds are for development.

### Ubuntu rehearsal

An optional minimal Ubuntu Server VM validates installation, configuration and networking while BeamNG remains on Fedora. It does not reproduce LinuxONE's architecture on an ordinary x86 laptop.

### Provided environment

1. Record OS/version, architecture, available CPU/memory and permissions.
2. Confirm connectivity using a health request and WebSocket exchange.
3. Build the same source for the destination. Native build on the target is the preferred first route if permitted; otherwise prepare a compatible cross-build.
4. Rust supports `s390x-unknown-linux-gnu` [S5], but every selected dependency/build feature still requires validation.
5. Configure tokens, URLs, scenario definitions and log destinations through configuration/environment.
6. Run the service under an available restart supervisor; use systemd if permitted. Do not assume root access.
7. Run physical bridge trials and defined load tests against that deployed instance.
8. Save logs, configuration, commit hash and machine allocation with results.

A Fedora-built x86 executable cannot simply be copied to s390x. Even same-architecture deployment needs compatible runtime libraries. Avoid introducing unnecessary native/GPU dependencies into the telemetry coordinator.

### Credible platform claim

LinuxONE hosts the actual shared coordination decisions across multiple independent intersection workloads. IBM describes LinuxONE in terms of scalable/reliable Linux workloads and consolidation [S6]. The demo must show workload execution and measured capacity; it must not claim that ordinary Rust code requires LinuxONE or that the allocated VM inherits every enterprise platform capability.

If the organizer provides only an ordinary Ubuntu VM, describe the deployment as Ubuntu and confirm how it relates to the event's LinuxONE requirement. Do not call a generic VM LinuxONE without evidence.

## 12. Four-person work allocation

Names are intentionally unassigned. Choose roles according to actual strengths; one experienced member owns integration decisions and protocol changes.

| Role | Person level | Owned work | First independently reviewable deliverable |
|---|---|---|---|
| A: Rust backend and algorithm | Experienced, Rust-capable | Protocol types, world ownership, predictor, scheduler, compute bounds, server build | Synthetic two-car input returns a deterministic bounded plan |
| B: BeamNG and integration | Experienced | Routes, coherent polling, control response calibration, advice application, fallback, remote connection | Two cars send states and obey a tested slowing instruction |
| C: Monitoring and experiment records | Beginner | Simple status display, run metadata, plots/tables from logs, demo recording | Display vehicle IDs, caps, order and latency from supplied sample messages |
| D: Scenario QA and deployment checklist | Beginner with experienced review | Configure repeatable cases, execute reset/fault trials, record results, assist load runner | Reproduce one case twice with complete run metadata |

Beginners should receive sample messages, fixed commands and bounded tasks. They should not independently redesign scheduling or deploy changes to the shared integration environment. Experienced members review safety-sensitive/control changes. All code—including Codex output—requires compilation and behaviour checks by its owner.

Use separate branches/worktrees for concurrent work. Freeze protocol version 1 early, keep sample messages in the repository and announce changes before integration. Codex availability helps implementation throughput but does not replace module ownership or test evidence.

## 13. Preparation and event schedule

### Before the event, because prototypes are allowed

1. Obtain rules and server details; check the event's actual submission requirements.
2. Select map/car/routes and measure AI slowing/holding behaviour.
3. Build the first local two-car round trip and basic reservation logic.
4. Implement expiry, world/session identity, logging and deterministic resets.
5. Verify the reasonable baseline and contact/proximity instrumentation.
6. Rehearse an Ubuntu install; test s390x build as soon as target access is available.
7. Prepare sample messages, a synthetic load generator and known-good demonstration configuration.

### Suggested 24-hour event allocation

| Hours | Objective and exit gate |
|---|---|
| 0–2 | Verify provided server and network; deploy the known-good build; freeze demonstration scope |
| 2–6 | Run the physical scenario against the deployed server; resolve environment/control issues |
| 6–10 | Harden four-car coordination, reservations, expiry and fault handling |
| 10–14 | Execute paired baseline/coordinated trials and initial-load tests |
| 14–18 | Improve the measured bottleneck; explore higher telemetry loads only after P0 passes |
| 18–21 | Freeze features; rerun failed cases; finalize reproducible results and backup recording |
| 21–24 | Prepare the demo and submission; verify from a clean start; reserve time for venue/network failure |

This schedule assumes useful pre-event preparation; it does not require waiting for the event to begin implementation. If target access is delayed, continue localhost/LAN integration without changing the backend architecture.

## 14. Verification and release gates

Meaningful algorithm tests cover buffered interval overlap, physically occupied reservations, near-zero speed, infeasible slowing, following headway, deterministic ties and waiting progress. Protocol/integration tests cover frame order, reset/session isolation, invalid numerical data, missing cars and stale results.

Run formatting/static checks and the relevant Rust tests. Verify the selected scenario configuration and JSON examples. Hardware-in-the-loop simulator checks, fault injection and load measurements are essential; a unit-test pass alone does not establish coordination behaviour.

Before a demonstration release, confirm: a clean startup; two-car and four-car normal cases; tested local fallback; measured server identity; saved run metadata; and an accurate statement of which scale came from BeamNG physics versus synthetic/replayed telemetry.

## 15. Risks and responses

| Risk | Response |
|---|---|
| AI ignores or slowly follows a cap | Measure response first; reduce speed; use conservative margins; gate control handover |
| Separate worlds are accidentally merged | Require world/session/config IDs and test coordinate overlap across worlds |
| Laptop cannot run 25 cars | Use fewer physical cars; increase explicitly labelled telemetry load separately |
| Slow state or calculation backlog | Latest-frame coalescing, bounded workers and explicit deadline/overload counters |
| Unconnected road user enters scenario | Exclude from MVP; do not claim protection without actual perception/prediction |
| Route prediction is wrong | Monitor alignment/deviation; degrade; preserve uncertain occupancy |
| Server/network unavailable | Expiring advice and tested local fallback; prepare a clearly labelled local backup |
| s390x build/package incompatibility | Validate early; keep dependency set small; rebuild for the actual target |
| Safety claim exceeds testing | Bound claims to declared scenarios and report failed trials |
| Scope grows because coding assistance is available | Freeze P0; accept additions only after physical/deployment gates pass |

## 16. Definition of done and demo narrative

The MVP is done when the Rust service computes coordination on the demonstrated host, the bridge applies and acknowledges advice, the declared physical suite passes, faults reject stale advice, and the team can reproduce both normal trials and separately labelled capacity tests from saved configuration.

Suggested demonstration: show the identical setup with the baseline; enable Arc Angel; inspect the crossing order and measured car response; identify the LinuxONE/Ubuntu process computing decisions; increase independent telemetry workloads while showing latency/deadlines; disconnect advice and show the tested local response. Use real observations, even if the baseline already avoids collision or the throughput ceiling is lower than hoped.

Suggested claim after validation: “Arc Angel runs a shared Rust coordination service on the provided LinuxONE environment. It predicts crossing conflicts from vehicle telemetry and recommends bounded speeds. We evaluated physical outcomes in BeamNG and measured service latency as independent workloads increased.” Replace LinuxONE with Ubuntu if that is all that is verified.

## 17. Primary implementation references

These sources support API/platform choices. They do not establish this project's performance. Exact map behaviour, vehicle control response and selected crate compatibility require testing. Documentation checked during planning; installed versions remain authoritative.

- [S1] BeamNGpy README: https://documentation.beamng.com/api/beamngpy/master/readme.html
- [S2] BeamNG.tech system requirements: https://docs.beamng.com/beamng_tech/requirements/
- [S3] Axum documentation: https://docs.rs/axum/latest/axum/
- [S4] Tokio CPU/blocking tasks: https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html
- [S5] Rust s390x Linux target: https://doc.rust-lang.org/rustc/platform-support/s390x-unknown-linux-gnu.html
- [S6] IBM LinuxONE consolidation/platform overview: https://www.ibm.com/support/z-content-solutions/journey-to-linuxone/
- [S7] BeamNGpy API reference, including AIApi: https://documentation.beamng.com/api/beamngpy/master/beamngpy.html
- [S8] ScriptAI modes and realism: https://docs.beamng.com/beamng_tech/tools/scriptaieditor/scriptai_modes/

## 18. Decisions to record during the first work session

- Exact organizer rules, server access date and architecture.
- Role A/B/C/D names and the integration owner.
- Map name, car model, route/yield/commit/exit configuration and registered dimensions.
- Installed BeamNG.tech/BeamNGpy versions and tested AI settings.
- Rust toolchain and committed dependency versions.
- Measured stopping behaviour, allowed speeds, freshness limits and occupancy margins.
- Baseline policy, contact instrumentation and named initial-condition variants.
- Confirmed remote connection method and demonstration load goals.

These details complete configuration and calibration. They do not require reopening the Rust/Axum/Tokio stack decision.
