# URIEL — Fresh Randomized 3-Trial BeamNG Experiment

## Objective
Create and execute three NEW AI-driven trials for the 90-degree crossing scenario on BeamNG.tech Small Grid. Use two matching ETK vehicles (red and blue), starting approximately 40 metres from the crossing on perpendicular routes. Randomize selected AI-driving parameters independently for each trial and record complete telemetry for future ML training.

## 1. Start Fresh Safely
- Inspect the existing scenario and recorder before making changes.
- Preserve all previous recordings.
- Create a new experiment ID and three new run IDs: `fresh_001`, `fresh_002`, `fresh_003`.
- Save new outputs in a separate directory.
- Reset the simulation before each trial.
- Verify both vehicle IDs, positions, orientations, routes and damage state after each reset.
- Do not assume that resetting the simulation restores every setting; verify the actual state.

## 2. Scenario Configuration
- Map: Small Grid.
- Subject vehicles: Two matching ETK cars, red and blue.
- Routes: Perpendicular paths crossing at approximately 90 degrees.
- Initial distance: Approximately 40 metres from the crossing for each vehicle.
- Control: BeamNG AI.
- Background traffic: Use the existing four background vehicles if they can be verified and configured correctly.
- Recorder: Target 30 Hz, using simulation-time-based sampling.
- Trial duration: Use a predefined maximum duration sufficient to observe arrivals, stops and clearances. End earlier only when the completion conditions are satisfied.

## 3. Randomization
Use a reproducible random-number generator with a recorded seed for each trial.

Randomize within documented, physically plausible and simulator-supported bounds:
- Initial speed of each subject vehicle.
- AI target speed.
- Start delay between the red and blue vehicles.
- Background traffic starting conditions.
- Background traffic target speeds.
- Background traffic route assignments, only when valid and non-conflicting with the intended experiment.

Keep vehicle models, vehicle dimensions, the intersection geometry, route definitions and recording schema fixed across the three trials.

Do not randomize vehicle positions or orientations without checking that the vehicles remain on the intended lanes and retain the correct perpendicular routes.

Do not force the vehicles to arrive simultaneously. Let the AI drive naturally and record the actual outcomes.

## 4. Three-Trial Strategy
- Trial 1: Generate and save a random baseline configuration.
- Trial 2: Generate a new independent configuration.
- Trial 3: Generate another new independent configuration.

Use different recorded seeds. Randomization must change only the selected parameters; log every value so each trial can be reproduced.

Three trials are pilot experiments, not sufficient evidence of model quality or collision-avoidance safety.

## 5. Telemetry Recording
Record every relevant vehicle at the target sampling rate.

Required fields:
- `run_id`, `frame_id`, `sim_time`, `vehicle_id`, `vehicle_role`
- `x`, `y`, `z`, `yaw`, `pitch`, `roll`
- Velocity components, speed and acceleration where available
- Throttle, brake, steering and gear where available
- AI mode, target speed, route ID and start delay
- Relative distance and relative speed where valid
- Damage state and verified contact events
- Lane and conflict-zone state where measurable

Record the configuration and random seed in `metadata.json`. Write event logs separately from periodic telemetry.

## 6. Event Detection
Derive labels from the recorded trajectories:
- Front-boundary conflict-zone entry.
- Rear-boundary conflict-zone clearance.
- Stop-line crossing.
- Stopped-before-entry.
- Non-arrival within the observation horizon.
- Route deviation.
- Verified contact.
- Completed crossing.

Do not generate an entry or clearance timestamp if the event was not observed. Preserve missing, censored and ambiguous outcomes explicitly.

## 7. Output Structure
Create:

`uriel_experiment/fresh_001/`
`uriel_experiment/fresh_002/`
`uriel_experiment/fresh_003/`

Each run should contain:
- `telemetry.csv`
- `events.jsonl`
- `metadata.json`
- `geometry.json`
- `validation_report.json`

Also generate a combined `trial_summary.csv` containing the seed, randomized parameters, arrival outcomes, clearance outcomes, contact evidence, sample count and data-quality status for each run.

## 8. Validation and Execution Rules
Before starting:
1. Verify that the simulator and recorder are operational.
2. Verify the two subject vehicles and their routes.
3. Verify the conflict-zone geometry or clearly mark it unverified.
4. Confirm that output directories cannot overwrite previous recordings.
5. Confirm that the randomization ranges are valid for the installed BeamNG version.

After each trial:
1. Check timestamps, sample counts and missing data.
2. Confirm that the vehicle IDs remained stable.
3. Check whether each vehicle arrived, stopped or failed to arrive.
4. Verify event labels against the recorded trajectories.
5. Save a run summary before starting the next trial.

If a trial fails, preserve its logs, mark it failed and report the reason. Do not silently replace it with a successful run.

## 9. Final Report
Summarize all three new trials, including randomized settings, actual vehicle behaviour, entry and clearance times, contact evidence, recording quality, missing fields and unresolved geometry issues.

Do not claim that URIEL controlled the vehicles safely. These are randomized BeamNG AI baseline recordings unless the URIEL controller is explicitly connected and its commands are verified.

Begin by inspecting the current implementation and identifying the exact changes required. Then execute the three fresh trials if the simulator is available and report the actual results. Do not fabricate completed runs or metrics.