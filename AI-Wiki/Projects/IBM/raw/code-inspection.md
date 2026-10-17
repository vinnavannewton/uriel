# Static source inspection

Files inspected: README, Cargo.toml, Rust modules, scenario and frontend source. File hashes are preserved in `source-manifest.json`.

- Axum HTTP service plus a JSON WebSocket bridge; current dashboard polls HTTP.
- Worlds and reservations are in memory. Four global compute permits; one computation and one latest pending frame per world.
- Server loads one configured schematic scenario. A route has an explicit zone-center distance, yield distance and commit distance.
- Scheduler rebuilds reservations in first-seen/ID order. It does not first collect all occupied/committed vehicles before scheduling waiting vehicles. Static concern: an earlier waiting candidate can be scheduled before a later committed vehicle is discovered.
- Missing vehicles keep prior reservations, but those reservations have finite predicted exit times. Scheduling can move beyond those times without evidence of actual clearance. Missing cars without previous reservations have no occupancy record.
- Route deviation above four metres produces fallback; a thirty-second reservation is added only when the deviating car is considered committed.
- Stopping heuristic uses fixed 3 m/s² braking and 0.5 s response allowance; these are uncalibrated. Waiting arrival intervals, zone-pair footprint geometry and approach-age priority are simplified.
- Plans include a 0.5 simulation-second expiry, but completion checks only frame/session equality. No wall-age rejection exists before emitting a plan.
- Same-route headway caps are applied after reservations are calculated, without recalculating their timing.
- Logs use a bounded queue of 4096 values. Queue overflow warns and drops records. File failures log errors; status still says recording=jsonl. No log rotation or drain-on-shutdown guarantee is implemented.
- Only bridge upgrades have optional token protection. HTTP status/dashboard endpoints are unauthenticated. Bind defaults to localhost.
- No behavioural tests, physical trials or load measurements were executed during this wiki creation. Concerns above are static observations, not reproduced failure results.
