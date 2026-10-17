# Fresh randomized Small Grid pilots

Two matching ETK subjects and four background vehicles. Three independent seeded runs; 25 simulator seconds at measured average 30 Hz. No Uriel coordinator or ML training.

| Run | Seed | Red entry / clearance (s) | Blue entry / clearance (s) | Subject damage increase |
|---|---:|---|---|---|
| fresh_001 | 903101 | 6.967 / 8.367 | 9.334 / 10.900 | red 0.0, blue 6301.627197265625 |
| fresh_002 | 903102 | 7.800 / 9.533 | 7.067 / 8.300 | red 0.0, blue 0.0 |
| fresh_003 | 903103 | 6.600 / 10.734 | 6.934 / 9.367 | red 3346.7255859375, blue 7581.032470703125 |

Each run contains telemetry.csv, events.jsonl, metadata.json, geometry.json and validation_report.json. trial_summary.csv includes randomized settings.

Entry and clearance use sampled world spawn bounding boxes against a virtual 6x6m zone; deformation/contact geometry is uncalibrated. Damage can make labels ambiguous. Verified contact is unavailable, not zero.
Missing values: first-frame acceleration and all verified_contact fields. Orientations are radians; lengths metres; time seconds; speeds m/s; acceleration m/s². Relative distance is nearest vehicle reference-point distance, not body clearance; relative speed is radial separation rate.
AI mode records commanded state, not independently acknowledged internal AI state. Delayed vehicles are initially braked; stopped-before-entry may reflect that scheduled hold.
The original interval validator expected mathematically exact 1/30s. Observed 33.0/33.5ms steps represent 0.5ms physics quantization and average 30 Hz. Revision 2 checks quantization, phase, duration, counts, stable IDs, bbox labels and event evidence. Original validation reports preserved as validation_report_initial.json; telemetry/events unchanged.
Initial failed setup batch experiment_a972954ae237434f8d60ee1900441d55 is retained separately. The successful retry changed shift initialization to prevent backward roll. Seeds and exact executed source are archived; replay is not guaranteed bitwise deterministic.
