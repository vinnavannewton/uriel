# Uriel

A cooperative vehicle-safety prototype built for IBM Z Datathon 2026.

Uriel connects simulated vehicles to a shared server that predicts potential conflicts and coordinates speed or trajectory adjustments. It combines Rust-based algorithms with machine-learning models trained on BeamNG.tech simulation data.

## Architecture

- **BeamNG.tech + BeamNGpy:** Vehicle simulation, sensors, telemetry and control on Fedora laptops.
- **Rust backend:** Shared vehicle tracking, conflict prediction and coordination.
- **Python ML:** Data preparation, training, evaluation and server-side inference.
- **Web dashboard:** Vehicle states, predicted conflicts, interventions and results.
- **IBM LinuxONE:** Backend and ML inference deployed on Ubuntu 24.04, s390x.

## Planned Scenarios

- Intersection coordination, starting with two vehicles and increasing traffic.
- Head-on and rear-end collision threats.
- Unconnected vehicles tracked through LiDAR observations.
- Mixed vehicle sizes, including long-truck clearance.
- Driver/controller non-response and controlled stopping.
- Elevation-aware prediction for slopes and flyovers.
- Shared road-hazard reports and blockage-aware rerouting.
- Experimental airborne-vehicle trajectory prediction.

## Repository Structure

- `backend/` — Rust coordination server
- `bridge/` — BeamNG telemetry, sensors and control
- `ml/` — Training, evaluation and inference
- `dashboard/` — Web interface
- `scenarios/` — Scenario configurations and launchers
- `schemas/` — Shared message definitions
- `tests/` — Tests and small replay fixtures
- `deploy/` — LinuxONE deployment configuration
- `docs/` — Project documentation and results

## Development

Each teammate works on a separate branch and opens pull requests into `main`. Shared interfaces are coordinated across components. Integrated deployments use `main`.

Setup instructions will be added as the implementation stabilizes.

## Status

Under active development. Listed scenarios are planned capabilities; implemented features and measured results will be documented as testing progresses.

Uriel is a simulation prototype, not a validated system for controlling vehicles on public roads.
