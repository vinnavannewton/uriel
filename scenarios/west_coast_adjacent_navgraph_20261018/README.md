# West Coast adjacent-road scenario

The native scenario files preserve the two car placements/configurations. `manifest.json` records exact transforms and stable vehicle-name-to-route mappings.

`drive-path-session.json` is a native Drive Path Editor Save Session export captured from the live editor. It preserves both navigation graph node sequences, start/end nodes, vehicle links and AI settings. Load it using Drive Path Editor → Load Session while on West Coast USA. After respawning cars, relink the splines to `thePlayer` (red) and `clone0` (black), because BeamNG runtime numeric IDs can change.

This setup was saved without starting AI or running trials. Route execution remains untested.

## Collect multiple trials

From the project root:

```bash
./.venv/bin/python scripts/run_saved_navgraph_trial.py --trials 10 --traffic 4
```

Choose any positive trial count. Each trial resets both subject cars to the saved transforms and runs the saved AI routes for at most 45 simulation seconds. `--traffic 4` enables four background cars; omit it for no managed traffic. Existing background cars are reused and traffic reset between trials. Damage/proximity guards can end individual trials early; connection/setup errors stop the batch and preserve partial reports. The batch status `finished` means the requested attempts finished, not that routes or safety passed.

Outputs are stored in ignored `runs/sensor-crossing/navgraph-batch-<id>/trial-001/`, `trial-002/`, etc., with a `batch_summary.json`. The simulation pauses during cleanup. No Rust server or camera is used. These repeated configurations are not independent ML validation groups.
