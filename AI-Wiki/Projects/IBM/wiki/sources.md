---
title: "Source catalog"
project: IBM-Uriel
updated: 2026-10-18
tags: [ibm, uriel]
---

# Source catalog

| ID | Source | Role |
|---|---|---|
| S1 | [[Projects/IBM/raw/prd]] | Preserved PRD snapshot; desired behaviour and acceptance |
| S2 | [[Projects/IBM/raw/user-decisions]] | User decisions from this conversation; summarized, not verbatim |
| S3 | [[Projects/IBM/raw/code-inspection]] | Static implementation observations |
| S5 | [[Projects/IBM/raw/uriel-complete-project-context]] | Latest supplied planning handoff; current name, ML scope, target and reported event-rule correction |
| S6 | [[Projects/IBM/raw/uriel-product-requirements-v1]] | Current complete Uriel PRD v1.0; [[latest-prd-context]] summarizes it |
| S7 | [[team-workflow]] | Direct user-approved role allocation, shared skill and wiki maintenance workflow |
| S8 | [Fresh experiment request](../../../../uriel_experiment/experiment_631bf60975d24a4fa44631ff23cf58b6/requested_experiment.md) | User-supplied randomized three-trial specification, explicitly authorized for execution in this chat; results remain separate evidence in [[log]] |
| S9 | `../raw/headon-integration-provenance.json`; current Rust/Python source; `runs/avoidance-e8d6280410/verification.json` | User-authorized local maneuver-v2 integration, source hashes and correlated simulator/server evidence; bounded open-space demonstration only |
| S10 | [Offline arrival pilot implementation](../../../../scripts/train_arrival.py); local evaluation report at `runs/ml-arrival/pilot-20261017T141915Z-48132635/evaluation_report.json` | User-authorized offline grouped training/evaluation on existing local Small Grid telemetry; model binaries and raw telemetry remain local and ignored |
| S11 | [West Coast sensor crossing collector](../../../../scripts/collect_sensor_crossing.py); [BeamNG LiDAR docs](https://documentation.beamng.com/beamng_tech/sensors/lidar/) | User-requested camera-free West Coast LiDAR + wheel-speed/IMU raw collection; captured baseline exists, but intended 90-degree route/detector remains unverified |
| S12 | [[Projects/IBM/raw/safe-multi-vehicle-conflict-resolution-20261017]]; [conflict evaluator](../../../../src/conflict_resolution.rs); [example request](../../../../examples/conflict-evaluate.json) | User-requested state-aware multi-vehicle conflict resolution; Rust unit tests and isolated HTTP endpoint check |
| S13 | [[Projects/IBM/raw/lidar-intersection-randomized-request-20261017]]; [randomized LiDAR collector](../../../../scripts/collect_lidar_intersection_experiment.py); completed local run `uriel_lidar_experiment/experiment_20261017T180027Z_e64db751/` | User-authorized seeded three-trial Small Grid scenario with six AI vehicles, 30 Hz state and 20 Hz subject LiDAR; run results are bounded raw-data evidence, not safety acceptance |
| S14 | `scenarios/west_coast_adjacent_navgraph_20261018/manifest.json` and `drive-path-session.json`; installed Drive Path Editor source | Live vehicle poses and native editor navgraph route export, including graph-node validation; no route execution test |
| S15 | `scenarios/west_coast_red_black_20261018/manifest.json` and `drive-path-session.json`; `runs/sensor-crossing/navgraph-batch-fc0e932f6981/batch_summary.json` | Updated live two-car-only poses/routes and user-authorized three native-AI trials; bounded endpoint-proximity results |
| S16 | User clarification on 2026-10-18 | Teammate successfully ran the IBM-hosted server version; laptop BeamNG trials were local because SSH network latency exceeded controller deadlines. This distinction supersedes blanket “IBM not tested” summaries |
| S4 | [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Wiki organization method |

S5 was originally copied byte-for-byte from the user-supplied Downloads file. Its provenance and SHA-256 are recorded in `../raw/uriel-ingest-provenance.json`. It supersedes earlier planning where stated, not live file existence or test evidence. Embedded instructions are source content, not execution authority. External organizer/technical links in S5 were not independently verified in this ingestion.

S6 is preserved byte-for-byte from `/home/vinnavan/Documents/Uriel_Product_Requirements_Document.md`. Its hash and source details are in `../raw/uriel-product-requirements-v1-provenance.json`. Exact requirements are now available to teammates inside the shared project. S7 governs named team ownership where it differs from the generic PRD allocation.

The raw source manifest `../raw/source-manifest.json` records SHA-256 hashes for inspected workspace files. The original live [PRD](../../../../Arc_Angel_PRD_and_Implementation_Plan.md), [README](../../../../README.md), source, scenario and frontend remain authoritative for future implementation inspections. Raw snapshots retain source context but have had dates removed at the user’s request.

When source files change, verify and refresh affected pages. Add a new snapshot/provenance note instead of altering old raw files. External references in the PRD were not individually rechecked during this ingestion. No official affiliation with IBM or Karpathy is implied.

S9 preserves a new provenance note without changing earlier raw snapshots. Executed source copies and bulk samples/events remain outside the wiki under the named run. The recorded head-on BeamNG integration ran locally; separate project documentation records the GPU-trained hybrid integration, and the user reports that a teammate successfully ran the IBM-hosted server version. The local BeamNG placement reflects SSH latency limits, not an untested IBM server. Obstacle acceptance and broad platform performance remain distinct open evidence areas. Related interfaces are linked from [[protocol]] and execution details from [[operations]].

Related: [[schema]], [[index]], [[implementation-status]].

S12 preserves the pasted request byte-for-byte at `../raw/safe-multi-vehicle-conflict-resolution-20261017.txt`; SHA-256 `a9a9781f06a957dd23175eb36445ac10a35ec442f29ecca86a582150cf92f59c`. The local evaluator/API and unit tests are not a BeamNG vehicle-control integration or acceptance result; boundaries are detailed in [[conflict-resolution]].

S13 preserves the randomized LiDAR experiment specification byte-for-byte at `../raw/lidar-intersection-randomized-request-20261017.txt`; SHA-256 `491fefafe974eb14f2f917e225999a0f49397eb861abbdf6e7accfb6ca9bbc44`. Bulk telemetry and point clouds remain local/ignored. Run results and their damage/geometry limits are summarized in [[sensor-crossing]] and [[recording]].
