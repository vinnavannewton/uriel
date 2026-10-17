# Preparing Ananya's scenario instructions

Create one runnable checklist per actual supported scenario. Use the latest PRD's U-S identifiers, but mark unimplemented cases blocked. Do not turn desired acceptance conditions into claims about existing controls.

## Guide contract

Include these fields in the guide:

1. **Identity:** scenario ID/title, purpose, guide revision and owner; code/model revision, manifest/seed and mode to record.
2. **Prerequisites:** required software/version, known map/vehicle configuration, dataset/model if needed, ready indicators, expected server/bridge and log destinations. Use configured host aliases and no passwords/tokens.
3. **Setup:** exact supplied commands and launch order, expected output, then observable UI labels/actions. Verify installed UI/API details before prescribing clicks; never guess button names or map coordinates.
4. **Execution:** numbered actions, one action per step, including where to observe and what to record. Use repeatable scenario launchers instead of manual placement when available. Separate requested commands, acknowledged application and achieved motion.
5. **Expected result:** scenario-specific observable behaviour and configured numerical thresholds. Include normal, negative and fault cases only when their setup/control path exists. Missing thresholds or instrumentation make a measurement blocked, not passed.
6. **Evidence:** run ID, manifest/seed/mode, code/model versions, telemetry/event paths, detector definition, measurements and failure timestamps. Screenshots/video supplement logs. Keep evaluation-only unknown-vehicle truth isolated from online planning input.
7. **Outcome:** PASS, FAIL, BLOCKED or INCONCLUSIVE, with exact unmet criteria. PASS requires every declared criterion and eventual resolution; indefinite holding is not success. No detector means no claim of zero contacts.
8. **Recovery:** stop/cancel/reset through the verified scenario owner, confirm a new run identity and no old advice/tracks/reservations; save evidence before resets that discard it.

## Evidence to capture by capability

- Crossing: both front entry and rear clearance, minimum body separation, waiting, achieved deceleration/jerk and no newly created conflict.
- ML comparison: same manifests for algorithm-only/hybrid, prediction versus observed times, model applicability/status and actual planner effect.
- Unknown traffic: declared perception mode, observation age/uncertainty, loss handling and no hidden telemetry leakage.
- Reliability: injected fault, last valid state/plan, local response, affected reservations and recovery identity.

Only request a supported family. A successful two-car case does not establish truck, elevation, LiDAR, evasive or airborne support.

## Failure report form

```text
Scenario / guide revision:
Run ID / seed / mode:
Code / model / simulator versions:
Setup completed through step:
Action and observed result:
Expected result / measurement threshold:
Outcome: FAIL | BLOCKED | INCONCLUSIVE
Evidence files and simulation timestamps:
Repetition count / recovery taken:
Assigned owner:
```

Keep execution with Ananya, log interpretation and fixes with the responsible engineer, and shared server changes with Vinnavan. Do not run deferred physical tests merely to author a checklist.
