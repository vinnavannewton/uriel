#!/usr/bin/env python3
"""Collect three Small Grid 90-degree trials with two streaming LiDARs.

The existing fresh-experiment geometry, AI routes and OOBB event labels are
reused. Ground-truth vehicle states are sampled at 30 Hz; each subject's
streaming LiDAR is requested at 20 Hz and stored independently as compressed
point-cloud arrays. No Uriel control commands are sent.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import importlib.metadata
import json
import math
import random
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import Damage, Electrics, Lidar

from fresh_experiment import (
    FIELDS,
    ROOT,
    aggression_preset,
    ai_line,
    box_metrics,
    configuration,
    derive_events,
    dump,
    position,
    set_ai_aggression,
)


SIM_HZ = 30
LIDAR_HZ = 20
LIDAR_CONFIG = {
    "mode": "full_360",
    "requested_update_interval_seconds": 1 / LIDAR_HZ,
    "max_distance_m": 80.0,
    "vertical_resolution_channels": 32,
    "vertical_field_of_view_degrees": 26.9,
    "frequency_hz": 20.0,
    "density": 25,
    "visualized": False,
    "semantic_annotations": False,
    "shared_memory_streaming": True,
    "sensor_local_position_m": [0.0, 0.0, 1.8],
    "coordinate_frame": "BeamNG.tech LiDAR pointCloud output; empirically checked against world-space sensor pose during validation",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=25252)
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--duration", type=float, default=25.0)
    p.add_argument("--seed", type=int, default=781003)
    p.add_argument("--ai-aggression", type=float, default=0.3)
    p.add_argument("--output", type=Path, default=ROOT / "uriel_lidar_experiment")
    p.add_argument("--resume", type=Path, help="resume a prior experiment directory without overwriting completed trials")
    p.add_argument("--background-config", type=Path, default=ROOT / "scenarios/smallgrid_background_configs.json")
    p.add_argument("--validation-duration", type=float, default=3.0)
    p.add_argument("--safe-sequential", action="store_true",
                   help="run only red/blue subjects; hold blue until red is rear-clear and stopped")
    return p


def sequential_configuration(seed: int, aggression: float) -> list[dict[str, Any]]:
    """Build a two-car, one-at-a-time crossing with no background traffic."""
    rng = random.Random(seed)
    configs = []
    for index, (vehicle_id, axis, color) in enumerate((
        ("uriel_red", "x", (1, 0, 0, 1)),
        ("uriel_blue", "y", (0, 0.15, 1, 1)),
    )):
        configs.append({
            "vehicle_id": vehicle_id, "role": "subject", "axis": axis,
            "lane": 0, "progress": -40, "start_delay": 0.0,
            "target_speed": round(rng.uniform(3.0, 4.0), 3),
            "initial_speed_requested": 0.0, "model": "etkc",
            "source_background_id": None,
            "route_id": f"{axis}_lane_0", "color": color,
            "aggression": aggression, "ai_started": False,
            "sequence_order": index + 1,
        })
    return configs


def boxes_overlap_3d(first: list[list[float]], second: list[list[float]]) -> bool:
    """Conservative AABB overlap test over the simulator OOBB corner sets."""
    a = np.asarray(first, dtype=float)
    b = np.asarray(second, dtype=float)
    return bool(np.all(a.min(axis=0) <= b.max(axis=0)) and
                np.all(b.min(axis=0) <= a.max(axis=0)))


def sensor_pose(state: dict[str, Any]) -> dict[str, Any]:
    """Derive roof sensor pose from the contemporaneous vehicle state."""
    pos = np.asarray(state["pos"], dtype=float)
    up = np.asarray(state["up"], dtype=float)
    direction = np.asarray(state["dir"], dtype=float)
    sensor_pos = pos + up * LIDAR_CONFIG["sensor_local_position_m"][2]
    return {
        "position_world_m": sensor_pos.tolist(),
        "direction_world": direction.tolist(),
        "up_world": up.tolist(),
        "vehicle_state_time_s": state.get("time"),
        "method": "vehicle pose plus configured 1.8m local-up mount offset",
    }


def save_cloud(path: Path, points: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, points=points.astype(np.float32, copy=False))
    return str(path)


def vehicle_row(v: Any, c: dict[str, Any], run_id: str, frame: int,
                elapsed: float, sim_time: float, boxes: dict[str, Any],
                previous: dict[str, Any], lidar_ref: str | None) -> dict[str, Any]:
    st = v.state
    p, vel, direction, up = st["pos"], st["vel"], st["dir"], st["up"]
    e = v.sensors["electrics"]
    acc = [None, None, None]
    if v.vid in previous:
        old = previous[v.vid]
        dt = sim_time - old["time"]
        if dt > 0:
            acc = [(a - b) / dt for a, b in zip(vel, old["vel"])]
    previous[v.vid] = {"time": sim_time, "vel": vel}
    peers = [u for u in _all_vehicles if u.vid != v.vid]
    nearest = min(peers, key=lambda u: math.dist(p, u.state["pos"]))
    distance = math.dist(p, nearest.state["pos"])
    relative_velocity = [a - b for a, b in zip(nearest.state["vel"], vel)]
    delta = [a - b for a, b in zip(nearest.state["pos"], p)]
    radial = sum(a * b for a, b in zip(relative_velocity, delta)) / distance if distance > 0 else None
    front, rear, overlap = box_metrics(boxes[v.vid], c)
    lateral_axis = 1 if c["axis"] == "x" else 0
    lateral = p[lateral_axis] - c["lane"]
    right = (direction[1], -direction[0], 0)
    roll = math.atan2(sum(a * b for a, b in zip(up, right)), up[2])
    return dict(
        run_id=run_id, frame_id=frame, sim_time=sim_time, elapsed=elapsed,
        vehicle_id=v.vid, vehicle_role=c["role"], x=p[0], y=p[1], z=p[2],
        yaw=math.atan2(direction[1], direction[0]),
        pitch=math.atan2(direction[2], math.hypot(*direction[:2])), roll=roll,
        vx=vel[0], vy=vel[1], vz=vel[2], speed=math.sqrt(sum(a*a for a in vel)),
        ax=acc[0], ay=acc[1], az=acc[2], throttle=e.get("throttle"),
        brake=e.get("brake"), steering=e.get("steering"),
        gear=e.get("gear_index", e.get("gear")), ai_mode="manual" if c.get("ai_started") else "disabled",
        ai_aggression=c["aggression"], ai_aggression_preset=aggression_preset(c["aggression"]),
        target_speed=c["target_speed"], route_id=c["route_id"], start_delay=c["start_delay"],
        nearest_vehicle_id=nearest.vid, relative_distance=distance, relative_speed=radial,
        damage=v.sensors["damage"].get("damage"), verified_contact=None,
        lane_state="within_virtual_lane" if abs(lateral) <= 1.8 else "outside_virtual_lane",
        conflict_zone_state="overlap" if overlap else "outside",
        route_deviation=abs(lateral) > 2, front_progress=front, rear_progress=rear,
        bbox_json=json.dumps(boxes[v.vid], separators=(",", ":")),
        lidar_index_ref=lidar_ref,
    )


_all_vehicles: list[Any] = []


def collect_trial(bng: BeamNGpy, folder: Path, run_id: str, seed: int,
                  backgrounds: list[dict[str, Any]], duration: float,
                  aggression: float, *, validation: bool = False,
                  safe_sequential: bool = False) -> dict[str, Any]:
    global _all_vehicles
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "lidar/red").mkdir(parents=True)
    (folder / "lidar/blue").mkdir(parents=True)
    (folder / "events.jsonl").touch()
    (folder / "telemetry.csv").touch()
    (folder / "lidar_index.jsonl").touch()
    config = sequential_configuration(seed, aggression) if safe_sequential else configuration(seed, backgrounds)
    for c in config:
        c["aggression"] = aggression
    run_tag = f"{run_id}_{uuid.uuid4().hex[:6]}"
    subject_ids = {"uriel_red", "uriel_blue"}
    meta: dict[str, Any] = {
        "run_id": run_id, "seed": seed, "status": "preparing",
        "map": "smallgrid", "duration_target_seconds": duration,
        "simulator_version": "BeamNG.tech 0.39.4.0 (local install)",
        "beamngpy_version": importlib.metadata.version("beamngpy"),
        "sampling": {"vehicle_state_target_hz": SIM_HZ, "lidar_target_hz": LIDAR_HZ,
                     "simulator_fixed_step_hz": SIM_HZ},
        "vehicle_configuration": config,
        "configuration": config,
        "lidar_configuration": {**LIDAR_CONFIG, "visualized": bool(validation)},
        "validation_trial": validation,
        "controller": ("sequential ground-truth safety gate; BeamNG AI route following; no Rust control"
                       if safe_sequential else "BeamNG AI baseline only; no URIEL control commands"),
        "safe_sequential": safe_sequential,
        "geometry": {"map": "smallgrid", "zone": {"x": [-3, 3], "y": [-3, 3]},
                     "intersection": "virtual origin crossing on Small Grid", "zone_bounds_m": {"x": [-3, 3], "y": [-3, 3]},
                     "subject_start_distance_target_m": 40.0, "subject_route_angle_target_deg": 90.0,
                     "physical_road_markings": "not present; routes are predefined virtual AI paths"},
        "limitations": [
            "Small Grid has no calibrated public-road intersection; the 90-degree crossing and lane boundaries are virtual coordinates.",
            "Conflict events use spawn OOBB proxies, not deforming collision geometry.",
            "BeamNG damage is recorded, but verified contact sensing is unavailable.",
            "LiDAR data are raw observations; simulator IDs, poses and labels stay in separate ground-truth telemetry.",
            "Semantic annotations are disabled to avoid ground-truth labels leaking into perception input.",
            *( ["Vehicles are released sequentially using simulator ground truth; this is not LiDAR-driven conflict control."] if safe_sequential else [] ),
        ],
    }
    dump(folder / "metadata.json", meta)
    dump(folder / "geometry.json", meta["geometry"])
    vehicles: list[Any] = []
    lidars: dict[str, Lidar] = {}
    outcomes: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    lidar_errors: list[dict[str, Any]] = []
    point_counts: dict[str, list[int]] = {"uriel_red": [], "uriel_blue": []}
    lidar_futures: list[concurrent.futures.Future] = []
    state_pool = concurrent.futures.ThreadPoolExecutor(max_workers=6)
    disk_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    try:
        scenario = Scenario("smallgrid", f"uriel_lidar_{uuid.uuid4().hex[:10]}",
                            human_name="URIEL 90 Degree LiDAR Baseline",
                            description=("Two perpendicular ETK subjects, sequential release, no background traffic."
                                         if safe_sequential else "Two perpendicular ETK subjects and four AI traffic vehicles."))
        for i, c in enumerate(config):
            part_config = None if i < 2 else backgrounds[i - 2].get("config")
            vehicle = Vehicle(c["vehicle_id"], model=c["model"],
                              license=f"URIEL-{i+1}", color=c["color"], part_config=part_config)
            vehicle.sensors.attach("damage", Damage())
            vehicle.sensors.attach("electrics", Electrics())
            quaternion = (0, 0, -math.sqrt(.5), math.sqrt(.5)) if c["axis"] == "x" else (0, 0, 1, 0)
            scenario.add_vehicle(vehicle, pos=position(c), rot_quat=quaternion)
            vehicles.append(vehicle)
        _all_vehicles = vehicles
        scenario.make(bng)
        bng.scenario.load(scenario)
        bng.scenario.start()
        bng.control.pause()
        bng.settings.set_deterministic(SIM_HZ)
        for vehicle in vehicles:
            vehicle.ai.set_mode("disabled")
            vehicle.set_shift_mode("realistic_automatic")
            # BeamNG can retain velocity for a reused vehicle ID across scenario
            # reloads. Zero it before any settling steps so start-pose checks
            # measure the new scenario rather than momentum from the old one.
            vehicle.set_velocity(0.0, dt=1 / SIM_HZ)
            vehicle.control(throttle=0, brake=1, parkingbrake=1)
        bng.control.step(1)

        initial: dict[str, Any] = {}
        dimensions: dict[str, Any] = {}
        for vehicle, c in zip(vehicles, config):
            vehicle.sensors.poll()
            state = vehicle.state
            meta.setdefault("observed_initial_state", {})[vehicle.vid] = state
            expected_pos = position(c)
            if math.dist(state["pos"][:2], expected_pos[:2]) > 1:
                raise RuntimeError(f"{vehicle.vid}: start position differs from configured route origin")
            expected_axis = 0 if c["axis"] == "x" else 1
            if state["dir"][expected_axis] < .99:
                raise RuntimeError(f"{vehicle.vid}: heading does not match the perpendicular route")
            bbox = list(vehicle.get_bbox().values())
            axis = 0 if c["axis"] == "x" else 1
            dimensions[vehicle.vid] = {
                "length_m": max(p[axis] for p in bbox) - min(p[axis] for p in bbox),
                "width_m": max(p[1-axis] for p in bbox) - min(p[1-axis] for p in bbox),
                "height_m": max(p[2] for p in bbox) - min(p[2] for p in bbox),
            }
            initial[vehicle.vid] = state
            vehicle.control(throttle=0, brake=0, parkingbrake=0)
            vehicle.set_velocity(c["initial_speed_requested"], dt=1 / SIM_HZ)
        bng.control.step(1)
        for vehicle, c in zip(vehicles, config):
            vehicle.sensors.poll()
            c["initial_speed_measured_mps"] = math.sqrt(sum(v*v for v in vehicle.state["vel"]))
            vehicle.control(throttle=0, brake=1, parkingbrake=1)
        for vehicle in vehicles:
            if vehicle.sensors["damage"].get("damage", 0) > 1:
                raise RuntimeError(f"{vehicle.vid}: vehicle damaged during setup")
        baseline_damage = {
            vehicle.vid: float(vehicle.sensors["damage"].get("damage", 0.0))
            for vehicle in vehicles
        }
        meta.update(observed_initial_state=initial, vehicle_dimensions=dimensions)
        for vehicle, c in zip(vehicles[:2], config[:2]):
            name = f"uriel_lidar_{run_tag}_{'red' if vehicle.vid == 'uriel_red' else 'blue'}"
            lidar = Lidar(
                name, bng, vehicle=vehicle,
                requested_update_time=1 / LIDAR_HZ,
                pos=tuple(LIDAR_CONFIG["sensor_local_position_m"]),
                vertical_resolution=32, vertical_angle=26.9,
                frequency=20, max_distance=80, density=25,
                is_360_mode=True, is_rotate_mode=False,
                is_using_shared_memory=True, is_streaming=True,
                is_visualised=bool(validation), is_annotated=False,
            )
            lidars[vehicle.vid] = lidar
            sensor_world = lidar.get_position()
            meta.setdefault("sensor_identity", {})[vehicle.vid] = {
                "sensor_id": name, "attached_vehicle_id": vehicle.vid,
                "sensor_world_position_setup_m": list(sensor_world),
                "sensor_configuration": {**LIDAR_CONFIG, "visualized": bool(validation)},
            }
        meta.update(status="recording", scene="Small Grid", subject_geometry_verified=True)
        dump(folder / "metadata.json", meta)
        dump(folder / "geometry.json", {**meta["geometry"],
             "observed_initial_states": initial, "vehicle_dimensions": dimensions,
             "subject_heading_angle_degrees": 90.0})

        # Streaming LiDAR reads shared memory directly, so the state loop never
        # waits for a BeamNG GE socket response. Disk compression is also queued
        # separately, with a bounded backlog and explicit dropped-frame rows.
        previous: dict[str, Any] = {}
        active: set[str] = set()
        sequence = {
            "red_stop_requested": False,
            "red_stopped_frames": 0,
            "blue_released": False,
            "blue_stop_requested": False,
            "blue_stopped_frames": 0,
            "complete": False,
            "overlap_frames": 0,
        }
        next_lidar_due = {vid: None for vid in subject_ids}
        telemetry_rows: list[dict[str, Any]] = []
        events.extend({"run_id": run_id, "vehicle_id": c["vehicle_id"], "event": "configured_route",
                       "route_id": c["route_id"], "target_speed_mps": c["target_speed"],
                       "start_delay_seconds": c["start_delay"]} for c in config)
        start_sim: float | None = None
        frame_count = round(duration * SIM_HZ) + 1
        with (folder / "telemetry.csv").open("w", newline="") as telemetry:
            writer = csv.DictWriter(telemetry, fieldnames=FIELDS + ["lidar_index_ref"])
            writer.writeheader()
            with (folder / "lidar_index.jsonl").open("a", encoding="utf-8") as lidar_index:
                for frame in range(frame_count):
                    if frame:
                        bng.control.step(1)
                    list(state_pool.map(lambda v: v.sensors.poll(), vehicles))
                    states = {v.vid: v.state for v in vehicles}
                    if start_sim is None:
                        start_sim = float(states["uriel_red"]["time"])
                    sim_time = float(states["uriel_red"]["time"])
                    elapsed = sim_time - start_sim
                    for vehicle, c in zip(vehicles, config):
                        if safe_sequential:
                            launch_ready = (
                                (vehicle.vid == "uriel_red" and frame == 0)
                                or (vehicle.vid == "uriel_blue" and sequence["blue_released"])
                            )
                        else:
                            launch_ready = elapsed + 1e-9 >= c["start_delay"]
                        if vehicle.vid not in active and launch_ready:
                            vehicle.control(throttle=0, brake=0, parkingbrake=0)
                            vehicle.ai.set_line(ai_line(c))
                            set_ai_aggression(vehicle, aggression)
                            c["ai_started"] = True
                            active.add(vehicle.vid)
                            events.append({"run_id": run_id, "vehicle_id": vehicle.vid,
                                           "event": "AI_launch_command", "frame_id": frame,
                                           "elapsed": elapsed, "sim_time": sim_time})
                    lua = 'local out={}; for _,name in ipairs({' + ",".join(json.dumps(v.vid) for v in vehicles) + '}) do local v=scenetree.findObject(name); local box=v:getSpawnWorldOOBB(); local p={}; for i=0,7 do local a=box:getPoint(i); p[#p+1]={a.x,a.y,a.z} end; out[name]=p end; return jsonEncode(out)'
                    boxes = json.loads(bng.control.queue_lua_command(lua, response=True))

                    if safe_sequential:
                        red_vehicle = next(v for v in vehicles if v.vid == "uriel_red")
                        blue_vehicle = next(v for v in vehicles if v.vid == "uriel_blue")
                        red_box, blue_box = boxes["uriel_red"], boxes["uriel_blue"]
                        if boxes_overlap_3d(red_box, blue_box):
                            sequence["overlap_frames"] += 1
                            bng.control.pause()
                            for v in vehicles:
                                v.ai.set_mode("disabled")
                                v.control(throttle=0, brake=1, parkingbrake=1)
                            raise RuntimeError(f"safety_interlock_oobb_overlap frame={frame}")
                        for v in vehicles:
                            damage = float(v.sensors["damage"].get("damage", 0.0))
                            if damage > baseline_damage[v.vid] + 1.0:
                                bng.control.pause()
                                for subject in vehicles:
                                    subject.ai.set_mode("disabled")
                                    subject.control(throttle=0, brake=1, parkingbrake=1)
                                raise RuntimeError(
                                    f"safety_interlock_damage_increase vehicle={v.vid} frame={frame}"
                                )

                        subject_by_id = {c["vehicle_id"]: c for c in config}
                        for vehicle, stop_key, stopped_key, next_release in (
                            (red_vehicle, "red_stop_requested", "red_stopped_frames", "blue_released"),
                            (blue_vehicle, "blue_stop_requested", "blue_stopped_frames", "complete"),
                        ):
                            if vehicle.vid not in active or sequence["complete"]:
                                continue
                            _, rear, zone_overlap = box_metrics(boxes[vehicle.vid], subject_by_id[vehicle.vid])
                            if not sequence[stop_key] and rear > 15.0 and not zone_overlap:
                                vehicle.ai.set_mode("disabled")
                                vehicle.control(throttle=0, brake=1, parkingbrake=0)
                                sequence[stop_key] = True
                                events.append({"run_id": run_id, "vehicle_id": vehicle.vid,
                                               "event": "rear_clearance_verified_brake_requested",
                                               "frame_id": frame, "sim_time": sim_time,
                                               "rear_progress_m": rear})
                            if sequence[stop_key]:
                                speed_now = math.sqrt(sum(float(x) ** 2 for x in vehicle.state["vel"]))
                                if speed_now < 0.2:
                                    sequence[stopped_key] += 1
                                else:
                                    sequence[stopped_key] = 0
                                if sequence[stopped_key] >= 15 and not sequence[next_release]:
                                    vehicle.control(throttle=0, brake=1, parkingbrake=1)
                                    if next_release == "blue_released":
                                        sequence["blue_released"] = True
                                        events.append({"run_id": run_id, "vehicle_id": vehicle.vid,
                                                       "event": "stopped_verified_release_next_vehicle",
                                                       "frame_id": frame, "sim_time": sim_time,
                                                       "next_vehicle_id": "uriel_blue"})
                                    else:
                                        sequence["complete"] = True
                                        events.append({"run_id": run_id, "vehicle_id": vehicle.vid,
                                                       "event": "stopped_verified_sequence_complete",
                                                       "frame_id": frame, "sim_time": sim_time})

                    frame_refs: dict[str, str] = {}
                    for vid in subject_ids:
                        lidar = lidars[vid]
                        if next_lidar_due[vid] is None:
                            next_lidar_due[vid] = sim_time + 1 / LIDAR_HZ
                        if sim_time + 1e-6 < next_lidar_due[vid]:
                            continue
                        while next_lidar_due[vid] <= sim_time + 1e-6:
                            next_lidar_due[vid] += 1 / LIDAR_HZ
                        index_row = {
                            "run_id": run_id, "frame_id": frame, "vehicle_id": vid,
                            "sensor_id": meta["sensor_identity"][vid]["sensor_id"],
                            "sim_time_s": sim_time, "capture_host_monotonic_s": time.monotonic(),
                            "sensor_pose": sensor_pose(states[vid]),
                            "sensor_configuration": {k: v for k, v in meta["sensor_identity"][vid]["sensor_configuration"].items()},
                            "coordinate_frame": "world_xyz_m (BeamNG.tech Lidar pointCloud output)",
                        }
                        try:
                            points = np.asarray(lidar.stream().get("pointCloud", []), dtype=np.float32).reshape((-1, 3))
                            index_row["point_count"] = int(len(points))
                            index_row["status"] = "ok" if len(points) else "empty_reading"
                            point_counts[vid].append(len(points))
                            relative = Path("lidar") / ("red" if vid == "uriel_red" else "blue") / f"frame_{frame:06d}.npz"
                            if len(points):
                                pending = sum(not f.done() for f in lidar_futures)
                                if pending < 8:
                                    future = disk_pool.submit(save_cloud, folder / relative, points.copy())
                                    lidar_futures.append(future)
                                    index_row["point_cloud_file"] = relative.as_posix()
                                    index_row["storage_status"] = "queued"
                                    frame_refs[vid] = relative.as_posix()
                                else:
                                    index_row["status"] = "dropped_write_backlog"
                                    index_row["storage_status"] = "not_queued"
                                    lidar_errors.append({"vehicle_id": vid, "frame_id": frame, "error": "writer queue full"})
                        except Exception as exc:
                            index_row.update(status="sensor_error", error=repr(exc))
                            lidar_errors.append({"vehicle_id": vid, "frame_id": frame, "error": repr(exc)})
                        lidar_index.write(json.dumps(index_row, allow_nan=False) + "\n")
                    for vehicle, c in zip(vehicles, config):
                        row = vehicle_row(vehicle, c, run_id, frame, elapsed, sim_time,
                                          boxes, previous, frame_refs.get(vehicle.vid))
                        writer.writerow(row)
                        telemetry_rows.append(row)
                    telemetry.flush()
                    if frame and frame % (SIM_HZ * 5) == 0:
                        print(f"PROGRESS {run_id} {elapsed:.1f}s sim; frames={frame}", flush=True)

        for future in concurrent.futures.as_completed(lidar_futures):
            try:
                future.result()
            except Exception as exc:
                lidar_errors.append({"error": f"point cloud write failed: {exc!r}"})
        # Only the two subject cars are expected to use the central conflict
        # zone. The four offset traffic paths intentionally stay outside it.
        event_list, outcomes = derive_events(telemetry_rows, config[:2])
        events.extend(event_list)
        with (folder / "events.jsonl").open("w", encoding="utf-8") as stream:
            for event in sorted(events, key=lambda e: (e.get("sim_time", e.get("elapsed", 0)), e.get("vehicle_id", ""))):
                stream.write(json.dumps(event, allow_nan=False) + "\n")
        per_vehicle_samples = {vid: point_counts[vid] for vid in sorted(point_counts)}
        moving_status = {}
        for c in config:
            rows = [r for r in telemetry_rows if r["vehicle_id"] == c["vehicle_id"]]
            displacement = math.dist((rows[-1]["x"], rows[-1]["y"]), (rows[0]["x"], rows[0]["y"]))
            moving_status[c["vehicle_id"]] = {
                "ai_start_commanded": bool(c.get("ai_started")),
                "distance_moved_m": displacement,
                "moving_observed": displacement > 0.5,
                "route_deviation_observed": any(r["route_deviation"] for r in rows),
                "route_deviation_frames": sum(bool(r["route_deviation"]) for r in rows),
                "stopped_frames_after_scheduled_start": sum(
                    float(r["elapsed"]) >= c["start_delay"] and float(r["speed"]) < 0.2 for r in rows
                ),
                "damage_increase": max(float(r["damage"]) for r in rows) - float(rows[0]["damage"]),
                "route_endpoint_reached": (rows[-1]["x"] if c["axis"] == "x" else rows[-1]["y"]) >= 98,
                "final_position_m": [rows[-1]["x"], rows[-1]["y"], rows[-1]["z"]],
                "route_id": c["route_id"],
                "target_speed_mps": c["target_speed"],
                "start_delay_seconds": c["start_delay"],
                "outcome": outcomes.get(c["vehicle_id"]),
            }
        actual_time = telemetry_rows[-1]["sim_time"] - telemetry_rows[0]["sim_time"]
        quality = {
            "target_vehicle_state_hz": SIM_HZ,
            "measured_vehicle_state_hz": (frame_count - 1) / actual_time if actual_time > 0 else None,
            "vehicle_state_rows": len(telemetry_rows),
            "expected_vehicle_state_rows": frame_count * len(config),
            "all_expected_vehicle_ids_present": {c["vehicle_id"] for c in config} == {r["vehicle_id"] for r in telemetry_rows},
            "sample_timestamp_gaps": sum(
                1 for a, b in zip(telemetry_rows, telemetry_rows[len(config):])
                if b["sim_time"] <= a["sim_time"]
            ),
            "lidar_readings": {vid: len(values) for vid, values in per_vehicle_samples.items()},
            "lidar_nonempty_readings": {vid: sum(n > 0 for n in values) for vid, values in per_vehicle_samples.items()},
            "lidar_mean_points": {vid: (float(np.mean(values)) if values else None) for vid, values in per_vehicle_samples.items()},
            "lidar_errors": lidar_errors,
            "point_cloud_files": sum(1 for _ in (folder / "lidar").glob("**/*.npz")),
            "background_vehicle_count": sum(c["role"] == "background" for c in config),
            "all_background_ai_commands_sent": all(
                moving_status[c["vehicle_id"]]["ai_start_commanded"]
                for c in config if c["role"] == "background"
            ),
            "safe_sequential": safe_sequential,
            "rear_clearance_and_stops_verified": sequence["complete"] if safe_sequential else None,
            "simulator_oobb_overlap_frames": sequence["overlap_frames"],
        }
        status = "PASS_WITH_LIMITATIONS"
        if quality["vehicle_state_rows"] != quality["expected_vehicle_state_rows"]:
            status = "FAIL"
        if quality["measured_vehicle_state_hz"] is None or abs(quality["measured_vehicle_state_hz"] - SIM_HZ) > 0.1:
            status = "FAIL"
        if any(quality["lidar_nonempty_readings"][vid] < max(1, int(duration * 10)) for vid in subject_ids):
            status = "FAIL"
        if quality["point_cloud_files"] != sum(quality["lidar_nonempty_readings"].values()):
            status = "FAIL"
        if safe_sequential:
            expected_to_move = {"uriel_red"} if validation else {"uriel_red", "uriel_blue"}
            if any(not moving_status[vid]["moving_observed"] for vid in expected_to_move):
                status = "FAIL"
            if sequence["overlap_frames"]:
                status = "FAIL"
            if not validation and not sequence["complete"]:
                status = "FAIL"
        elif any(not moving_status[c["vehicle_id"]]["moving_observed"] for c in config):
            status = "FAIL"
        if any(quality["lidar_nonempty_readings"][vid] < max(1, int(duration * LIDAR_HZ * 0.8)) for vid in subject_ids):
            status = "FAIL"
        meta.update(status="complete" if status != "FAIL" else "failed_validation",
                    quality=status, telemetry_quality=quality, vehicle_observed_behaviour=moving_status,
                    outcomes=outcomes, lidar_errors=lidar_errors,
                    sample_count=len(telemetry_rows), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        report = {
            "status": status, "run_id": run_id, "expected_state_hz": SIM_HZ,
            "measured_state_hz": quality["measured_vehicle_state_hz"],
            "initial_positions_and_headings_verified": True,
            "initial_vehicle_dimensions_m": dimensions,
            "subjects_perpendicular": True,
            "lidar_nonempty_readings": quality["lidar_nonempty_readings"],
            "lidar_mean_points": quality["lidar_mean_points"],
            "background_vehicle_count": quality["background_vehicle_count"],
            "background_ai_commanded": quality["all_background_ai_commands_sent"],
            "safe_sequential": safe_sequential,
            "rear_clearance_and_stops_verified": quality["rear_clearance_and_stops_verified"],
            "simulator_oobb_overlap_frames": quality["simulator_oobb_overlap_frames"],
            "unresolved": meta["limitations"],
        }
        dump(folder / "validation_report.json", report)
        dump(folder / "metadata.json", meta)
        print(f"COMPLETE {run_id} {status} rows={len(telemetry_rows)} lidar={quality['lidar_readings']}", flush=True)
        return meta
    except BaseException as exc:
        meta.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc))
        dump(folder / "metadata.json", meta)
        dump(folder / "validation_report.json", {"status": "FAIL", "reason": repr(exc)})
        raise
    finally:
        state_pool.shutdown(wait=True, cancel_futures=True)
        disk_pool.shutdown(wait=True, cancel_futures=True)
        for lidar in lidars.values():
            try:
                lidar.remove()
            except Exception:
                pass
        for vehicle in vehicles:
            try:
                vehicle.ai.set_mode("disabled")
                vehicle.control(throttle=0, brake=1, parkingbrake=1)
            except Exception:
                pass
        try:
            bng.control.pause()
        except Exception:
            pass


def write_lidar_summary(exp: Path, results: list[dict[str, Any]]) -> None:
    fields = ["run_id", "seed", "status", "quality", "sample_count",
              "state_hz", "red_entry_s", "red_clearance_s", "blue_entry_s",
              "blue_clearance_s", "non_arrivals", "route_deviations",
              "damage_increase", "verified_contact", "red_lidar_readings",
              "blue_lidar_readings", "red_lidar_mean_points", "blue_lidar_mean_points",
              "randomized_vehicle_speeds_and_delays"]
    with (exp / "trial_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for meta in results:
            configurations = meta.get("vehicle_configuration", meta.get("configuration", []))
            outcomes = meta.get("outcomes", {})
            quality = meta.get("telemetry_quality", {})
            writer.writerow({
                "run_id": meta.get("run_id"), "seed": meta.get("seed"),
                "status": meta.get("status"), "quality": meta.get("quality"),
                "sample_count": meta.get("sample_count"),
                "state_hz": quality.get("measured_vehicle_state_hz"),
                "red_entry_s": outcomes.get("uriel_red", {}).get("entry_seconds"),
                "red_clearance_s": outcomes.get("uriel_red", {}).get("clearance_seconds"),
                "blue_entry_s": outcomes.get("uriel_blue", {}).get("entry_seconds"),
                "blue_clearance_s": outcomes.get("uriel_blue", {}).get("clearance_seconds"),
                "non_arrivals": sum(o.get("arrival_censored", False) for o in outcomes.values()),
                "route_deviations": sum(o.get("route_deviation", False) for o in outcomes.values()),
                "damage_increase": json.dumps({
                    vid: state.get("damage_increase")
                    for vid, state in meta.get("vehicle_observed_behaviour", {}).items()
                }, sort_keys=True),
                "verified_contact": "unavailable; damage is separate evidence",
                "red_lidar_readings": quality.get("lidar_readings", {}).get("uriel_red"),
                "blue_lidar_readings": quality.get("lidar_readings", {}).get("uriel_blue"),
                "red_lidar_mean_points": quality.get("lidar_mean_points", {}).get("uriel_red"),
                "blue_lidar_mean_points": quality.get("lidar_mean_points", {}).get("uriel_blue"),
                "randomized_vehicle_speeds_and_delays": json.dumps([
                    {k: c.get(k) for k in ("vehicle_id", "route_id", "target_speed", "start_delay", "initial_speed_measured_mps")}
                    for c in configurations
                ], sort_keys=True),
            })


def main() -> int:
    args = parser().parse_args()
    if args.trials != 3:
        raise SystemExit("This experiment is defined as exactly three fresh trials")
    if args.duration <= 0 or args.validation_duration <= 0:
        raise SystemExit("durations must be positive")
    if args.safe_sequential and args.duration < 35:
        raise SystemExit("--safe-sequential requires --duration >= 35 seconds")
    if not 0.3 <= args.ai_aggression <= 1.0:
        raise SystemExit("--ai-aggression must be between 0.3 and 1.0")
    backgrounds = [] if args.safe_sequential else json.loads(args.background_config.read_text(encoding="utf-8"))
    if not args.safe_sequential and len(backgrounds) != 4:
        raise SystemExit("Background config must define exactly four vehicles")
    if args.resume:
        exp = args.resume.expanduser().resolve()
        config_path = exp / "experiment_config.json"
        if not config_path.exists():
            raise SystemExit(f"Cannot resume: missing {config_path}")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("random_seeds") != [args.seed, args.seed + 1, args.seed + 2]:
            raise SystemExit("Cannot resume with different random seeds")
        if config.get("trial_duration_seconds") != args.duration:
            raise SystemExit("Cannot resume with a different trial duration")
        if config.get("safe_sequential", False) != args.safe_sequential:
            raise SystemExit("Cannot resume with a different safe-sequential setting")
        validation_report_path = exp / "validation_report.json"
        if not validation_report_path.exists() or json.loads(validation_report_path.read_text()).get("status") == "FAIL":
            raise SystemExit("Cannot resume: sensor validation is missing or failed")
        config.pop("error", None)
        config["status"] = "resuming_trials"
        dump(config_path, config)
    else:
        root = args.output.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        experiment_id = f"experiment_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{uuid.uuid4().hex[:8]}"
        exp = root / experiment_id
        exp.mkdir(exist_ok=False)
        config = {
        "experiment_id": experiment_id, "map": "smallgrid", "trial_count": args.trials,
        "trial_duration_seconds": args.duration, "validation_duration_seconds": args.validation_duration,
        "random_seeds": [args.seed, args.seed + 1, args.seed + 2],
        "vehicle_state_target_hz": SIM_HZ, "lidar_target_hz": LIDAR_HZ,
        "ai_aggression": args.ai_aggression,
        "background_vehicle_count": 0 if args.safe_sequential else 4,
        "safe_sequential": args.safe_sequential,
        "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "beamngpy_version": importlib.metadata.version("beamngpy"),
        "background_configuration_source": str(args.background_config),
        "status": "starting_validation",
        }
        dump(exp / "experiment_config.json", config)
        (exp / "collector_source.py").write_bytes(Path(__file__).read_bytes())
        if not args.safe_sequential:
            (exp / "source_background_configs.json").write_bytes(args.background_config.read_bytes())
    print(f"EXPERIMENT {exp}", flush=True)
    bng = BeamNGpy(args.host, args.port)
    bng.open(launch=False)
    try:
        bng.control.queue_lua_command(
            "settings.setValue('fpsLimit',60);settings.setValue('fpsLimitEnabled',true);settings.setValue('fpsLimitBackgroundEnabled',false)",
            response=True,
        )
        validation_report_path = exp / "validation_report.json"
        if not args.resume:
            validation = collect_trial(
                bng, exp / "validation", "validation", args.seed - 1, backgrounds,
                args.validation_duration, args.ai_aggression, validation=True,
                safe_sequential=args.safe_sequential,
            )
            validation_report = json.loads((exp / "validation/validation_report.json").read_text())
            dump(validation_report_path, validation_report)
            if validation.get("status") != "complete":
                config.update(status="validation_failed", validation_run="validation")
                dump(exp / "experiment_config.json", config)
                print("VALIDATION FAILED: stopping before the three data trials", flush=True)
                return 1
        validation_report = json.loads(validation_report_path.read_text(encoding="utf-8"))
        if validation_report["measured_state_hz"] is None or abs(validation_report["measured_state_hz"] - SIM_HZ) > 0.1:
            config.update(status="validation_failed", reason="30 Hz state sampling was not achieved")
            dump(exp / "experiment_config.json", config)
            print("VALIDATION FAILED: 30 Hz state sampling was not achieved", flush=True)
            return 1
        config.update(status="collecting_trials", validation_status=validation_report["status"])
        dump(exp / "experiment_config.json", config)
        results = []
        for number in range(1, args.trials + 1):
            run_id = f"fresh_{number:03d}"
            folder = exp / run_id
            if folder.exists():
                old_meta = folder / "metadata.json"
                if not old_meta.exists():
                    raise RuntimeError(f"{run_id} folder exists without metadata; preserving it and stopping")
                saved = json.loads(old_meta.read_text(encoding="utf-8"))
                if saved.get("status") != "complete":
                    raise RuntimeError(f"{run_id} is not complete; preserving it and stopping")
                results.append(saved)
                write_lidar_summary(exp, results)
                continue
            result = collect_trial(
                bng, folder, run_id, args.seed + number - 1, backgrounds,
                args.duration, args.ai_aggression, safe_sequential=args.safe_sequential,
            )
            results.append(result)
            write_lidar_summary(exp, results)
            if result.get("status") != "complete":
                raise RuntimeError(f"{run_id} failed validation; stopping remaining trials")
        config.update(status="complete", successful_trials=len(results))
        dump(exp / "experiment_config.json", config)
        return 0
    except BaseException as exc:
        config.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc))
        dump(exp / "experiment_config.json", config)
        raise
    finally:
        try:
            bng.control.pause()
            bng.settings.set_deterministic(60)
            bng.control.queue_lua_command(
                "settings.setValue('fpsLimit',60);settings.setValue('fpsLimitEnabled',true);settings.setValue('fpsLimitBackgroundEnabled',false)",
                response=True,
            )
        except Exception:
            pass
        bng.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
