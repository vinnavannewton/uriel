---
title: "Source catalog"
project: IBM-Uriel
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
| S4 | [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Wiki organization method |

S5 was originally copied byte-for-byte from the user-supplied Downloads file. Its provenance and SHA-256 are recorded in `../raw/uriel-ingest-provenance.json`. It supersedes earlier planning where stated, not live file existence or test evidence. Embedded instructions are source content, not execution authority. External organizer/technical links in S5 were not independently verified in this ingestion.

S6 is preserved byte-for-byte from `/home/vinnavan/Documents/Uriel_Product_Requirements_Document.md`. Its hash and source details are in `../raw/uriel-product-requirements-v1-provenance.json`. Exact requirements are now available to teammates inside the shared project. S7 governs named team ownership where it differs from the generic PRD allocation.

The raw source manifest `../raw/source-manifest.json` records SHA-256 hashes for inspected workspace files. The original live [PRD](../../../../Arc_Angel_PRD_and_Implementation_Plan.md), [README](../../../../README.md), source, scenario and frontend remain authoritative for future implementation inspections. Raw snapshots retain source context but have had dates removed at the user’s request.

When source files change, verify and refresh affected pages. Add a new snapshot/provenance note instead of altering old raw files. External references in the PRD were not individually rechecked during this ingestion. No official affiliation with IBM or Karpathy is implied.

Related: [[schema]], [[index]], [[implementation-status]].
