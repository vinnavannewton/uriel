# IBM / Uriel project instructions

## Project context

At the start of work, read `AI-Wiki/Projects/IBM/wiki/index.md`, then relevant topic pages and `implementation-status.md`. Follow `AI-Wiki/Projects/IBM/wiki/schema.md` for wiki maintenance. Verify facts against current source before relying on an old implementation snapshot.

## Durable documentation

After meaningful code changes, investigations, decisions or verification results, update the relevant wiki pages, refresh the index if navigation changes, and append the chronological log. Keep PRD requirements, current implementation, static concerns and actual validation results distinct. Preserve `raw/` snapshots; create new dated sources when needed. Do not store secrets or bulk telemetry in the vault.

## Shared team skill

Use the repo-local `uriel` skill at `.agents/skills/uriel/SKILL.md` for Uriel work. Read `AI-Wiki/Projects/IBM/wiki/team-workflow.md` for current ownership and teammate usage, and `latest-prd-context.md` for newer requirements/source availability. Keep the wiki current after meaningful work as described above.

## Current user constraints

Development is local first. Current Uriel requirements and reported LinuxONE target/resources are summarized in `AI-Wiki/Projects/IBM/wiki/latest-prd-context.md`; check actual access before relying on deployment readiness. The desired product includes the server, BeamNG/ML integration and dashboard. West Coast USA is intended, but car model, routes and controller limits are uncalibrated. The user deferred behavioural testing to hackathon day; do not run these tests without subsequent authorization. Compilation and syntax checks were previously accepted. No native GUI migration, deployment, commit or push has been requested.

Wiki maintenance does not authorize unrelated implementation changes. Follow the user's current request when it changes these constraints.
