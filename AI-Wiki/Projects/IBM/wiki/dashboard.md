---
title: "Browser dashboard"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Browser dashboard

## Planned Uriel dashboard beyond the template

S5 adds predicted-versus-observed arrival, model/version status, advice age/overrides, computation/RTT/deadlines and trial outcomes. Proposed controls include scenario/mode selection, trial start/pause/reset, starting conditions and fault injection, with requested/acknowledged/observed actions distinguished. These controls and ML/evaluation panels are not implemented by the existing read-only template below.

Existing HTML branding still says Arc Angel; wiki ingestion does not rename application files. A compact operator UI remains the scope; no native desktop migration is selected. Source: [[sources]] S5 section 12. Related: [[ml-arrival-prediction]], [[implementation-status]].

The Rust service embeds `web/index.html`, `web/style.css` and `web/app.js` at compile time. Rebuild/restart after changing frontend files to update the served copy.

Panels show world choice, vehicle count, plan/frame, uptime, a schematic route map, crossing order, session state, vehicle actual/advised speeds and latest recommendation activity. The map uses local scenario coordinates, not geographic tiles or a calibrated West Coast USA background.

The browser polls `/api/status` and `/api/worlds` every 500 ms and fetches the selected scenario through `/api/scenarios/{id}`. There is no dashboard WebSocket. The display is read-only; it does not actuate vehicles.

**Preview demo** renders explicitly labelled example cars and plans entirely in the frontend. Disable it for live server worlds. Data shown as example telemetry is not an experiment result. The “Activity” panel shows current recommendations, not a persisted event history.

The template is plain HTML/CSS/JavaScript so frontend teammates can replace the design. Fonts are requested from Google Fonts with local system fallbacks. Native GTK/Qt/Tauri alternatives were discussed but not adopted.

## Sources

- [[sources]]: S2 user decisions, S3 source inspection.
- [HTML](../../../../web/index.html), [CSS](../../../../web/style.css), [JavaScript](../../../../web/app.js).
- Related: [[decisions]], [[operations]], [[recording]].
