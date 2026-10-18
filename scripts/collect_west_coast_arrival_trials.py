#!/usr/bin/env python3
"""Collect randomized arrival/clearance telemetry on saved West Coast routes.

BeamNG.tech must already be open with the GE Lua/BeamNGpy server on port 25252.
The collector uses only the saved clone12/clone13 cars and their linked editor
NavGraph routes. It does not start traffic. --rust-url enables Rust speed advice.
Labels are provisional until the junction boundary is calibrated.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import time
import uuid

from beamngpy import BeamNGpy, Vehicle
from beamngpy.sensors import Damage, Electrics


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "scenarios" / "extended-90-degree-data-collection" / "extended-90-degree-data-collection.json"
IDS = ("clone12", "clone13")
ROUTES = {
    # Keep both cars on the drivable road graph. This is the last clean,
    # damage-free clone12 route; direct coordinate cutting is not safe here.
    "clone12": ["junction1_wp12", "junction1_wp18"],
    "clone13": [
        "tunnel_city_A_57", "tunnel_city_A_58", "tunnel_city_A_59",
        "tunnel_city_A_60", "tunnel_city_A_61", "tunnel_city_A_62",
        "tunnel_city_A_63", "junction1_wp12", "junction1_wp29",
    ],
}
ZONE = {"center_xyz_m": [-363.9833175, 612.7043416, 74.9039979],
        "radius_m": 4.3655501548769, "source": "BeamNG West Coast road graph junction1_wp12.radius",
        "status": "provisional candidate; pavement boundary not surveyed"}
ROUTE_DISTANCE_M = {"clone12": 100.0, "clone13": 154.0}
SCHEDULE = [
    (6.0, 6.0, 4.0, 0.0, 5.0),
    (7.0, 6.0, 18.0, 0.0, 7.0),
    (6.0, 7.0, 16.0, 0.0, 11.0),
    (8.0, 7.0, 0.0, 0.0, 10.0),
    (7.0, 8.0, 13.0, 0.0, 8.0),
    (8.0, 8.0, 12.0, 0.0, 5.0),
    (5.0, 6.0, 17.0, 0.0, 11.0),
    (6.0, 5.0, 0.0, 7.0, 21.0),
    (9.0, 6.0, 0.0, 13.0, 28.0),
    (6.0, 9.0, 19.0, 0.0, 19.0),
    (9.0, 8.0, 0.0, 0.0, 8.0),
    (8.0, 5.0, 0.0, 15.0, 33.0),
]
FIELDS = [
    "trial_id", "frame_id", "sim_time_s", "elapsed_s", "vehicle_id", "vehicle_model",
    "target_speed_mps", "start_delay_s", "ai_active", "x_m", "y_m", "z_m",
    "forward_x", "forward_y", "forward_z", "up_x", "up_y", "up_z",
    "vx_mps", "vy_mps", "vz_mps", "speed_mps", "forward_speed_mps",
    "ax_mps2", "ay_mps2", "az_mps2", "throttle", "brake", "steering",
    "gear", "damage", "nearest_vehicle_id", "nearest_distance_m",
    "nearest_relative_speed_mps", "bbox_world_json", "zone_occupied",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def selector_for(vehicle):
    kind = vehicle.queue_lua_command(
        "local g=powertrain.getDevice('gearbox'); return g and g.type or 'missing'",
        response=True,
    )
    if kind in ("dctGearbox", "automaticGearbox"):
        return 2
    if kind == "manualGearbox":
        return 1
    raise RuntimeError(f"Unsupported gearbox on {vehicle.vid}: {kind!r}")


def compile_editor_paths(bng, routes):
    """Expand selected nodes exactly as the editor draws them, without lane detours."""
    encoded = json.dumps(routes)
    chunk = "local routes=jsonDecode([==[" + encoded + "]==]);" + """
local graph=map.getGraphpath();local out={};
for name,waypoints in pairs(routes) do
  local path={};
  for i=1,#waypoints-1 do
    local section=map.getPath(waypoints[i],waypoints[i+1]);
    assert(#section>1,'Disconnected editor path for '..name);
    for _,node in ipairs(section) do
      if #path==0 or path[#path]~=node then path[#path+1]=node end
    end
  end
  local positions={};
  for _,node in ipairs(path) do
    local p=graph.positions[node];assert(p,'Unknown road node '..node);
    positions[#positions+1]={p.x,p.y,p.z}
  end
  out[name]={path=path,positions=positions}
end;return jsonEncode(out)
"""
    paths = json.loads(bng.control.queue_lua_command(chunk, response=True))
    if any(len(paths[name]["path"]) < 2 for name in routes):
        raise RuntimeError("Editor paths must contain connected road nodes")
    return paths


def start_editor_path(vehicle, path, speed_mps):
    """Supply a complete graph path; wpTargetList would invoke a different planner."""
    if len(path) < 2 or not math.isfinite(speed_mps) or speed_mps <= 0:
        raise ValueError("A connected path and a positive finite speed are required")
    nodes = ",".join(json.dumps(node) for node in path)
    command = ("ai.driveUsingPath{path={" + nodes + "},routeSpeed=" + repr(float(speed_mps))
               + ",routeSpeedMode='limit',driveInLane='off',avoidCars='on',aggression=0.3};return ai.mode")
    return vehicle.queue_lua_command(command, response=True)


def read_ai_path(vehicle):
    return json.loads(vehicle.queue_lua_command("""
for i=1,16 do
  local name,value=debug.getupvalue(ai.dumpCurrentRoute,i)
  if not name then break end
  if name=='currentRoute' then return jsonEncode(value and value.path or {}) end
end;return '[]'
""", response=True))


def convex_hull(points):
    points = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(points) <= 2:
        return points

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def point_in_polygon(point, poly):
    inside = False
    j = len(poly) - 1
    for i, a in enumerate(poly):
        b = poly[j]
        if ((a[1] > point[1]) != (b[1] > point[1]) and
                point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]):
            inside = not inside
        j = i
    return inside


def launch_stalled(start_pos, current_pos, elapsed_since_launch_s,
                   timeout_s=5.0, min_displacement_m=0.5):
    """Stop a batch when an AI launch produces no measurable vehicle motion."""
    moved = math.dist(start_pos, current_pos)
    return elapsed_since_launch_s >= timeout_s and moved < min_displacement_m


def yaw_half_turn(quaternion_xyzw):
    """Pre-multiply an XYZW pose quaternion by a 180-degree world-Z rotation."""
    x, y, z, w = quaternion_xyzw
    return (-y, x, w, -z)


def overlaps_zone(box):
    center = ZONE["center_xyz_m"]
    z_values = [float(p[2]) for p in box]
    if min(z_values) > center[2] + 2.2 or max(z_values) < center[2] - 2.2:
        return False
    hull = convex_hull(box)
    c = (center[0], center[1])
    if point_in_polygon(c, hull):
        return True
    return min(point_segment_distance(c, hull[i], hull[(i + 1) % len(hull)])
               for i in range(len(hull))) <= ZONE["radius_m"]


def get_box_lua():
    names = ",".join(json.dumps(name) for name in IDS)
    return (
        "local out={}; for _,name in ipairs({" + names + "}) do "
        "local v=scenetree.findObject(name); if not v then error('missing '..name) end; "
        "local b=v:getSpawnWorldOOBB(); local p={}; "
        "for i=0,7 do local q=b:getPoint(i); p[#p+1]={q.x,q.y,q.z} end; "
        "out[name]=p end; return jsonEncode(out)"
    )


def sample(vehicles, boxes, previous, trial_id, frame, elapsed, settings, active):
    states = {v.vid: v.state for v in vehicles}
    damage = {v.vid: float(v.sensors["damage"].get("damage", 0.0)) for v in vehicles}
    rows = []
    for vehicle in vehicles:
        name = vehicle.vid
        s = states[name]
        pos, vel, direction, up = s["pos"], s["vel"], s["dir"], s["up"]
        speed = math.sqrt(sum(x * x for x in vel))
        forward_speed = sum(a * b for a, b in zip(vel, direction))
        old = previous.get(name)
        dt = float(s["time"]) - old[0] if old else 0.0
        acc = [(a - b) / dt for a, b in zip(vel, old[1])] if old and dt > 1e-8 else [None] * 3
        previous[name] = (float(s["time"]), list(vel))
        other = next(v for v in vehicles if v.vid != name)
        other_state = states[other.vid]
        separation = math.dist(pos, other_state["pos"])
        relative_velocity = [a - b for a, b in zip(other_state["vel"], vel)]
        line = [a - b for a, b in zip(other_state["pos"], pos)]
        relative_speed = (sum(a * b for a, b in zip(relative_velocity, line)) / separation
                          if separation > 1e-8 else None)
        electrics = vehicle.sensors["electrics"]
        rows.append({
            "trial_id": trial_id, "frame_id": frame, "sim_time_s": float(s["time"]),
            "elapsed_s": elapsed, "vehicle_id": name, "vehicle_model": vehicle.model,
            "target_speed_mps": settings[name]["speed_mps"],
            "start_delay_s": settings[name]["delay_s"], "ai_active": name in active,
            "x_m": pos[0], "y_m": pos[1], "z_m": pos[2],
            "forward_x": direction[0], "forward_y": direction[1], "forward_z": direction[2],
            "up_x": up[0], "up_y": up[1], "up_z": up[2],
            "vx_mps": vel[0], "vy_mps": vel[1], "vz_mps": vel[2],
            "speed_mps": speed, "forward_speed_mps": forward_speed,
            "ax_mps2": acc[0], "ay_mps2": acc[1], "az_mps2": acc[2],
            "throttle": electrics.get("throttle"), "brake": electrics.get("brake"),
            "steering": electrics.get("steering"),
            "gear": electrics.get("gear_index", electrics.get("gear")),
            "damage": damage[name], "nearest_vehicle_id": other.vid,
            "nearest_distance_m": separation, "nearest_relative_speed_mps": relative_speed,
            "bbox_world_json": json.dumps(boxes[name], separators=(",", ":")),
            "zone_occupied": overlaps_zone(boxes[name]),
        })
    return rows, damage


def trial_spec(index, routes=None, rng=None, min_speed_kmh=18.0,
               max_speed_kmh=40.0, max_delay_s=15.0):
    if routes is not None:
        rng = rng or random.Random()
        return {
            name: {"speed_mps": rng.uniform(min_speed_kmh, max_speed_kmh) / 3.6,
                   "delay_s": rng.uniform(0.0, max_delay_s), "route": routes[name]}
            for name in IDS
        } | {"planned_arrival_gap_s": None}
    a, b, delay_a, delay_b, gap = SCHEDULE[index]
    return {
        "clone12": {"speed_mps": a, "delay_s": delay_a, "route": ROUTES["clone12"]},
        "clone13": {"speed_mps": b, "delay_s": delay_b, "route": ROUTES["clone13"]},
        "planned_arrival_gap_s": gap,
    }


def stop_and_restore(bng, vehicles, saved, restore):
    errors = []
    for v in vehicles:
        try:
            v.ai.set_mode("disabled")
            v.control(steering=0, throttle=0, brake=1, parkingbrake=1,
                      gear=restore["selectors"].get(v.vid))
        except Exception as e:
            errors.append(f"stop {v.vid}: {e!r}")
    try:
        bng.control.pause()
    except Exception as e:
        errors.append(f"pause: {e!r}")
    if restore.get("positions"):
        for v in vehicles:
            try:
                p = saved[v.vid]
                if not bng.vehicles.teleport(v, tuple(p["position_m"]),
                                             rot_quat=tuple(p["rotation_quat_xyzw"]),
                                             reset=True, safe_spawn=False):
                    errors.append(f"restore {v.vid}: teleport refused")
            except Exception as e:
                errors.append(f"restore {v.vid}: {e!r}")
    try:
        bng.control.pause()
    except Exception as e:
        errors.append(f"final pause: {e!r}")
    return errors


def run_trial(bng, vehicles, saved, selectors, batch_dir, index, max_sim_s,
              speed_factor, routes, rng, min_speed_kmh, max_speed_kmh,
              max_delay_s, snapshot_path, sample_callback=None, speed_scales=None,
              rust_controller=None):
    spec = trial_spec(index, routes, rng, min_speed_kmh, max_speed_kmh,
                      max_delay_s)
    for name, scale in (speed_scales or {}).items():
        if name not in spec or not math.isfinite(scale) or scale <= 0:
            raise ValueError("Invalid per-route speed multiplier")
        spec[name]["speed_mps"] *= scale
    exact_paths = compile_editor_paths(bng, {name: spec[name]["route"] for name in IDS})
    config = {name: {"speed_mps": spec[name]["speed_mps"],
                     "delay_s": spec[name]["delay_s"],
                     "model": saved[name].get("model"),
                     "vehicle_config_sha256": hashlib.sha256(json.dumps(
                         saved[name].get("config", {}), sort_keys=True).encode()).hexdigest(),
                     "expanded_path": exact_paths[name]["path"],
                     "path_mode": "explicit_editor_graph_path",
                     "route": spec[name]["route"]} for name in IDS}
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    trial_id = f"trial-{index + 1:02d}-{config_hash[:8]}"
    folder = batch_dir / trial_id
    folder.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    metadata = {
        "trial_id": trial_id, "group_id": config_hash, "status": "preparing",
        "started_utc": started, "level": "west_coast_usa", "controlled_vehicles": list(IDS),
        "other_scene_vehicles_ignored": [],
        "configuration": config, "planned_arrival_gap_s": spec["planned_arrival_gap_s"],
        "approach_distance_estimates_m": {},
        "zone": ZONE, "labels_are_training_eligible": False,
        "label_limitation": "zone boundary is a provisional map-node-radius proxy; contact sensor unavailable",
        "sampling": {"target_hz": 5.0,
                     "physics_steps_per_sample": max(1, 4 // speed_factor),
                     "physics_rate_hz": 60, "beamng_speed_factor": speed_factor},
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "beamngpy_version": "1.36", "damage_before": {},
        "editor_routes": {name: spec[name]["route"] for name in IDS},
        "expanded_graph_paths": exact_paths,
        "path_execution": "explicit connected graph path; lane-based replanning disabled; car avoidance enabled",
        "coordination_mode": "rust_crossing" if rust_controller else "native_ai_baseline",
        "rust_scenario": rust_controller.client.scenario if rust_controller else None,
    }
    write_json(folder / "metadata.json", metadata)
    events = []
    active = set()
    previous = {}
    entry = {name: None for name in IDS}
    clearance = {name: None for name in IDS}
    ever_occupied = {name: False for name in IDS}
    first_damage = {name: None for name in IDS}
    launch_state = {}
    path_readbacks = {}
    rows_written = 0
    damage_before = {}
    restore_state = {"selectors": selectors, "positions": True}

    for v in vehicles:
        v.ai.set_mode("disabled")
        v.control(steering=0, throttle=0, brake=1, parkingbrake=1,
                  gear=selectors[v.vid])
        p = saved[v.vid]
        if not bng.vehicles.teleport(v, tuple(p["position_m"]),
                                     rot_quat=tuple(p["rotation_quat_xyzw"]),
                                     reset=True, safe_spawn=False):
            raise RuntimeError(f"Could not restore saved pose for {v.vid}")
        v.set_shift_mode("realistic_automatic")
        v.control(steering=0, throttle=0, brake=1, parkingbrake=1,
                  gear=selectors[v.vid])

    bng.control.step(1)
    for v in vehicles:
        v.sensors.poll()
        damage_before[v.vid] = float(v.sensors["damage"].get("damage", 0.0))
        if damage_before[v.vid] > 5.0:
            raise RuntimeError(f"{v.vid} is already damaged ({damage_before[v.vid]}); refusing trial")
    metadata["damage_before"] = damage_before
    metadata["status"] = "recording"
    write_json(folder / "metadata.json", metadata)

    duration = max_sim_s
    lua = get_box_lua()
    stop_reason = "duration_elapsed"
    start_sim = None
    elapsed = 0.0
    previous_elapsed = None
    frozen_frames = 0
    wall_start = time.perf_counter()
    with (folder / "telemetry.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for frame in range(int(math.ceil(duration * 5.0)) + 1):
            elapsed_target = elapsed
            for v in vehicles:
                name = v.vid
                if name not in active and elapsed_target + 1e-9 >= spec[name]["delay_s"]:
                    # Release the manual brake before handing control to BeamNG AI.
                    # Sending a manual control frame after the AI route can keep the
                    # electrics brake input asserted and pin the car at its spawn.
                    v.control(steering=0, throttle=0, brake=0, parkingbrake=0,
                              gear=selectors[name])
                    start_editor_path(v, exact_paths[name]["path"], spec[name]["speed_mps"])
                    active.add(name)
                    launch_state[name] = {"elapsed_s": elapsed_target,
                                          "start_pos": list(v.state["pos"])}
                    events.append({"event": "ai_launch", "vehicle_id": name,
                                   "elapsed_s": elapsed_target,
                                   "target_speed_mps": spec[name]["speed_mps"]})
                    print(f"  {trial_id}: launched {name} at t={elapsed_target:.1f}s", flush=True)
            if frame:
                bng.control.step(max(1, 4 // speed_factor))
            for v in vehicles:
                v.sensors.poll()
                if v.vid in active and v.vid not in path_readbacks:
                    actual_path = read_ai_path(v)
                    if actual_path:
                        expected_path = exact_paths[v.vid]["path"]
                        if len(actual_path) > len(expected_path) or actual_path != expected_path[-len(actual_path):]:
                            raise RuntimeError(f"{v.vid} accepted a different graph path; refusing to continue")
                        path_readbacks[v.vid] = actual_path
                        events.append({"event": "ai_path_readback", "vehicle_id": v.vid,
                                       "elapsed_s": elapsed, "path": actual_path})
            boxes = json.loads(bng.control.queue_lua_command(lua, response=True))
            sim_times = [float(v.state["time"]) for v in vehicles]
            if start_sim is None:
                start_sim = min(sim_times)
            elapsed = max(sim_times) - start_sim
            frozen_frames = frozen_frames + 1 if previous_elapsed is not None and elapsed <= previous_elapsed else 0
            if frozen_frames >= 5:
                raise RuntimeError("Physics clock did not advance across five sampling steps; recording aborted")
            previous_elapsed = elapsed
            new_rows, damages = sample(vehicles, boxes, previous, trial_id, frame,
                                       elapsed, config, active)
            current_positions = {
                row["vehicle_id"]: (row["x_m"], row["y_m"], row["z_m"])
                for row in new_rows
            }
            for row in new_rows:
                name = row["vehicle_id"]
                hit = row["zone_occupied"]
                if hit and not ever_occupied[name] and entry[name] is None:
                    entry[name] = elapsed
                    ever_occupied[name] = True
                    events.append({"event": "zone_entry_proxy", "vehicle_id": name,
                                   "elapsed_s": elapsed})
                elif not hit and ever_occupied[name] and clearance[name] is None:
                    clearance[name] = elapsed
                    events.append({"event": "rear_clearance_proxy", "vehicle_id": name,
                                   "elapsed_s": elapsed})
                if damages[name] > damage_before[name] + 5.0 and first_damage[name] is None:
                    first_damage[name] = elapsed
                    events.append({"event": "damage_sensor_threshold", "vehicle_id": name,
                                   "elapsed_s": elapsed,
                                   "increase": damages[name] - damage_before[name]})
            for row in new_rows:
                writer.writerow(row)
                rows_written += 1
            if sample_callback is not None:
                sample_callback(trial_id, frame, elapsed, vehicles)
            if rust_controller is not None and not any(value is not None for value in first_damage.values()):
                rust_controller.update(new_rows, vehicles)
            if frame % 10 == 0:
                stream.flush()
                print(f"  {trial_id}: {elapsed:5.1f}s sim, entries={entry}, clearance={clearance}, "
                      f"damage={damages}", flush=True)
            if any(value is not None for value in first_damage.values()):
                stop_reason = "damage_sensor_threshold"
                break
            stalled = [name for name in active
                       if not (rust_controller and name in rust_controller.yielding_ids)
                       if launch_stalled(launch_state[name]["start_pos"],
                                         current_positions[name],
                                         elapsed - launch_state[name]["elapsed_s"])]
            if stalled:
                stop_reason = "launch_failed_no_motion"
                events.append({"event": "launch_failed_no_motion", "vehicle_ids": stalled,
                               "elapsed_s": elapsed, "minimum_displacement_m": 0.5,
                               "watchdog_timeout_s": 5.0})
                break
            if all(clearance[n] is not None for n in IDS):
                stop_reason = "both_cleared"
                break
            if elapsed >= duration:
                break

    summary = {
        "trial_id": trial_id, "group_id": config_hash,
        "outcome": stop_reason,
        "motion_valid": stop_reason not in {"launch_failed_no_motion"},
        "simulated_seconds": elapsed if start_sim is not None else 0.0,
        "wall_seconds": time.perf_counter() - wall_start,
        "samples_per_vehicle": rows_written // len(IDS),
        "entry_time_proxy_s": entry, "rear_clearance_time_proxy_s": clearance,
        "damage_increase": {name: max(0.0, float(v.sensors["damage"].get("damage", 0.0)) - damage_before[name])
                            for name, v in ((v.vid, v) for v in vehicles)},
        "damage_before": damage_before,
        "damage_before_entry": {name: first_damage[name] is not None and
                                 (entry[name] is None or first_damage[name] <= entry[name])
                                 for name in IDS},
        "labels_are_training_eligible": False,
        "label_quality": "provisional map-radius occupancy proxy; exact conflict polygon not calibrated",
        "contact_evidence": None,
        "events": events,
        "ai_path_readbacks": path_readbacks,
    }
    for event in events:
        with (folder / "events.jsonl").open("a", encoding="utf-8") as event_file:
            event_file.write(json.dumps(event, allow_nan=False) + "\n")
    write_json(folder / "summary.json", summary)
    metadata.update(status=("invalid_no_motion" if stop_reason == "launch_failed_no_motion" else
                            "complete" if stop_reason in {"both_cleared", "duration_elapsed"} else
                            "stopped_on_damage"), finished_utc=datetime.now(timezone.utc).isoformat(),
                    sample_count=rows_written)
    write_json(folder / "metadata.json", metadata)
    print("TRIAL", json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=12, choices=range(1, 13))
    parser.add_argument("--start-index", type=int, default=0, choices=range(0, 12),
                        help="first schedule index to collect (0-based); supports resuming after a pilot")
    parser.add_argument("--port", type=int, default=25252)
    parser.add_argument("--max-sim-s", type=float, default=65.0)
    parser.add_argument("--speed-factor", type=int, default=4, choices=(1, 2, 4),
                        help="BeamNG deterministic speed; 4 keeps approximately 5 Hz telemetry")
    parser.add_argument("--min-speed-kmh", type=float, default=18.0)
    parser.add_argument("--max-speed-kmh", type=float, default=40.0)
    parser.add_argument("--max-delay-s", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--output", type=Path, default=ROOT / "runs")
    parser.add_argument("--export-rust-scenario", type=Path,
                        help="read live road geometry and export Rust scenario, without moving cars")
    parser.add_argument("--rust-url", help="optional ws://host:port/ws/bridge speed-cap coordinator")
    parser.add_argument("--rust-scenario", type=Path,
                        help="exact scenario file exported for the Rust server")
    args = parser.parse_args()
    if args.min_speed_kmh <= 0 or args.max_speed_kmh < args.min_speed_kmh:
        parser.error("speed bounds must satisfy 0 < min <= max")
    if args.max_delay_s < 0:
        parser.error("--max-delay-s must be nonnegative")
    if args.rust_url and (not args.rust_scenario or args.export_rust_scenario):
        parser.error("--rust-url needs --rust-scenario and cannot be combined with export")
    if args.rust_url and args.max_speed_kmh > 43.2:
        parser.error("Rust crossing mode currently supports at most 43.2 km/h")
    snapshot = read_json(args.snapshot)
    saved = {v["name"]: v for v in snapshot["vehicles"]}
    # Older pose snapshots stored quaternions opposite to their measured
    # headings; the named editor-session snapshot captures live orientations.
    # Check each car against its live heading before applying any correction.
    routes = {s.get("linked_vehicle_name"): s.get("graphNodes")
              for s in snapshot.get("splines", []) if s.get("isEnabled")}
    routes = {name: routes.get(name) for name in IDS}
    if (not set(IDS).issubset(saved) or snapshot.get("mapName") != "west_coast_usa"
            or any(not route or len(route) < 2 for route in routes.values())):
        raise RuntimeError("Snapshot must contain both saved cars and enabled linked NavGraph routes on West Coast USA")
    rng = random.Random(args.seed)
    batch = args.output / ("west-coast-arrival-" + uuid.uuid4().hex[:10])
    batch.mkdir(parents=True, exist_ok=False)
    bng = BeamNGpy("127.0.0.1", args.port, quit_on_close=False, socket_timeout=5)
    vehicles = []
    summaries = []
    selectors = {}
    failures = []
    try:
        bng.open(launch=False)
        bng.connection.skt.skt.settimeout(8)
        level = bng.control.queue_lua_command("return getCurrentLevelIdentifier()", response=True)
        if level != "west_coast_usa":
            raise RuntimeError(f"Expected West Coast USA; found {level!r}; no car commands sent")
        rust_scenario = None
        if args.export_rust_scenario or args.rust_url:
            from crossing_client import scenario_from_paths
            exact_paths = compile_editor_paths(bng, routes)
            expected = scenario_from_paths(exact_paths, saved, ZONE["center_xyz_m"], ZONE["radius_m"])
            if args.export_rust_scenario:
                write_json(args.export_rust_scenario, expected)
                print(f"EXPORTED {args.export_rust_scenario}; no vehicle commands sent", flush=True)
                return
            rust_scenario = read_json(args.rust_scenario)
            if rust_scenario != expected:
                raise RuntimeError("Rust scenario differs from the saved/live editor paths; export it again")
        info = json.loads(bng.control.queue_lua_command(
            "local out={};for _,v in ipairs(getAllVehicles()) do out[v:getName()]={model=v:getJBeamFilename(),id=v:getID()} end;return jsonEncode(out)",
            response=True))
        for name in IDS:
            expected_model = saved[name]["model"]
            if name not in info or info[name]["model"] != expected_model:
                raise RuntimeError(f"Expected saved {expected_model} {name}; found {info.get(name)!r}")
            v = Vehicle(name, model=expected_model)
            v.connect(bng)
            v.connection.skt.skt.settimeout(8)
            v.sensors.attach("damage", Damage())
            v.sensors.attach("electrics", Electrics())
            vehicles.append(v)
        bng.control.pause()
        bng.settings.set_deterministic(60, speed_factor=args.speed_factor)
        for v in vehicles:
            v.ai.set_mode("disabled")
            selectors[v.vid] = selector_for(v)
            v.set_shift_mode("realistic_automatic")
            v.control(steering=0, throttle=0, brake=1, parkingbrake=1,
                      gear=selectors[v.vid])
        bng.control.step(1)
        positions = {}
        pose_adjustments = {}
        for v in vehicles:
            v.sensors.poll()
            pos = v.state["pos"]
            initial = saved[v.vid]
            delta = math.dist(pos, initial["position_m"])
            heading_dot = sum(a * b for a, b in zip(v.state["dir"], initial["forward"]))
            if delta <= 2.0 and heading_dot < -0.95:
                corrected = yaw_half_turn(initial["rotation_quat_xyzw"])
                if not bng.vehicles.teleport(v, tuple(initial["position_m"]),
                                             rot_quat=corrected, reset=True,
                                             safe_spawn=False):
                    raise RuntimeError(f"Could not align {v.vid} to its saved approach heading")
                initial["rotation_quat_xyzw"] = corrected
                pose_adjustments[v.vid] = "applied 180-degree yaw to match saved forward vector"
            elif delta > 2.0 or heading_dot < 0.95:
                raise RuntimeError(f"{v.vid} differs from the saved pose (position delta={delta:.2f}m, "
                                   f"heading dot={heading_dot:.3f}); refusing to take over")
        if pose_adjustments:
            bng.control.step(1)
        for v in vehicles:
            v.sensors.poll()
            initial = saved[v.vid]
            delta = math.dist(v.state["pos"], initial["position_m"])
            heading_dot = sum(a * b for a, b in zip(v.state["dir"], initial["forward"]))
            if delta > 2.0 or heading_dot < 0.95:
                raise RuntimeError(f"{v.vid} differs from the saved pose (position delta={delta:.2f}m, "
                                   f"heading dot={heading_dot:.3f}); refusing to take over")
            positions[v.vid] = {"delta_m": delta, "heading_dot": heading_dot,
                                "heading_adjustment": pose_adjustments.get(v.vid)}
        write_json(batch / "batch.json", {
            "batch_id": batch.name, "created_utc": datetime.now(timezone.utc).isoformat(),
            "level": level, "trials_requested": args.trials,
            "vehicles": list(IDS), "starting_pose_check": positions,
            "snapshot_heading_check": "live heading checked against saved forward vector; quaternion corrected only on opposite heading",
            "other_scene_vehicles_ignored": sorted(set(info) - set(IDS)),
            "scene_traffic": "not spawned; user reported disabled",
            "candidate_zone": ZONE, "training_ready": False,
            "reason_not_training_ready": "geometry boundary is provisional; trainer is fixed to Small Grid",
            "seed": args.seed,
            "randomization": {"speed_kmh": [args.min_speed_kmh, args.max_speed_kmh],
                              "start_delay_s": [0.0, args.max_delay_s]},
            "editor_routes": routes,
            "schedule": {"distribution": "uniform per car and trial",
                         "speed_kmh": [args.min_speed_kmh, args.max_speed_kmh],
                         "start_delay_s": [0.0, args.max_delay_s]},
            "beamng_speed_factor": args.speed_factor,
            "target_sampling_hz": 5.0,
        })
        print(f"CONNECTED {level}; saved poses match; collecting {args.trials} trials in {batch}", flush=True)
        for index in range(args.start_index, args.start_index + args.trials):
            rust_controller = None
            try:
                if args.rust_url:
                    from crossing_client import CrossingController
                    rust_controller = CrossingController(args.rust_url, rust_scenario,
                        batch / f"crossing-{index + 1:02d}-wire.jsonl")
                summary = run_trial(bng, vehicles, saved, selectors, batch, index,
                                    args.max_sim_s, args.speed_factor, routes, rng,
                                    args.min_speed_kmh, args.max_speed_kmh,
                                    args.max_delay_s, args.snapshot,
                                    rust_controller=rust_controller)
                summaries.append(summary)
            except BaseException as e:
                failures.append({"trial_index": index + 1, "error": repr(e)})
                print(f"TRIAL_FAILED {index + 1}: {e!r}", flush=True)
                break
            finally:
                if rust_controller is not None:
                    rust_controller.close()
            if summary["outcome"] == "damage_sensor_threshold":
                print("STOPPING_BATCH: damage threshold; leaving scene paused", flush=True)
                break
            errors = stop_and_restore(bng, vehicles, saved,
                                      {"selectors": selectors, "positions": True})
            if errors:
                failures.append({"trial_index": index + 1, "cleanup_errors": errors})
                print("RESTORE_FAILED", errors, flush=True)
                break
            if summary["outcome"] == "launch_failed_no_motion":
                print("STOPPING_BATCH: no-motion watchdog; inspect AI route before collecting more", flush=True)
                break
            if index + 1 < args.trials:
                time.sleep(0.5)
        complete = len(summaries)
        write_json(batch / "batch_summary.json", {
            "batch_id": batch.name, "trials_requested": args.trials,
            "trials_recorded": complete, "failures": failures,
            "entry_events_by_vehicle": {name: sum(s["entry_time_proxy_s"][name] is not None for s in summaries)
                                         for name in IDS},
            "clearance_events_by_vehicle": {name: sum(s["rear_clearance_time_proxy_s"][name] is not None for s in summaries)
                                             for name in IDS},
            "clean_no_damage_trials": sum(s.get("motion_valid", False) and
                                             all(x <= 5 for x in s["damage_increase"].values())
                                             for s in summaries),
            "invalid_no_motion_trials": sum(not s.get("motion_valid", False) for s in summaries),
            "distinct_groups": len({s["group_id"] for s in summaries}),
            "training_ready": False,
            "note": "raw telemetry and provisional proxy labels saved; calibrate junction boundary before training",
        })
    finally:
        if vehicles and bng.connection:
            try:
                stop_and_restore(bng, vehicles, saved,
                                 {"selectors": selectors, "positions": not any(
                                     s.get("outcome") == "damage_sensor_threshold" for s in summaries)})
            except Exception as e:
                failures.append({"final_cleanup_error": repr(e)})
        if bng.connection:
            bng.disconnect()
        print(f"EVIDENCE {batch}", flush=True)


if __name__ == "__main__":
    main()
