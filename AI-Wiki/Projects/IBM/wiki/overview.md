---
title: "Uriel product overview"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Uriel product overview

Uriel targets the **Real-Time AI for Critical Decisions** track of IBM Z Datathon, according to the supplied context. It is a simulation prototype proposal for coordinating connected cars at an unsignalized intersection.

Cars report observed positions, velocities and intended routes through Python/BeamNGpy bridges. A LinuxONE service predicts conflict-zone timing, schedules crossing order and recommends feasible speed caps. A small learned arrival-time predictor supports explicit geometry, reservations and physical constraints; the bridge owns immediate actuation and fallback.

Start with two cars and fixed routes in one BeamNG world. Expand to four cars only after the basic loop is reliable. Multiple laptop worlds share a backend for aggregate load; their vehicles do not physically interact across worlds. Cameras, LiDAR perception, unknown-car detection, potholes, rerouting and evasive steering are later extensions.

The team has four people: two experienced and two beginners. Named roles are recorded in [[team-workflow]]. BeamNG driving integration has been exercised locally, and the user reports a teammate successfully ran the IBM-hosted server version. The laptop's live BeamNG trials used local coordination because SSH-tunnel latency exceeded controller deadlines. S5 reports all four have BeamNG.tech/BeamNGpy installed on Fedora 44 KDE. The lead laptop is reported as Ryzen 7 7840HS, RTX 4060 Mobile with 8 GB VRAM and 16 GB RAM; other allocations are unknown. This does not establish 25-car real-time capacity per laptop. Existing code and bounded trial evidence are described in [[implementation-status]].

Cooperative intersection management is established research. Claims must follow demonstrated integration, ML evaluation, deployment and experiments; no arbitrary-traffic safety or performance guarantee exists.

## Sources

- [[sources]]: S5 sections 1–6, 13, 16, 19; S1 remains historical.
- Related: [[decisions]], [[architecture]], [[event-preparation]].
