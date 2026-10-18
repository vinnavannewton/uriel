# Updated red and black West Coast scenario

Saved from the live scene and Drive Path Editor on 2026-10-18. The red ETK (`thePlayer`) follows `junction1_wp25 → junction1_wp3`. The black midsize (`clone0`, editor label `bllck`) follows `tunnel_city_A_59 → DR323_3`. Exact transforms, paints, configurations and navgraph positions are in `manifest.json`; `drive-path-session.json` is a native editor export. The native scenario is also installed in the BeamNG user folder.

The four previously generated traffic cars were removed before the three-trial run. Both remaining cars use their saved native AI settings, including avoid-cars and lane driving. There is no Rust or camera; red LiDAR, wheel speed and IMU are recorded. The damage/proximity monitor uses simulator ground truth, not LiDAR decisions.

```bash
./.venv/bin/python scripts/run_saved_navgraph_trial.py --trials 3 --traffic 0
```

This is now the runner's default saved scene. `--scene` can select a different scenario folder. Start with only the two subject cars loaded when requesting a two-car-only trial. On scene reload, numeric editor links may require reassignment.

The first three trials are in `runs/sensor-crossing/navgraph-batch-fc0e932f6981/`. Trials 2 and 3 reached both endpoint proximity conditions; trial 1 reached only the red endpoint before timeout. Black damage readings increased slightly in all three; this does not establish collision-free acceptance.
