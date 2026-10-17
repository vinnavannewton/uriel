---
title: "Running and deployment"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Running and deployment

## Deployment target update

S5 reports user-confirmed **Ubuntu 24.04 / IBM LinuxONE / s390x**; Fedora 44 KDE/x86_64 remains development context. Actual SSH access, allocation, installed packages and deployment are unverified. This supersedes earlier target-unknown wording; it does not prove the remote service exists.

Plan native locked release builds on the target during the permitted event window and validate Python native packages in the supplied s390x environment. Transfer source, JSON/CSV and configuration, not Fedora executables, `target/`, Python virtual environments or undocumented native memory dumps. Model transfer needs compatible versions and numerical verification. The proposed Python inference worker runs on the same LinuxONE instance; laptop inference merely displayed remotely is not platform inference.

S5's account/lab steps and build/test commands are preparation guidance, not instructions executed during this wiki update. Source: [[sources]] S5 sections 14–15. Related: [[ml-arrival-prediction]], [[event-preparation]].

Run from the IBM workspace:

```sh
cargo run
```

Open [local dashboard](http://127.0.0.1:3000). Builds require a suitable Rust toolchain and Cargo dependencies. The lockfile exists. Reported performance must eventually use a release build on the actual destination; no performance result is established now.

| Variable | Default |
|---|---|
| `ARC_BIND` | `127.0.0.1:3000` |
| `ARC_SCENARIO` | `scenarios/crossing-v1.json` |
| `ARC_RUN_DIR` | `runs` |
| `ARC_TOKEN` | Unset; optional bridge token |
| `RUST_LOG` | `arc_angel=info` |

The Rust process can run headlessly. A browser on an operator laptop displays its dashboard. No GTK/Qt desktop is required on the remote machine.

Earlier planning left the target unknown; S5 now specifies Ubuntu 24.04/s390x. Access and permitted ports remain unknown. An x86 Fedora executable cannot substitute for the target build.

The implementation has no TLS termination or supervisor unit. HTTP observation endpoints are unauthenticated; optional token validation protects only the bridge upgrade. Keep the localhost default until the remote access method is explicitly configured. Remote deployment needs authenticated access and encrypted transport or an agreed secure tunnel.

The previous local server launch was previously reported. Current process availability was not checked during wiki creation.

## Sources

- [[sources]]: S1 PRD section 11, S2 decisions, S3 current code; [README](../../../../README.md).
- Related: [[protocol]], [[recording]], [[open-questions]].
