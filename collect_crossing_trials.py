"""Collect three authorized, uncoordinated BeamNG Small Grid crossing trials."""

import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time
import uuid

from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import Damage, Electrics


TRIALS = [(8, 8, 0), (8, 8, 3), (10, 6, 0)]
FIELDS = ["trial", "vehicle", "sim_time", "elapsed", "x", "y", "z",
          "front_x", "front_y", "front_z", "vx", "vy", "vz", "speed",
          "dir_x", "dir_y", "dir_z", "throttle", "brake", "steering",
          "damage", "front_in_zone"]


def script(axis, speed, delay):
    nodes = []
    if delay:
        nodes.append(dict(x=0, y=-40, z=0, t=0))
    for distance in range(0, 101, 10):
        p = -40 + distance
        nodes.append(dict(x=p if axis == "x" else 0,
                          y=p if axis == "y" else 0, z=0,
                          t=delay + distance / speed))
    return nodes


def main():
    root = Path(__file__).resolve().parent / "runs" / ("crossing-" + uuid.uuid4().hex)
    root.mkdir(parents=True)
    meta = {"status": "running", "map": "smallgrid", "mode": "scripted-ai-uncoordinated",
            "beamngpy": importlib.metadata.version("beamngpy"),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "sample_step_seconds": 0.1, "duration_seconds": 20,
            "zone": {"x": [-3, 3], "y": [-3, 3]},
            "arrival_definition": "first sampled front reference point inside zone; no interpolation",
            "limitations": ["front reference entry is not body occupancy or rear clearance",
                             "damage change is not a complete contact detector",
                             "three trials are pilot data, not a trained model or acceptance suite"],
            "trials": []}
    metadata = root / "metadata.json"
    metadata.write_text(json.dumps(meta, indent=2))
    print("OUTPUT", root, flush=True)
    b = BeamNGpy("localhost", 25252)
    connected = False
    try:
        b.open(launch=False)
        connected = True
        b.settings.set_deterministic(60)
        for number, (red_speed, blue_speed, delay) in enumerate(TRIALS, 1):
            folder = root / f"trial-{number}"
            folder.mkdir()
            s = Scenario("smallgrid", f"uriel_collect_{uuid.uuid4().hex[:8]}")
            vehicles = []
            for name, color, pos, quat in [
                ("uriel_red", (1, 0, 0, 1), (-40, 0, 0.5), (0, 0, -math.sqrt(.5), math.sqrt(.5))),
                ("uriel_blue", (0, .15, 1, 1), (0, -40, .5), (0, 0, 1, 0)),
            ]:
                v = Vehicle(name, model="etkc", color=color)
                v.sensors.attach("damage", Damage())
                v.sensors.attach("electrics", Electrics())
                s.add_vehicle(v, pos=pos, rot_quat=quat)
                vehicles.append(v)
            config = {"trial": number, "red_target_mps": red_speed,
                      "blue_target_mps": blue_speed, "blue_delay_seconds": delay,
                      "scenario": s.name, "status": "running"}
            meta["trials"].append(config)
            metadata.write_text(json.dumps(meta, indent=2))
            s.make(b)
            b.scenario.load(s)
            b.scenario.start()
            b.control.pause()
            # Let freshly spawned cars settle under brakes before collecting.
            for v in vehicles:
                v.ai.set_mode("disabled")
                v.control(throttle=0, brake=1, parkingbrake=1)
            b.control.step(120)
            for v in vehicles:
                v.sensors.poll()
                dx, dy, _ = v.state["dir"]
                expected = dx if v.vid == "uriel_red" else dy
                if expected < .95:
                    raise RuntimeError(f"Unexpected initial heading: {v.vid} {v.state}")
                v.control(throttle=0, brake=0, parkingbrake=0)
            vehicles[0].ai.set_script(script("x", red_speed, 0))
            vehicles[1].ai.set_script(script("y", blue_speed, delay))
            rows, starts = [], {}
            print("START TRIAL", number, config, flush=True)
            with (folder / "telemetry.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                for sample in range(201):
                    if sample:
                        b.control.step(6)
                    for v in vehicles:
                        v.sensors.poll()
                        state = v.state
                        starts.setdefault(v.vid, state["time"])
                        pos, front, vel, direction = (state[k] for k in ("pos", "front", "vel", "dir"))
                        electrics = v.sensors["electrics"]
                        row = dict(trial=number, vehicle=v.vid, sim_time=state["time"],
                                   elapsed=state["time"]-starts[v.vid],
                                   speed=math.sqrt(sum(x*x for x in vel)),
                                   throttle=electrics.get("throttle"), brake=electrics.get("brake"),
                                   steering=electrics.get("steering"),
                                   damage=v.sensors["damage"].get("damage"),
                                   front_in_zone=abs(front[0]) <= 3 and abs(front[1]) <= 3)
                        for keys, values in [(('x','y','z'),pos),
                                             (('front_x','front_y','front_z'),front),
                                             (('vx','vy','vz'),vel),
                                             (('dir_x','dir_y','dir_z'),direction)]:
                            row.update(zip(keys, values))
                        writer.writerow(row)
                        rows.append(row)
                    f.flush()
            summary = {}
            arrivals = {}
            for v in vehicles:
                vr = [r for r in rows if r["vehicle"] == v.vid]
                arrival = next((r["elapsed"] for r in vr if r["front_in_zone"]), None)
                arrivals[v.vid] = arrival
                summary[v.vid] = {"arrival_seconds": arrival,
                    "censored": arrival is None, "rows": len(vr),
                    "max_speed_mps": max(r["speed"] for r in vr),
                    "damage_increase": max(r["damage"] for r in vr)-vr[0]["damage"],
                    "final_position": [vr[-1][k] for k in ("x", "y", "z")]}
            with (folder / "arrival_labels.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["trial", "vehicle", "sim_time", "arrival_seconds", "remaining_seconds", "censored"])
                writer.writeheader()
                for r in rows:
                    arrival = arrivals[r["vehicle"]]
                    if arrival is not None and r["elapsed"] > arrival:
                        continue
                    writer.writerow(dict(trial=number, vehicle=r["vehicle"], sim_time=r["sim_time"],
                        arrival_seconds=arrival, remaining_seconds=None if arrival is None else arrival-r["elapsed"],
                        censored=arrival is None))
            (folder / "summary.json").write_text(json.dumps(summary, indent=2))
            config.update(status="complete", summary=summary)
            metadata.write_text(json.dumps(meta, indent=2))
            for v in vehicles:
                v.ai.set_mode("disabled")
                v.control(throttle=0, brake=1, parkingbrake=1)
            print("COMPLETE TRIAL", number, json.dumps(summary), flush=True)
        meta["status"] = "complete"
    except BaseException as error:
        meta.update(status="failed", error=repr(error))
        raise
    finally:
        metadata.write_text(json.dumps(meta, indent=2))
        if connected:
            try:
                b.control.pause()
            finally:
                b.disconnect()
        print("SAVED", root, meta["status"], flush=True)


if __name__ == "__main__":
    main()
