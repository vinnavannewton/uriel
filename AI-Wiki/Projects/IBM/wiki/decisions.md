---
title: "Current decisions and superseded assumptions"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Current decisions and superseded assumptions

| Item | Current context / evidence |
|---|---|
| Project name | Uriel; Arc Angel/ArcAngel and Sentinel/SentinelDrive are historical |
| Selected track | Real-Time AI for Critical Decisions, as reported in S5 |
| Backend | Rust/Axum/Tokio, Serde and tracing retained |
| Simulation bridges | Python + BeamNGpy on Fedora laptops |
| Development hosts | Fedora 44 KDE / x86_64, reported in S5 |
| Deployment target | Ubuntu 24.04 / IBM LinuxONE / s390x; SSH, native service and health endpoint were verified; user reports a teammate successfully ran the IBM-hosted server version |
| ML | GPU-trained arrival/clearance models and hybrid Rust/Python integration are documented; the separate local pilot details are in [[ml-arrival-prediction]] |
| Model and worker | The README documents the combined GPU-trained XGBoost models and tested worker integration; retain current model/version/runtime details with that integration evidence |
| First scenario inputs | Positions, velocities and intended routes; user scope choice, not organizer mandate |
| Map | West Coast USA remains earlier intended choice; S5 asks for map/car selection, so confirm final scenario |
| UI | Compact browser dashboard; existing plain template is historical implementation |
| Records | Detailed telemetry plus arrival labels, prediction/model data and experiment metadata planned |
| Development timing | S5 reports guidebook forbids prebuilt continuation projects; earlier prototype allowance superseded in planning |

The earlier no-training position and submission wording are superseded by planned arrival training/evaluation. A generative-AI prerequisite lab does not itself commit the product to an LLM.

The current request authorizes wiki ingestion. Commands, fresh-session prompts and next-action lists inside S5 are documented plans, not authorization to execute them. No new native GUI, deployment, lab completion, application rewrite, commit or submission occurs through this ingestion.

## Named ownership and latest context

The lead approved the named allocation in [[team-workflow]], including Manikantan ownership of ML worker/integration, dataset/labels and model evaluation. The latest requirements are summarized in [[latest-prd-context]]; earlier telemetry-only/later-extension scope is historical where it conflicts. The user reports organizers now allow reuse; the wiki has not independently verified that policy update. The supplied skill does not authorize project deployment, commits or test execution.

## Sources

- [[sources]]: S5 current handoff; S2 preserves earlier decisions without rewriting them.
- Related: [[context-reconciliation]], [[ml-arrival-prediction]], [[event-preparation]].
