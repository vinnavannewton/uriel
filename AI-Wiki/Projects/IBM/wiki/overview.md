---
title: "Uriel product overview"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Uriel product overview

Uriel targets the **Real-Time AI for Critical Decisions** track of IBM Z Datathon, according to the supplied context. The lead describes its broader vision as a shared AI supervisor connecting autonomous vehicles' onboard AI for cooperative road safety. An onboard client would share state, intentions and hazards with the supervisor, which predicts interactions and sends coordinated guidance back to participating vehicles. Each vehicle retains immediate driving control and local fallback.

IBM LinuxONE hosts the shared Rust coordination service and ML worker. Timely prediction and communication are central design requirements because advice must arrive while vehicles can still respond. The prototype reports positions, velocities and intended routes through Python/BeamNGpy bridges, predicts conflict timing and recommends speed caps. This simulator bridge represents the future onboard integration; deployment on real autonomous vehicles is not implemented.

The two-car 90-degree BeamNG crossing is a small demonstration of the wider supervisory idea. It makes a shared decision visible by slowing one car while another passes. The wider scope includes oncoming encounters, rear-end threats, shared road hazards and coordinated responses across a road network; these ambitions must remain distinct from the bounded simulator evidence. Multiple laptop worlds can share a backend for aggregate load, but their vehicles do not physically interact across worlds.

The team has four people: two experienced and two beginners. Named roles are recorded in [[team-workflow]]. BeamNG driving integration has been exercised locally, and the user reports a teammate successfully ran the IBM-hosted server version. The laptop's live BeamNG trials used local coordination because SSH-tunnel latency exceeded controller deadlines. S5 reports all four have BeamNG.tech/BeamNGpy installed on Fedora 44 KDE. The lead laptop is reported as Ryzen 7 7840HS, RTX 4060 Mobile with 8 GB VRAM and 16 GB RAM; other allocations are unknown. This does not establish 25-car real-time capacity per laptop. Existing code and bounded trial evidence are described in [[implementation-status]].

Cooperative intersection management is established research. Claims must follow demonstrated integration, ML evaluation, deployment and experiments; no arbitrary-traffic safety or performance guarantee exists.

## Sources

- [[sources]]: S5 sections 1–6, 13, 16, 19; S1 remains historical.
- Related: [[decisions]], [[architecture]], [[event-preparation]].
