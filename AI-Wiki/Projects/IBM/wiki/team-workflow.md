---
title: "Team ownership and using the Uriel skill"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Team ownership and using the Uriel skill

## Approved ownership

| Person | Ownership | Coordination |
|---|---|---|
| Vinnavan, lead | Architecture, main Rust server/coordinator, main BeamNG integration, final integration and shared deployment | Reviews shared contracts; controls shared service changes |
| Manikantan | ML worker/inference integration, dataset generation/label definitions, training and model evaluation; co-develops assigned server work and assists BeamNG | Agrees bridge capture with Vinnavan; uses Ananya's run execution; owns prediction schema/model releases |
| Ankita | Dashboard UI, live state/decision display and operator/report views | Works from agreed sample messages; control changes go through authoritative scenario owner |
| Ananya | Guided scenario execution, run evidence, repeatability checks and failure reports | Engineers provide verified step-by-step guides and diagnose reported defects |

This replaces unnamed role assignments in older planning. Dataset/model ownership is with Manikantan, not left as miscellaneous assistance. It does not require everyone to edit the same server files or run shared deployments concurrently.

## Shared skill

The repo-local entry is `.agents/skills/uriel/SKILL.md`, with UI metadata and a manual-scenario-guide reference. It points to maintained wiki pages instead of embedding the entire PRD. The full current PRD is bundled at `AI-Wiki/Projects/IBM/raw/uriel-product-requirements-v1.md`, linked through [[latest-prd-context]]. Automatic selection is allowed; explicitly invoke it with `$uriel` when useful.

To share, include `.agents/skills/uriel/`, `AGENTS.md` and `AI-Wiki/` in the project handoff/repository. Teammates open their project checkout in Codex and start a new chat. If the skill is not listed after discovery, restart Codex. Confirm with “List available skills; is uriel available?” Keep hidden `.agents/` files when copying. No global installation is necessary for repo-local usage.

Prompts:

```text
Use $uriel. I am Vinnavan. Work on the assigned server/bridge task and update the wiki with actual results.

Use $uriel. I am Manikantan. Define the arrival/clearance feature and label contract and the ML worker interface; coordinate changes with the bridge owner.

Use $uriel. I am Ankita. Work on the assigned dashboard task using the agreed API/sample data, then update the dashboard wiki page.

Use $uriel. I am Ananya. Give me the verified setup, numbered actions, expected results, evidence paths and reset instructions for scenario U-S01. Mark unavailable controls or measurements blocked.
```

The skill does not transfer conversation history, plugin connections, software installations or SSH credentials. Each teammate configures their own access. Use local paths relative to the checkout, never Vinnavan-specific absolute paths in the shared skill.

## Integration and testing

Agree message versions, units, producer/consumer fields and model features before parallel work. Keep changes in scoped branches when Git exists and integrate reviewed changes; skill creation does not initialize Git or publish anything. Keep one owner for shared deployment. Tests and simulator runs follow current user authorization; assigning Ananya as tester does not automatically launch tests now.

AI prepares runnable checklists and interprets saved evidence. Ananya performs simulator clicks and records outcomes. Use deterministic launch/log-collection tools where implemented; do not have agents repeatedly navigate the simulator unless asked. Separate PASS/FAIL/BLOCKED/INCONCLUSIVE; no verified outcome means no success claim.

After durable changes, the acting agent updates relevant wiki pages and status, refreshes navigation as needed and appends the log. Preserve raw sources and report actual verification limits. Topic implementation facts require current source inspection.

## Sources

- S7 in [[sources]]: user-approved named ownership and request to create/share this skill and maintain the wiki.
- Related: [[decisions]], [[implementation-status]], [[latest-prd-context]], [[schema]].
