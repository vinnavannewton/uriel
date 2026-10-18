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

The browser polls `/api/status` and `/api/worlds` every 500 ms and fetches the selected scenario through `/api/scenarios/{id}`. There is no dashboard WebSocket. Live telemetry remains read-only; it does not actuate vehicles.

The dashboard also has a **Next-run preset** panel for controller mode, background traffic count/speed cap, two vehicle model names, subject speed cap and cross-trial randomization. It stores preferences in browser `localStorage` and can copy the versioned JSON preset. This is an operator note for manual setup: no current BeamNG collector imports the JSON, and saving it does not alter the live simulation or launch a trial. The panel therefore does not represent live AI/traffic controls. Current cache key is `operator-presets-v1`.

**Preview demo** renders explicitly labelled example cars and plans entirely in the frontend. Disable it for live server worlds. Data shown as example telemetry is not an experiment result. The “Activity” panel shows current recommendations, not a persisted event history.

The template is plain HTML/CSS/JavaScript so frontend teammates can replace the design. Fonts are requested from Google Fonts with local system fallbacks. Native GTK/Qt/Tauri alternatives were discussed but not adopted.

The head-on v2 view now draws the two server recommendation polylines over the straight approach lanes, highlights the red/blue cars, and shows maneuver phase, plan number and each car's path acknowledgement. Lateral position is expanded in the schematic so the dodge is visible; the label distinguishes that view from metre-based telemetry. Live positions, speeds, status and paths come from the backend snapshots; a disconnect remains labelled stale/disconnected.

The Preview demo button animates a clearly labelled synthetic two-car head-on pass through execute and complete. It is frontend-only example data, not a BeamNG run or server decision. The remote LinuxONE page was rebuilt and served after that earlier UI update; `/health` returned `ok`. No browser screenshot or visual inspection was available in that environment. A live remote-controller attempt did not pass the hello response timeout: the SSH path measured about 325 ms TCP round-trip while the controller enforces a 500 ms freshness lease with 100 ms reserved to pause. The run remained paused and supplied no live vehicle telemetry, so the preview must not be presented as that run.

The demo selector now keeps two clearly labelled synthetic previews: the existing head-on pass and a 90-degree crossing. In the crossing preview, the blue vehicle has an eased approach, a 2.5-second deceleration, a brief yield pause until red clears, then a gradual launch; its rear brake lamps blink during braking and while stopped. Both are frontend-only examples, not BeamNG runs or server decisions. Dashboard asset URLs are relative so the HTML can load its sibling CSS and JavaScript when opened directly from a local `file://` URL. The dashboard accent is `#c8b6ff`. The remote LinuxONE page must be rebuilt/restarted before these source changes appear there. Direct `file://` preview can render the two synthetic demos, but live API endpoints are unavailable there.

The dashboard does not yet display the deployed model's predicted arrivals or model status, and its operator controls remain manual. This UI limitation is separate from the implemented and LinuxONE-tested backend inference path.

The follow-up user-requested BeamNG trial used the separate local Rust release server at `127.0.0.1:3001`; the LinuxONE service stayed running. This pass completed with 127 samples, 129 server plans, both accepted paths and `complete` status. Open `http://127.0.0.1:3001` to inspect its final two-car positions and planned paths. After the runner disconnects the world is marked disconnected, while its last plan and measured final positions remain visible. This documents why the laptop's BeamNG trial used localhost; it does not contradict the teammate-reported successful IBM-hosted server run.

The user reported the map kept showing the previous world during the next pass. The frontend retained any selected world still present in the API list, even after that head-on world had disconnected. Selection now switches to the newest connected head-on world when the current head-on selection is absent or disconnected; the bundled script URL also carries a cache version so a page reload fetches the update. For the verification repeat `runs/avoidance-82ebb49eb5/`, the API advanced from frame 77 to 87 in one second while both vehicle positions changed and the selected world status was `connected`. This verifies changing API data and the selection rule; no screenshot-based visual inspection was available.

The next user-requested repeat completed on the local coordinator at `http://127.0.0.1:3001` in about 13 seconds. The run produced 129 live simulator samples and the API retained its final two-car positions after disconnect. The browser itself was not inspected in this run, so the live map's visual behavior remains for the user to confirm.

The head-on map now renders the open Grid Plane as a proportional XY grid with 10 m minor squares and coordinate labels, rather than stretching lateral coordinates into a lane-focused schematic. Matched vehicle icons interpolate over 500 ms between new telemetry frames and follow their measured heading; animation stops after telemetry stops advancing. The footer and map label identify the grid and read-only live positions. A rebuilt local Rust dashboard on port 3001 returned `/health` successfully and served the updated cache-versioned HTML/JavaScript. Browser screenshot QA was unavailable, and no simulator run was started for this display change.

The coordinator keeps current worlds in memory: restarting the local port-3001 process cleared the prior run from `/api/worlds`. Refresh the browser to load the new UI; a connected BeamNG run is required for live telemetry again. The Preview demo remains synthetic example data.

## Intentional collision observation

The collision runner now streams measured positions through a dedicated display-only HTTP endpoint. Its `collision-grid-observer-v1` world appears in the normal world APIs with `observation_only=true`, no recommendations, and actual measured car dimensions. The UI labels this collision baseline, uses a fixed proportional grid, auto-selects a new connected observation world when the prior selection is disconnected, and retains the final positions. Frame delivery stops being labelled live after 1.5 seconds without updates. No avoidance plan is requested or applied. The client defaults to the local port-3001 dashboard and can disable publishing with `--no-dashboard`. A synthetic two-car API roundtrip passed on a separate test server; browser automation was unavailable and a new live simulator run was not performed.

The initial collision display was blank despite two measured cars in the API: `mapView` returned early whenever `scenario.routes` was empty. Open Grid Plane intentionally has no routes. Removed that requirement so fixed bounds and vehicle coordinates can render the map. A JavaScript DOM regression reproduced zero markers before the fix and now checks two markers, finite positions, motion on new frames and retained final markers. Per the user’s clarification, head-on maps now show only two coloured dots over the grid, without car icons, visible names or route/plan overlays. Coordinate updates still come from measured telemetry.

The same display-only endpoint now accepts `mode=dodge` for the converted user runner. Both dots still follow measured coordinates; headings and labels say dodge rather than intentional collision. This mode flag does not request a Rust driving plan.

The user subsequently requested minimal car icons instead of dots. Current markers use compact red/blue top-down silhouettes with small wheels and a dark cabin, rotating with measured heading. Visible names and path overlays remain omitted; the same telemetry interpolation and final-position retention apply.

The car silhouettes now have an asymmetric tapered nose, a forward-shaped dark windshield, pale front headlights and red tail lights at the square rear. Local +X is the nose; the existing measured-heading rotation points it in the actual driving direction.

The display-only observer now also accepts the six fixed IDs from `scripts/fresh_experiment.py` in `mode=crossing`. The runner publishes every sampled vehicle pose, velocity, heading, dimensions and damage value while it records the trial. The dashboard shows the red/blue subjects and four cyan traffic cars on a fixed `[-75,110] m` grid, interpolating between measured frames; it does not call the coordinator or produce driving plans. The user-requested run `uriel_experiment/experiment_c040ffd3ca504ddbb96e2fc0a1f4dd21/fresh_001/` reached API frame 251 with six vehicles and retained their final positions after the trial. The map was API-verified; no browser screenshot was available.

The local paired Grid comparison now publishes both measured Vivace poses to `/api/collision/telemetry` as a two-car `mode=crossing` observer world. This feed is display-only; the baseline sends no coordinator request, while the hybrid's control messages still go only to its local Rust coordinator on port 3098. The dashboard auto-selects a connected crossing observer, identifies whether it contains two or six cars, and draws measured positions on the proportional grid. The top-down marker now has a conventional car body, front/rear windows, four wheels, headlights and brake lamps. The comparison runner accepts `--dashboard-url` (default `http://127.0.0.1:3000`). A local dashboard process was started on port 3000 and `/health` returned `ok`; no BeamNG telemetry was streamed because port 25252 was closed. The updated frontend and Rust source compiled, but no browser screenshot or live simulator pass was verified.

The head-on dodge runner also streams its measured red/blue car positions to the local dashboard. In the two runs `headon-dodge-ebd6b2c455` and `headon-dodge-ded15ce9e8`, `/api/worlds` retained the final observer frame after the cars paused; the second run was selected in the open dashboard. This is display-only telemetry and produces no driving recommendations.

The subsequent recording pair `headon-dodge-37187ff5b7` and `headon-dodge-095f404c6d` also streamed to the same dashboard; the last run's final frame remains available after pause.

## Sources

- [[sources]]: S2 user decisions, S3 source inspection.
- [HTML](../../../../web/index.html), [CSS](../../../../web/style.css), [JavaScript](../../../../web/app.js).
- Related: [[decisions]], [[operations]], [[recording]].
