#!/usr/bin/env python3
"""Collect LiDAR-only emergency-braking trials with two aggressive BeamNG AI cars.

The red ego uses LiDAR returns in an ego-forward occupancy corridor to request
an emergency stop. The black car follows the red car with BeamNG's ``chase`` AI
mode and built-in vehicle avoidance enabled as a simulator-side safety guard.
Both AI speed targets are configured in km/h on the CLI and converted to m/s
for BeamNGpy. This is a rule-based demonstration, not a production detector.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import AdvancedIMU, Damage, Electrics, Lidar

from collect_sensor_crossing import ROOT, jsonable, vector3, write_json


EGO_ID = "thePlayer"
UNKNOWN_ID = "clone"
EGO_TARGET = "DR193_2"
SIM_HZ = 60
SAMPLE_HZ = 10
DURATION_S = 30.0
DEFAULT_SNAPSHOT = ROOT / "runs/sensor-crossing/scene-snapshots/west-coast-live-20261017T154736Z.json"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=25252)
    p.add_argument("--home", type=Path, default=Path(os.environ["BNG_HOME"]) if os.environ.get("BNG_HOME") else None)
    p.add_argument("--launch", action="store_true")
    p.add_argument("--restore-saved-poses", type=Path, default=DEFAULT_SNAPSHOT)
    p.add_argument("--ego-id", default=EGO_ID)
    p.add_argument("--unknown-id", default=UNKNOWN_ID)
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--seed", type=int, default=41790)
    p.add_argument("--ego-speed-kmh", type=float, default=35.0)
    p.add_argument("--unknown-speed-kmh", type=float, default=50.0)
    p.add_argument("--aggression", type=float, default=1.0)
    p.add_argument("--duration", type=float, default=DURATION_S)
    p.add_argument("--sample-hz", type=int, default=SAMPLE_HZ)
    p.add_argument("--deceleration-mps2", type=float, default=5.5,
                   help="assumed braking deceleration for the conservative LiDAR trigger")
    p.add_argument("--reaction-time-s", type=float, default=0.3)
    p.add_argument("--margin-m", type=float, default=5.0)
    return p


def attach_lidar_ego_motion(bng: BeamNGpy, ego: Any, run_tag: str, sample_hz: int) -> dict[str, Any]:
    electrics_name = f"lidar_brake_{run_tag}_electrics"
    ego.sensors.attach(electrics_name, Electrics())
    lidar = Lidar(
        f"lidar_brake_{run_tag}_lidar", bng, vehicle=ego,
        requested_update_time=1 / sample_hz,
        pos=(0.0, 0.0, 1.8), vertical_resolution=32, vertical_angle=26.9,
        max_distance=100.0, density=25, is_360_mode=True, is_rotate_mode=False,
        is_using_shared_memory=True, is_visualised=False, is_annotated=False,
    )
    imu = AdvancedIMU(
        f"lidar_brake_{run_tag}_imu", bng, vehicle=ego,
        gfx_update_time=1 / sample_hz, physics_update_time=1 / SIM_HZ,
        pos=(0.0, 0.0, 1.0), smoother_strength=0.0,
        is_send_immediately=False, is_using_gravity=True, is_visualised=False,
    )
    return {"lidar": lidar, "imu": imu, "electrics_name": electrics_name}


def find_forward_occupied_range(
    points: np.ndarray,
    state: dict[str, Any],
    *,
    corridor_half_width_m: float = 1.8,
    minimum_points: int = 4,
) -> tuple[float | None, int]:
    """Return nearest LiDAR return in a conservative ego-forward corridor.

    BeamNG's current point-cloud output is world-frame. Transform each return
    by the ego pose; ignore returns below the vehicle body to reject road hits.
    This intentionally reports occupied path, not semantic object identity.
    """
    points = np.asarray(points, dtype=np.float32).reshape((-1, 3))
    if len(points) == 0:
        return None, 0
    pos = np.asarray(state.get("pos", ()), dtype=np.float64)
    direction = np.asarray(state.get("dir", ()), dtype=np.float64)
    if pos.size < 3 or direction.size < 2:
        return None, 0
    forward = direction[:2]
    norm = float(np.linalg.norm(forward))
    if not np.isfinite(norm) or norm < 1e-6:
        return None, 0
    forward /= norm
    lateral = np.asarray((-forward[1], forward[0]))
    # The LiDAR is 1.8 m above vehicle origin; use world-up for its origin.
    origin = pos[:3].copy()
    origin[2] += 1.8
    rel = points.astype(np.float64, copy=False) - origin
    forward_m = rel[:, 0] * forward[0] + rel[:, 1] * forward[1]
    lateral_m = rel[:, 0] * lateral[0] + rel[:, 1] * lateral[1]
    height_m = rel[:, 2]
    mask = (
        # Ignore the ego car's own hood/bumper, which the roof-mounted sensor
        # can see at very short range.
        (forward_m > 3.0) & (forward_m < 100.0)
        & (np.abs(lateral_m) < corridor_half_width_m)
        & (height_m > -1.55) & (height_m < 0.8)
    )
    ranges = forward_m[mask]
    if len(ranges) < minimum_points:
        return None, int(len(ranges))
    return float(np.min(ranges)), int(len(ranges))


def braking_threshold_m(
    ego_speed_mps: float,
    closing_speed_mps: float,
    *,
    deceleration_mps2: float,
    reaction_time_s: float,
    margin_m: float,
) -> float:
    """Conservative gap for ego stop plus motion of an approaching obstacle."""
    v = max(0.0, ego_speed_mps)
    closing = max(v, closing_speed_mps)
    other_speed = max(0.0, closing - v)
    stop_time = v / max(0.1, deceleration_mps2)
    return (closing * reaction_time_s + v * v / (2 * max(0.1, deceleration_mps2))
            + other_speed * stop_time + margin_m)


def restore_snapshot_if_at_menu(bng: BeamNGpy, args: argparse.Namespace) -> str:
    map_name = str(bng.control.queue_lua_command("return getMissionFilename()", response=True))
    if map_name:
        return map_name
    snap = json.loads(args.restore_saved_poses.expanduser().read_text(encoding="utf-8"))
    if snap.get("map") != "/levels/west_coast_usa/main.level.json":
        raise RuntimeError(f"Saved-pose snapshot is not West Coast USA: {snap.get('map')!r}")
    states = snap["vehicles"]
    scenario = Scenario(
        "west_coast_usa", f"lidar_braking_{uuid.uuid4().hex[:10]}",
        human_name="LiDAR Aggressive Approach and Stop",
        description="Red 35 km/h and black 50 km/h AI with LiDAR-triggered braking.",
    )
    for vid, paint, plate in ((args.ego_id, (0.9, 0.03, 0.03, 1.0), "EGO"),
                              (args.unknown_id, (0.03, 0.03, 0.03, 1.0), "UNKNOWN")):
        saved = states[vid]
        scenario.add_vehicle(
            Vehicle(vid, model=saved["model"], license=plate, color=paint),
            pos=saved["state"]["pos"], rot_quat=saved["state"]["rotation"], safe_spawn=False,
        )
    scenario.make(bng)
    bng.load_scenario(scenario, connect_player_vehicle=True, connect_existing_vehicles=True)
    bng.start_scenario()
    bng.control.pause()
    return str(bng.control.queue_lua_command("return getMissionFilename()", response=True))


def place_vehicles_at_snapshot(bng: BeamNGpy, vehicles: dict[str, Any], snapshot_path: Path) -> dict[str, Any]:
    snapshot = json.loads(snapshot_path.expanduser().read_text(encoding="utf-8"))
    saved = snapshot.get("vehicles", {})
    for vid, vehicle in vehicles.items():
        if vid not in saved:
            raise RuntimeError(f"Saved-pose snapshot does not contain {vid!r}")
        if vehicle.model != saved[vid].get("model"):
            raise RuntimeError(f"{vid!r} model mismatch: loaded {vehicle.model}, saved {saved[vid].get('model')}")
        state = saved[vid]["state"]
        if not vehicle.teleport(state["pos"], rot_quat=state["rotation"], reset=True):
            raise RuntimeError(f"Could not place {vid!r} at the saved start pose")
    bng.control.step(1)
    for vehicle in vehicles.values():
        vehicle.sensors.poll("state")
    return {vid: jsonable(v.state) for vid, v in vehicles.items()}


def assess_start_geometry(states: dict[str, Any], ego_id: str, unknown_id: str) -> dict[str, Any]:
    ego, unknown = states[ego_id], states[unknown_id]
    epos = np.asarray(ego["pos"], dtype=float)
    upos = np.asarray(unknown["pos"], dtype=float)
    edir = np.asarray(ego["dir"], dtype=float)[:2]
    udir = np.asarray(unknown["dir"], dtype=float)[:2]
    edir /= max(1e-9, np.linalg.norm(edir))
    udir /= max(1e-9, np.linalg.norm(udir))
    dot = float(np.clip(np.dot(edir, udir), -1.0, 1.0))
    oriented = math.degrees(math.acos(dot))
    unoriented = min(oriented, 180.0 - oriented)
    delta = upos[:2] - epos[:2]
    return {
        "start_center_distance_m": float(np.linalg.norm(delta)),
        "heading_angle_deg": oriented,
        "unoriented_path_angle_deg": unoriented,
        "verified_90_degree_approach": abs(unoriented - 90.0) <= 10.0,
    }


def main() -> int:
    args = parser().parse_args()
    if args.trials < 1 or args.duration <= 0 or args.sample_hz < 1 or SIM_HZ % args.sample_hz:
        raise SystemExit("trials/duration/sample rate must be positive; sample-hz must divide 60")
    if not 0 < args.ego_speed_kmh <= 50 or not 0 < args.unknown_speed_kmh <= 60:
        raise SystemExit("ego speed must be in (0, 50] km/h and unknown speed in (0, 60] km/h")
    if not 0 <= args.aggression <= 1:
        raise SystemExit("--aggression must be in [0, 1]")
    if args.deceleration_mps2 <= 0 or args.reaction_time_s < 0 or args.margin_m < 0:
        raise SystemExit("braking parameters must be positive (reaction/margin may be zero)")

    out = ROOT / "runs" / "sensor-crossing" / f"lidar-brake-{uuid.uuid4().hex[:12]}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "trials").mkdir()
    (out / "ground_truth").mkdir()
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    run_tag = out.name[-8:]
    bng = BeamNGpy(args.host, args.port, home=str(args.home) if args.home else None)
    sensors: dict[str, Any] = {}
    vehicles: dict[str, Any] = {}
    opened = False
    metadata: dict[str, Any] = {
        "status": "connecting",
        "scenario": "west-coast-lidar-occupancy-emergency-stop",
        "mode": "beamng-ai-aggression-with-lidar-braking-rule",
        "trial_count": args.trials,
        "duration_seconds": args.duration,
        "sample_hz": args.sample_hz,
        "simulation_hz": SIM_HZ,
        "beamngpy_version": importlib.metadata.version("beamngpy"),
        "script_sha256": script_hash,
        "ego_target_speed_kmh": args.ego_speed_kmh,
        "unknown_target_speed_kmh": args.unknown_speed_kmh,
        "ego_beamng_ai_speed_api_mps": args.ego_speed_kmh / 3.6,
        "unknown_beamng_ai_speed_api_mps": args.unknown_speed_kmh / 3.6,
        "beamng_ai_aggression": args.aggression,
        "ego_vehicle": args.ego_id,
        "unknown_vehicle": args.unknown_id,
        "unknown_ai_mode": "chase",
        "unknown_ai_avoid_cars": False,
        "initial_pose_snapshot": str(args.restore_saved_poses),
        "perception_inputs": ["ego_360_lidar"],
        "ego_motion_auxiliary_inputs": ["ego_wheel_speed", "ego_imu"],
        "lidar_stop_rule": {
            "type": "world-point-forward-corridor-occupancy",
            "corridor_half_width_m": 1.8,
            "minimum_points": 1,
            "assumed_deceleration_mps2": args.deceleration_mps2,
            "reaction_time_s": args.reaction_time_s,
            "margin_m": args.margin_m,
            "clear_frames_to_resume": 10,
            "resume_hysteresis_m": 8.0,
        },
        "ground_truth_path": "ground_truth/",
        "rust_server_connected": False,
        "limitations": [
            "LiDAR stop logic detects occupied forward-corridor returns; it is not a trained object detector or tracker.",
            "Assumed braking deceleration and sensor/controller latency are not calibrated; stopping distance is a demonstration estimate.",
            "Unknown car uses BeamNG chase AI with its built-in avoid-cars guard; this is separate from the red ego LiDAR stop rule.",
            "The saved pose snapshot is nearly collinear and is not a verified 90-degree intersection.",
            "A visual route preflight is still required; no controller outcome is inferred from simulator ground-truth inputs.",
        ],
        "trials": [],
    }
    write_json(out / "metadata.json", metadata)
    Path(out / "collector_source.py").write_bytes(Path(__file__).read_bytes())
    print(f"OUTPUT {out}", flush=True)

    try:
        if args.launch and not args.home:
            raise RuntimeError("--launch requires --home or BNG_HOME")
        bng.open(launch=args.launch)
        opened = True
        bng.control.pause()
        bng.settings.set_deterministic(SIM_HZ)
        map_name = restore_snapshot_if_at_menu(bng, args)
        if "west_coast_usa" not in map_name.lower():
            raise RuntimeError(f"Expected West Coast USA, BeamNG reports {map_name!r}")
        current = bng.vehicles.get_current()
        if args.ego_id not in current or args.unknown_id not in current:
            raise RuntimeError(f"Need loaded {args.ego_id!r} and {args.unknown_id!r}; found {sorted(current)}")
        ego, unknown = current[args.ego_id], current[args.unknown_id]
        ego.connect(bng)
        unknown.connect(bng)
        vehicles = {args.ego_id: ego, args.unknown_id: unknown}
        starts = place_vehicles_at_snapshot(bng, vehicles, args.restore_saved_poses)
        for vehicle in vehicles.values():
            vehicle.sensors.attach(f"lidar_brake_{run_tag}_damage", Damage())
            vehicle.sensors.poll("state")
        metadata["start_geometry"] = assess_start_geometry(starts, args.ego_id, args.unknown_id)
        write_json(out / "ground_truth" / "initial_vehicle_states.json", starts)
        (out / "ground_truth" / "vehicle_configs.json").write_text(
            json.dumps(bng.vehicles.get_current_info(), indent=2, sort_keys=True) + "\n"
        )
        sensors = attach_lidar_ego_motion(bng, ego, run_tag, args.sample_hz)
        metadata.update(status="ready", map=map_name, ego_model=ego.model, unknown_model=unknown.model)
        write_json(out / "metadata.json", metadata)

        ego_speed_mps = args.ego_speed_kmh / 3.6
        unknown_speed_mps = args.unknown_speed_kmh / 3.6
        trial_offsets = [0.0, 0.8, 0.4]
        rng = random.Random(args.seed)
        rng.shuffle(trial_offsets)
        start_states = starts
        for trial_num in range(1, args.trials + 1):
            spec = {"trial": trial_num,
                    "ego_speed_kmh": args.ego_speed_kmh,
                    "ego_speed_mps": ego_speed_mps,
                    "unknown_speed_kmh": args.unknown_speed_kmh,
                    "unknown_speed_mps": unknown_speed_mps,
                    "aggression": args.aggression,
                    "unknown_start_delay_s": trial_offsets[(trial_num - 1) % len(trial_offsets)]}
            trial_dir = out / "trials" / f"trial-{trial_num:02d}"
            gt_dir = out / "ground_truth" / f"trial-{trial_num:02d}"
            trial_dir.mkdir()
            (trial_dir / "lidar").mkdir()
            gt_dir.mkdir()
            for v in vehicles.values():
                v.ai.set_mode("disabled")
                v.control(throttle=0, brake=1, parkingbrake=1)
            for vid, v in vehicles.items():
                state = start_states[vid]
                if not v.teleport(state["pos"], rot_quat=state["rotation"], reset=True):
                    raise RuntimeError(f"Failed to restore {vid} to its trial start")
            # Refresh physics and let LiDAR publish a non-empty stationary scan.
            for _ in range(max(12, SIM_HZ // args.sample_hz * 2)):
                bng.control.step(1)
                ego.sensors.poll("state")
                unknown.sensors.poll("state")

            ego.ai.drive_in_lane(True)
            ego.ai.set_avoid_cars(False)  # red braking decision is made by its LiDAR rule
            ego.ai.set_aggression(args.aggression)
            ego.ai.set_speed(ego_speed_mps, mode="set")
            ego.ai.set_waypoint(EGO_TARGET)
            ego.control(throttle=0, brake=0, parkingbrake=0)
            trial_meta = {**spec, "status": "running"}
            metadata["trials"].append(trial_meta)
            write_json(out / "metadata.json", metadata)
            print(f"START trial={trial_num} ego={args.ego_speed_kmh:g}km/h unknown={args.unknown_speed_kmh:g}km/h aggression={args.aggression:g}", flush=True)

            sensor_index = 0
            gt_rows: list[dict[str, Any]] = []
            previous_range: float | None = None
            previous_time: float | None = None
            stopped_for_lidar = False
            clear_frames = 0
            event_stream = (trial_dir / "events.jsonl").open("w", encoding="utf-8")
            index_path = trial_dir / "sensor_index.jsonl"
            index_path.touch()
            start_sim_time: float | None = None
            ticks_per_sample = SIM_HZ // args.sample_hz
            total_ticks = round(args.duration * SIM_HZ)
            try:
                for sample_tick in range(total_ticks // ticks_per_sample + 1):
                    if sample_tick:
                        for _ in range(ticks_per_sample):
                            # BeamNG's per-vehicle control input can be replaced
                            # by AI on the next physics tick. Hold full braking
                            # throughout every tick while the LiDAR stop is active.
                            if stopped_for_lidar:
                                ego.control(throttle=0, brake=1, parkingbrake=0)
                            bng.control.step(1)
                    ego.sensors.poll("state")
                    unknown.sensors.poll("state")
                    now = float(ego.state["time"])
                    if start_sim_time is None:
                        start_sim_time = now
                    elapsed = now - start_sim_time
                    if elapsed >= trial_meta["unknown_start_delay_s"] and not trial_meta.get("unknown_started"):
                        unknown.ai.drive_in_lane(True)
                        # The user requested a deliberate high-speed pursuit;
                        # leave the simulator's avoid-cars guard disabled.
                        unknown.ai.set_avoid_cars(False)
                        unknown.ai.set_aggression(args.aggression)
                        unknown.ai.set_speed(unknown_speed_mps, mode="set")
                        unknown.ai.set_target(args.ego_id, mode="chase")
                        unknown.control(throttle=0, brake=0, parkingbrake=0)
                        trial_meta["unknown_started"] = True

                    sensor_data, points = capture_frame(sensors, ego, trial_dir, sensor_index)
                    wheel_speed = sensor_data.get("wheel_speed_mps")
                    ego_speed = abs(float(wheel_speed)) if wheel_speed is not None else math.sqrt(sum(float(x)**2 for x in ego.state.get("vel", (0, 0, 0))))
                    nearest, occupied_points = find_forward_occupied_range(
                        points, ego.state, minimum_points=1,
                    )
                    lidar_available = len(points) > 0
                    closing = ego_speed
                    if nearest is not None and previous_range is not None and previous_time is not None and now > previous_time:
                        closing = max(ego_speed, min(80.0, (previous_range - nearest) / (now - previous_time)))
                    threshold = braking_threshold_m(
                        ego_speed, closing, deceleration_mps2=args.deceleration_mps2,
                        reaction_time_s=args.reaction_time_s, margin_m=args.margin_m,
                    )
                    # Missing/empty scans are sensor faults, never evidence that
                    # the path is clear. Treat them as a stop and do not resume
                    # until a non-empty scan repeatedly confirms clearance.
                    hazard = (not lidar_available) or (nearest is not None and nearest <= threshold)
                    event = None
                    if hazard and not stopped_for_lidar:
                        ego.ai.set_mode("disabled")
                        ego.control(throttle=0, brake=1, parkingbrake=0)
                        stopped_for_lidar = True
                        clear_frames = 0
                        event = "lidar_sensor_unavailable_stop" if not lidar_available else "lidar_emergency_brake"
                    elif stopped_for_lidar:
                        if lidar_available and (nearest is None or nearest > threshold + 8.0):
                            clear_frames += 1
                        else:
                            clear_frames = 0
                        if clear_frames >= 10:
                            ego.ai.set_aggression(args.aggression)
                            ego.ai.set_speed(ego_speed_mps, mode="set")
                            ego.ai.set_waypoint(EGO_TARGET)
                            ego.control(throttle=0, brake=0, parkingbrake=0)
                            stopped_for_lidar = False
                            clear_frames = 0
                            event = "lidar_path_clear_resume"

                    row = {
                        "frame": sensor_index, "sim_time_s": now, "elapsed_s": elapsed,
                        **sensor_data,
                        "lidar_forward_occupied_range_m": nearest,
                        "lidar_forward_occupied_points": occupied_points,
                        "lidar_available": lidar_available,
                        "estimated_closing_speed_mps": closing if nearest is not None else None,
                        "braking_threshold_m": threshold,
                        "lidar_stop_active": stopped_for_lidar,
                        "ego_speed_kmh": ego_speed * 3.6,
                        "unknown_ai_started": bool(trial_meta.get("unknown_started")),
                    }
                    with index_path.open("a", encoding="utf-8") as index:
                        index.write(json.dumps(jsonable(row), sort_keys=True) + "\n")
                    if event:
                        event_stream.write(json.dumps({"frame": sensor_index, "sim_time_s": now, "event": event,
                                                       "range_m": nearest, "threshold_m": threshold}) + "\n")
                        event_stream.flush()
                        print(f"EVENT trial={trial_num} frame={sensor_index} {event} range={nearest}", flush=True)

                    for role, v in (("ego", ego), ("unknown", unknown)):
                        v.sensors.poll(f"lidar_brake_{run_tag}_damage")
                        state = v.state
                        pos, vel = vector3(state, "pos"), vector3(state, "vel")
                        gt_rows.append({
                            "frame": sensor_index, "sim_time_s": now, "elapsed_s": elapsed,
                            "role": role, "simulator_vehicle_id": v.vid, "model": v.model,
                            "x_m": pos[0], "y_m": pos[1], "z_m": pos[2],
                            "vx_mps": vel[0], "vy_mps": vel[1], "vz_mps": vel[2],
                            "speed_mps": math.sqrt(sum(x*x for x in vel)) if all(map(math.isfinite, vel)) else None,
                            "damage_ground_truth": v.sensors[f"lidar_brake_{run_tag}_damage"].get("damage"),
                        })
                    previous_range, previous_time = nearest, now
                    sensor_index += 1
            finally:
                event_stream.close()

            with (gt_dir / "vehicle_state.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(gt_rows[0]) if gt_rows else [])
                writer.writeheader()
                writer.writerows(gt_rows)
            for v in vehicles.values():
                v.ai.set_mode("disabled")
                v.control(throttle=0, brake=1, parkingbrake=1)
            trial_meta.update(status="complete", sensor_frames=sensor_index,
                              sensor_index=f"trials/trial-{trial_num:02d}/sensor_index.jsonl",
                              events=f"trials/trial-{trial_num:02d}/events.jsonl",
                              ground_truth=f"ground_truth/trial-{trial_num:02d}/vehicle_state.csv")
            write_json(out / "metadata.json", metadata)
            print(f"COMPLETE trial={trial_num} sensor_frames={sensor_index}", flush=True)

        metadata["status"] = "complete"
        write_json(out / "metadata.json", metadata)
        return 0
    except BaseException as exc:
        metadata.update(status="failed", error=repr(exc))
        write_json(out / "metadata.json", metadata)
        raise
    finally:
        for name in ("lidar", "imu"):
            if name in sensors:
                try:
                    sensors[name].remove()
                except Exception:
                    pass
        if opened:
            for v in vehicles.values():
                try:
                    v.ai.set_mode("disabled")
                    v.control(throttle=0, brake=1, parkingbrake=1)
                except Exception:
                    pass
            try:
                bng.control.pause()
            except Exception:
                pass
            bng.disconnect()


def capture_frame(sensors: dict[str, Any], ego: Any, trial_dir: Path, index: int) -> tuple[dict[str, Any], np.ndarray]:
    stem = f"frame_{index:05d}"
    cloud = sensors["lidar"].poll().get("pointCloud")
    if cloud is None:
        cloud = np.empty((0, 3), dtype=np.float32)
    cloud = np.asarray(cloud, dtype=np.float32).reshape((-1, 3))
    relative = Path("lidar") / f"{stem}.npz"
    np.savez_compressed(trial_dir / relative, points=cloud)
    imu = sensors["imu"].poll()
    ego.sensors.poll(sensors["electrics_name"])
    electrics = ego.sensors[sensors["electrics_name"]]
    return ({
        "lidar_file": relative.as_posix(),
        "lidar_points": int(len(cloud)),
        "wheel_speed_mps": electrics.get("wheelspeed"),
        "ego_throttle": electrics.get("throttle"),
        "ego_brake": electrics.get("brake"),
        "ego_steering": electrics.get("steering"),
        "imu": jsonable(imu),
    }, cloud)


if __name__ == "__main__":
    raise SystemExit(main())
