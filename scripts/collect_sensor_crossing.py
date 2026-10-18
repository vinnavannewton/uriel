#!/usr/bin/env python3
"""Collect three LiDAR-only unknown-vehicle crossing trials on West Coast USA.

The ego vehicle's LiDAR is the only perception sensor. Ego wheel speed and IMU
are recorded as auxiliary motion inputs. Simulator state for both vehicles is
written to a separate ground_truth directory for offline scoring; it is never
sent to a controller.

The collector uses ``thePlayer`` as ego. It uses the requested/preloaded
unknown vehicle when available, or asks BeamNG traffic to create a random one.
The current West Coast waypoint setup is inherited from
collect_traffic_trials.py. No live run is started unless the operator
explicitly invokes this script.
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
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import AdvancedIMU, Damage, Electrics, Lidar


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRIALS = [
    {"ego_speed_mps": 6.0, "unknown_speed_mps": 6.0, "unknown_delay_s": 0.0},
    {"ego_speed_mps": 5.5, "unknown_speed_mps": 7.0, "unknown_delay_s": 0.8},
    {"ego_speed_mps": 7.0, "unknown_speed_mps": 5.5, "unknown_delay_s": 0.4},
]
EGO_ID = "thePlayer"
UNKNOWN_ID = "clone"
EGO_TARGET = "DR193_2"
UNKNOWN_TARGET = "DR602_5"
SIM_HZ = 60
SAMPLE_HZ = 5
DURATION_S = 30.0
SAVED_POSES = ROOT / "runs" / "sensor-crossing" / "scene-snapshots" / "west-coast-live-20261017T154736Z.json"


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(value), indent=2, sort_keys=True) + "\n")


def vector3(state: dict[str, Any], key: str) -> list[float]:
    value = state.get(key)
    if not isinstance(value, (tuple, list)) or len(value) < 3:
        return [math.nan, math.nan, math.nan]
    return [float(value[i]) for i in range(3)]


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=25252)
    parser.add_argument("--home", type=Path, default=Path(os.environ["BNG_HOME"]) if os.environ.get("BNG_HOME") else None,
                        help="BeamNG.tech installation; required with --launch")
    parser.add_argument("--launch", action="store_true", help="launch BeamNG.tech and own its API connection")
    parser.add_argument("--restore-saved-poses", type=Path,
                        help="when launched to the menu, load both cars from this saved-pose snapshot")
    parser.add_argument("--ego-id", default=EGO_ID)
    parser.add_argument("--unknown-id", default=UNKNOWN_ID)
    parser.add_argument("--trials", type=int, default=3, choices=(3,))
    parser.add_argument("--seed", type=int, default=41790)
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "sensor-crossing")
    parser.add_argument("--duration", type=float, default=DURATION_S)
    parser.add_argument("--sample-hz", type=int, default=SAMPLE_HZ, choices=(5,))
    return parser


def load_unknown_vehicle(
    bng: BeamNGpy, ego_id: str, preferred_id: str
) -> tuple[Any, str, Any, str]:
    """Choose a preloaded target or request one random BeamNG traffic car."""
    current = bng.vehicles.get_current()
    if ego_id not in current:
        raise RuntimeError(f"Ego vehicle {ego_id!r} not found; loaded vehicles: {sorted(current)}")
    if preferred_id in current and preferred_id != ego_id:
        ego, unknown = current[ego_id], current[preferred_id]
        ego.connect(bng)
        unknown.connect(bng)
        return ego, preferred_id, unknown, "preloaded_requested_id"
    candidates = [(vehicle_id, vehicle) for vehicle_id, vehicle in current.items()
                  if vehicle_id != ego_id]
    if candidates:
        vehicle_id, unknown = candidates[0]
        ego = current[ego_id]
        ego.connect(bng)
        unknown.connect(bng)
        return ego, vehicle_id, unknown, "preloaded_first_non_ego_vehicle"

    # BeamNG chooses the traffic vehicle model; the collector does not hard-code it.
    bng.traffic.spawn(max_amount=1, police_ratio=0, extra_amount=0, parked_amount=0)
    for _ in range(100):
        bng.control.pause()
        current = bng.vehicles.get_current()
        spawned = [(vehicle_id, vehicle) for vehicle_id, vehicle in current.items()
                   if vehicle_id != ego_id]
        if spawned:
            bng.traffic.stop(stop=True)
            vehicle_id, unknown = spawned[0]
            ego = current[ego_id]
            ego.connect(bng)
            unknown.connect(bng)
            return ego, vehicle_id, unknown, "beamng_random_traffic_spawn"
        for _ in range(6):
            bng.control.step(1)
        time.sleep(0.05)
    raise RuntimeError(
        "BeamNG did not load a vehicle after requesting one random traffic car. "
        "Check that traffic is enabled for this map, then retry."
    )


def attach_sensors(bng: BeamNGpy, ego: Any, sample_hz: int = SAMPLE_HZ) -> dict[str, Any]:
    ego.sensors.attach("sensor_crossing_electrics", Electrics())
    lidar = Lidar(
        "sensor_crossing_lidar", bng, vehicle=ego,
        requested_update_time=1 / sample_hz, pos=(0.0, 0.0, 1.8),
        vertical_resolution=32, vertical_angle=26.9, max_distance=100.0,
        density=25, is_360_mode=True, is_rotate_mode=False,
        is_using_shared_memory=True, is_visualised=False, is_annotated=False,
    )
    imu = AdvancedIMU(
        "sensor_crossing_imu", bng, vehicle=ego,
        gfx_update_time=1 / sample_hz, physics_update_time=1 / SIM_HZ,
        pos=(0.0, 0.0, 1.0), smoother_strength=0.0,
        is_send_immediately=False, is_using_gravity=True, is_visualised=False,
    )
    return {"lidar": lidar, "imu": imu}


def sensor_frame(sensors: dict[str, Any], ego: Any, trial_dir: Path, index: int) -> dict[str, Any]:
    stem = f"frame_{index:05d}"
    cloud = sensors["lidar"].poll().get("pointCloud")
    lidar_rel = Path("lidar") / f"{stem}.npz"
    if cloud is None:
        cloud = np.empty((0, 3), dtype=np.float32)
    lidar_path = trial_dir / lidar_rel
    lidar_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(lidar_path, points=np.asarray(cloud, dtype=np.float32))

    imu_readings = sensors["imu"].poll()
    ego.sensors.poll("sensor_crossing_electrics")
    electrics = ego.sensors["sensor_crossing_electrics"]
    # This stream contains only ego sensor data. No unknown-car simulator state
    # or identity is included in it.
    return {
        "lidar_file": lidar_rel.as_posix(),
        "lidar_points": int(len(cloud)),
        "wheel_speed_mps": electrics.get("wheelspeed"),
        "ego_throttle": electrics.get("throttle"),
        "ego_brake": electrics.get("brake"),
        "ego_steering": electrics.get("steering"),
        "imu": jsonable(imu_readings),
    }


def main() -> int:
    args = make_parser().parse_args()
    if args.duration <= 0:
        raise SystemExit("--duration must be positive")
    out = args.output.resolve() / f"run-{uuid.uuid4().hex[:12]}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "trials").mkdir()
    (out / "ground_truth").mkdir()
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rng = random.Random(args.seed)
    # Keep the crossing speeds and vary only controlled timing/speed factors.
    trial_specs = [dict(item) for item in DEFAULT_TRIALS]
    rng.shuffle(trial_specs)
    metadata: dict[str, Any] = {
        "status": "connecting",
        "scenario": "west-coast-usa-90-degree-unknown-vehicle",
        "mode": "sensor-recording-ai-route-following",
        "trial_count": args.trials,
        "seed": args.seed,
        "duration_seconds": args.duration,
        "sample_hz_requested": args.sample_hz,
        "simulation_hz": SIM_HZ,
        "beamngpy_version": importlib.metadata.version("beamngpy"),
        "script_sha256": script_hash,
        "ego_vehicle": args.ego_id,
        "unknown_vehicle_role": "unknown_to_perception",
        "route_waypoints": {"ego": EGO_TARGET, "unknown": UNKNOWN_TARGET},
        "perception_inputs": ["ego_360_lidar"],
        "ego_motion_auxiliary_inputs": ["ego_wheel_speed", "ego_imu"],
        "sensor_mounts_vehicle_local": {
            "lidar": {"pos_m": [0.0, 0.0, 1.8], "horizontal_fov_deg": 360.0},
            "imu": {"pos_m": [0.0, 0.0, 1.0]},
        },
        "excluded_from_perception_inputs": [
            "unknown_vehicle_id", "unknown_vehicle_pose", "unknown_vehicle_velocity",
            "simulator_bbox", "simulator_depth_image", "map_world_coordinates",
        ],
        "ground_truth_path": "ground_truth/",
        "rust_server_connected": False,
        "limitations": [
            "No LiDAR object detector or track estimator is included; this records raw LiDAR and ego-motion inputs.",
            "The current Rust crossing contract consumes explicit vehicle state and cannot yet consume a sensor-derived unknown track.",
            "The selected target is treated as unknown by the perception pipeline; BeamNG state is written only to the separate ground-truth stream.",
            "The selected waypoint pair requires a live visual preflight before trial execution.",
            "Point-cloud timestamps are frame-level simulator timestamps; LiDAR-to-IMU calibration and sensor skew need measured validation.",
            "Ground-truth zone labels use the approximate evaluation zone from the existing West Coast collector.",
        ],
        "trials": [],
    }
    write_json(out / "metadata.json", metadata)
    shutil.copyfile(__file__, out / "collector_source.py")
    print(f"OUTPUT {out}", flush=True)

    bng = BeamNGpy(args.host, args.port, home=str(args.home) if args.home else None)
    opened = False
    sensors: dict[str, Any] | None = None
    vehicles: dict[str, Any] = {}
    try:
        if args.launch and not args.home:
            raise RuntimeError("--launch requires --home or BNG_HOME")
        bng.open(launch=args.launch)
        opened = True
        bng.control.pause()
        bng.settings.set_deterministic(SIM_HZ)
        map_name = str(bng.control.queue_lua_command("return getMissionFilename()", response=True))
        if not map_name and args.restore_saved_poses:
            saved_snapshot = json.loads(args.restore_saved_poses.expanduser().read_text(encoding="utf-8"))
            if saved_snapshot.get("map") != "/levels/west_coast_usa/main.level.json":
                raise RuntimeError(f"Saved-pose snapshot is not West Coast USA: {saved_snapshot.get('map')!r}")
            saved_vehicles = saved_snapshot["vehicles"]
            scenario = Scenario(
                "west_coast_usa", f"sensor_crossing_{uuid.uuid4().hex[:10]}",
                human_name="Sensor Crossing Saved Pose Run",
                description="AI sensor-crossing trial initialized from saved user vehicle poses.",
            )
            scenario.add_vehicle(
                Vehicle(args.ego_id, model=saved_vehicles[args.ego_id]["model"],
                        license="EGO", color=(0.9, 0.03, 0.03, 1.0)),
                pos=saved_vehicles[args.ego_id]["state"]["pos"],
                rot_quat=saved_vehicles[args.ego_id]["state"]["rotation"], safe_spawn=False,
            )
            scenario.add_vehicle(
                Vehicle(args.unknown_id, model=saved_vehicles[args.unknown_id]["model"],
                        license="UNKNOWN", color=(0.03, 0.03, 0.03, 1.0)),
                pos=saved_vehicles[args.unknown_id]["state"]["pos"],
                rot_quat=saved_vehicles[args.unknown_id]["state"]["rotation"], safe_spawn=False,
            )
            scenario.make(bng)
            bng.load_scenario(scenario, connect_player_vehicle=True, connect_existing_vehicles=True)
            bng.start_scenario()
            bng.control.pause()
            map_name = str(bng.control.queue_lua_command("return getMissionFilename()", response=True))
            metadata["initial_scene_source"] = str(args.restore_saved_poses)
            metadata["beamng_scenario"] = scenario.name
        if "west_coast_usa" not in map_name.lower():
            raise RuntimeError(f"Expected West Coast USA, BeamNG reports {map_name!r}")
        ego, unknown_id, unknown, unknown_source = load_unknown_vehicle(
            bng, args.ego_id, args.unknown_id
        )
        vehicles = {args.ego_id: ego, unknown_id: unknown}
        for vehicle in (ego, unknown):
            vehicle.sensors.attach("sensor_crossing_damage", Damage())
            vehicle.sensors.poll("state")
        ego_start = jsonable(ego.state)
        unknown_start = jsonable(unknown.state)
        initial = {
            "ego": {"vehicle_id": args.ego_id, "model": ego.model, "state": ego_start},
            "unknown": {"vehicle_id": unknown_id, "model": unknown.model, "state": unknown_start,
                        "spawn_source": unknown_source},
        }
        write_json(out / "ground_truth" / "initial_vehicle_states.json", initial)
        (out / "ground_truth" / "initial_vehicle_configs.json").write_text(
            json.dumps(bng.vehicles.get_current_info(), indent=2, sort_keys=True) + "\n"
        )
        sensors = attach_sensors(bng, ego)
        metadata.update(status="ready", map=map_name, ego_model=ego.model,
                        unknown_vehicle_id=unknown_id, unknown_model=unknown.model,
                        unknown_spawn_source=unknown_source)
        write_json(out / "metadata.json", metadata)

        start_states = {args.ego_id: jsonable(ego.state), unknown_id: jsonable(unknown.state)}
        for trial_num, spec in enumerate(trial_specs, 1):
            trial_dir = out / "trials" / f"trial-{trial_num:02d}"
            trial_dir.mkdir()
            gt_dir = out / "ground_truth" / f"trial-{trial_num:02d}"
            gt_dir.mkdir()
            ego.ai.set_mode("disabled")
            unknown.ai.set_mode("disabled")
            for vehicle in (ego, unknown):
                vehicle.control(throttle=0, brake=1, parkingbrake=1)
            for vehicle_id, vehicle in ((args.ego_id, ego), (unknown_id, unknown)):
                state = start_states[vehicle_id]
                if not vehicle.teleport(state["pos"], rot_quat=state["rotation"], reset=True):
                    raise RuntimeError(f"Failed to restore {vehicle_id} to its captured starting pose")
            # Teleport(reset=True) restores the captured start state. One
            # physics step is enough to refresh state sensors; a 60-step batch
            # can stall the simulator during sensor-heavy scene startup.
            bng.control.step(1)
            ego.sensors.poll("state")
            unknown.sensors.poll("state")

            ego.ai.drive_in_lane(True)
            ego.ai.set_waypoint(EGO_TARGET)
            ego.ai.set_speed(spec["ego_speed_mps"], mode="limit")
            ego.control(throttle=0, brake=0, parkingbrake=0)

            trial_meta = {"trial": trial_num, **spec, "status": "running"}
            metadata["trials"].append(trial_meta)
            write_json(out / "metadata.json", metadata)
            print(f"START trial={trial_num} settings={spec}", flush=True)
            start_sim_time: float | None = None
            unknown_started = False
            sensor_index = 0
            sensor_rows: list[dict[str, Any]] = []
            ground_truth_rows: list[dict[str, Any]] = []
            step_count = round(args.duration * SIM_HZ)
            sample_stride = SIM_HZ // args.sample_hz
            sensor_index_path = trial_dir / "sensor_index.jsonl"
            sensor_index_path.touch()
            for sample_tick in range(step_count // sample_stride + 1):
                if sample_tick:
                    # BeamNG.tech 0.39.4 disconnects on larger manual-step
                    # batches in this sensor-heavy scene. Advance one frame
                    # per acknowledged API call to keep the reset/sample path
                    # bounded and observable.
                    for _ in range(sample_stride):
                        bng.control.step(1)
                ego.sensors.poll("state")
                unknown.sensors.poll("state")
                now = float(ego.state["time"])
                if start_sim_time is None:
                    start_sim_time = now
                elapsed = now - start_sim_time
                if not unknown_started and elapsed >= spec["unknown_delay_s"]:
                    unknown.ai.drive_in_lane(True)
                    unknown.ai.set_waypoint(UNKNOWN_TARGET)
                    unknown.ai.set_speed(spec["unknown_speed_mps"], mode="limit")
                    unknown.control(throttle=0, brake=0, parkingbrake=0)
                    unknown_started = True
                sensor_data = sensor_frame(sensors, ego, trial_dir, sensor_index)
                sensor_row = {
                    "frame": sensor_index,
                    "sim_time_s": now,
                    "elapsed_s": elapsed,
                    **sensor_data,
                }
                sensor_rows.append(sensor_row)
                with sensor_index_path.open("a", encoding="utf-8") as index_stream:
                    index_stream.write(json.dumps(jsonable(sensor_row), sort_keys=True) + "\n")
                # These exact pose/velocity fields are evaluation-only.
                for label, vehicle in (("ego", ego), ("unknown", unknown)):
                    state = vehicle.state
                    vehicle.sensors.poll("sensor_crossing_damage")
                    pos, vel = vector3(state, "pos"), vector3(state, "vel")
                    ground_truth_rows.append({
                        "frame": sensor_index,
                        "sim_time_s": now,
                        "elapsed_s": elapsed,
                        "role": label,
                        "simulator_vehicle_id": vehicle.vid,
                        "model": vehicle.model,
                        "x_m": pos[0], "y_m": pos[1], "z_m": pos[2],
                        "vx_mps": vel[0], "vy_mps": vel[1], "vz_mps": vel[2],
                        "speed_mps": math.sqrt(sum(c*c for c in vel)) if all(map(math.isfinite, vel)) else None,
                        "damage_ground_truth": vehicle.sensors["sensor_crossing_damage"].get("damage"),
                    })
                sensor_index += 1

            with (gt_dir / "vehicle_state.csv").open("w", newline="", encoding="utf-8") as stream:
                fields = list(ground_truth_rows[0]) if ground_truth_rows else [
                    "frame", "sim_time_s", "elapsed_s", "role", "simulator_vehicle_id", "model",
                    "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps", "speed_mps",
                ]
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(ground_truth_rows)

            for vehicle in (ego, unknown):
                vehicle.ai.set_mode("disabled")
                vehicle.control(throttle=0, brake=1, parkingbrake=1)
            trial_meta.update(status="complete", sensor_frames=sensor_index,
                              ground_truth_rows=len(ground_truth_rows),
                              sensor_index=f"trials/trial-{trial_num:02d}/sensor_index.jsonl",
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
        if sensors:
            for name in ("lidar", "imu"):
                try:
                    sensors[name].remove()
                except Exception:
                    pass
        if opened:
            try:
                for vehicle in vehicles.values():
                    try:
                        vehicle.ai.set_mode("disabled")
                        vehicle.control(throttle=0, brake=1, parkingbrake=1)
                    except Exception:
                        pass
                bng.control.pause()
            finally:
                bng.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
