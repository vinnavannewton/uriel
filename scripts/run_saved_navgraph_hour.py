#!/usr/bin/env python3
"""Collect LiDAR and telemetry on both saved West Coast route vehicles.

The two saved vehicles repeatedly travel from their saved graph start nodes to
their saved end nodes. BeamNG's native waypoint AI drives both cars with
avoid-cars enabled. LiDAR is the only perception sensor; ego wheel speed and
IMU are auxiliary. Simulator vehicle states are kept in a separate ground-
truth stream for offline labels and must not be treated as perception input.
"""

from __future__ import annotations

import argparse
import json
import math
import signal
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from beamngpy import BeamNGpy
from beamngpy.sensors import AdvancedIMU, Damage, Electrics, Lidar

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "scenarios/west_coast_red_black_20261018"
DEFAULT_SPEED_PROFILES = ((20.0, 30.0), (30.0, 40.0), (40.0, 50.0))
SIM_HZ = 60


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def parse_profiles(value: str) -> tuple[tuple[float, float], ...]:
    try:
        profiles = tuple(
            tuple(float(speed) for speed in pair.split(","))
            for pair in value.split(";")
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "use red,black pairs separated by semicolons, e.g. 20,30;30,40;40,50"
        ) from exc
    if not profiles or any(len(pair) != 2 for pair in profiles):
        raise argparse.ArgumentTypeError("each speed profile must contain red,black")
    if any(speed <= 0 or speed > 80 for pair in profiles for speed in pair):
        raise argparse.ArgumentTypeError("target speeds must be within (0, 80] km/h")
    return profiles  # type: ignore[return-value]


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=SCENE)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=25252)
    parser.add_argument("--hours", type=float, default=1.0,
                        help="total driving simulation time to record (default: 1)")
    parser.add_argument("--speed-factor", type=int, default=1,
                        help="BeamNG deterministic simulation speed factor (default: 1)")
    parser.add_argument("--traffic-cars", type=int, choices=range(0, 9), default=0,
                        help="number of background AI traffic vehicles (0-8; medium is 6)")
    parser.add_argument("--continue-after-damage", action="store_true",
                        help="record a damage-triggered leg, reset at the next start, and continue")
    parser.add_argument("--lidar-hz", type=float, default=1.0,
                        help="LiDAR/IMU/wheel-speed sample rate (default: 1 Hz)")
    parser.add_argument("--state-hz", type=float, default=10.0,
                        help="ground-truth state rate for both vehicles (default: 10 Hz)")
    parser.add_argument("--speed-profiles-kmh", type=parse_profiles,
                        default=DEFAULT_SPEED_PROFILES,
                        help="cycling red,black target speeds, e.g. '20,30;30,40;40,50'")
    parser.add_argument("--max-leg-seconds", type=float, default=60.0,
                        help="max simulation seconds for a start-to-end leg (default: 60)")
    parser.add_argument("--damage-limit", type=float, default=1.0,
                        help="stop the run if per-leg damage delta exceeds this")
    return parser


def attach_run_sensors(bng: BeamNGpy, red: Any, black: Any, run_id: str,
                       lidar_hz: float) -> dict[str, Any]:
    # Unique names avoid collisions with sensors left in the live vehicle from
    # earlier user runs. All are detached in finally.
    names = {
        "electrics": f"hour_electrics_{run_id}",
        "lidar_red": f"hour_lidar_red_{run_id}",
        "lidar_black": f"hour_lidar_black_{run_id}",
        "imu": f"hour_imu_{run_id}",
        "damage_red": f"hour_damage_red_{run_id}",
        "damage_black": f"hour_damage_black_{run_id}",
    }
    red.sensors.attach(names["electrics"], Electrics())
    lidar_options = {
        "requested_update_time": 1 / lidar_hz, "pos": (0.0, 0.0, 1.8),
        "vertical_resolution": 32, "vertical_angle": 26.9,
        "max_distance": 100.0, "density": 25, "is_360_mode": True,
        "is_rotate_mode": False, "is_using_shared_memory": True,
        "is_visualised": False, "is_annotated": False,
    }
    lidar_red = Lidar(names["lidar_red"], bng, vehicle=red, **lidar_options)
    lidar_black = Lidar(names["lidar_black"], bng, vehicle=black, **lidar_options)
    imu = AdvancedIMU(names["imu"], bng, vehicle=red,
                      gfx_update_time=1 / lidar_hz,
                      physics_update_time=1 / SIM_HZ,
                      pos=(0.0, 0.0, 1.0), smoother_strength=0.0,
                      is_send_immediately=False, is_using_gravity=True,
                      is_visualised=False)
    return {"electrics_name": names["electrics"], "lidar_red": lidar_red,
            "lidar_black": lidar_black, "imu": imu,
            "lidar_red_name": names["lidar_red"],
            "lidar_black_name": names["lidar_black"], "imu_name": names["imu"]}


def save_sensor_frame(sensors: dict[str, Any], vehicles: dict[str, Any], out: Path,
                      index: int) -> dict[str, Any]:
    lidar_files: dict[str, str] = {}
    lidar_points: dict[str, int] = {}
    for vid, sensor_key, color in (("thePlayer", "lidar_red", "red"),
                                   ("clone0", "lidar_black", "black")):
        cloud = sensors[sensor_key].poll().get("pointCloud")
        if cloud is None:
            cloud = np.empty((0, 3), dtype=np.float32)
        lidar_rel = Path("lidar") / color / f"frame_{index:06d}.npz"
        np.savez_compressed(out / lidar_rel, points=np.asarray(cloud, dtype=np.float32))
        lidar_files[vid] = lidar_rel.as_posix()
        lidar_points[vid] = int(len(cloud))
    imu = sensors["imu"].poll()
    electrics_name = sensors["electrics_name"]
    red = vehicles["thePlayer"]
    red.sensors.poll(electrics_name)
    electrics = red.sensors[electrics_name]
    return {
        "lidar_files": lidar_files,
        "lidar_points": lidar_points,
        "wheel_speed_mps": electrics.get("wheelspeed"),
        "ego_throttle": electrics.get("throttle"),
        "ego_brake": electrics.get("brake"),
        "ego_steering": electrics.get("steering"),
        "imu": jsonable(imu),
    }


def read_state(vehicle: Any, damage_name: str) -> tuple[dict[str, Any], float]:
    vehicle.sensors.poll("state", damage_name)
    return dict(vehicle.state), float(vehicle.sensors[damage_name].get("damage", 0.0))


def set_route(vehicle: Any, route: dict[str, Any], session: dict[str, Any],
              target_kmh: float) -> None:
    spline = next(item for item in session["splines"]
                  if item["id"] == route["spline_id"])
    nodes = route["graph_nodes"]
    vehicle.control(throttle=0, brake=0, parkingbrake=0)
    vehicle.ai.drive_using_waypoints(
        nodes,
        wp_speeds={node: target_kmh / 3.6 for node in nodes},
        no_of_laps=spline["numLaps"],
        route_speed=target_kmh / 3.6,
        route_speed_mode="limit",
        drive_in_lane=spline["isDriveInLane"],
        aggression=spline["aggression"],
        avoid_cars=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.hours <= 0 or args.lidar_hz <= 0 or args.state_hz <= 0:
        raise SystemExit("--hours, --lidar-hz and --state-hz must be positive")
    if args.speed_factor < 1:
        raise SystemExit("--speed-factor must be at least 1")
    if args.max_leg_seconds <= 0 or args.damage_limit <= 0:
        raise SystemExit("--max-leg-seconds and --damage-limit must be positive")

    scene = args.scene.resolve()
    manifest = json.loads((scene / "manifest.json").read_text())
    session = json.loads((scene / "drive-path-session.json").read_text())
    routes = manifest["navigation_graph"]["routes"]
    node_positions = manifest["navigation_graph"]["node_positions_m"]
    expected = set(manifest["vehicles"])
    if expected != {"thePlayer", "clone0"}:
        raise RuntimeError(f"expected saved red/black pair; got {sorted(expected)}")

    run_id = uuid.uuid4().hex[:12]
    out = ROOT / "runs/sensor-crossing" / f"navgraph-hour-{run_id}"
    (out / "ground_truth").mkdir(parents=True, exist_ok=False)
    (out / "lidar/red").mkdir(parents=True)
    (out / "lidar/black").mkdir()
    stop_requested = False

    def handle_stop(_signum: int, _frame: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    summary: dict[str, Any] = {
        "status": "connecting", "run_id": run_id, "output": str(out),
        "scene": str(scene), "map_expected": "west_coast_usa",
        "target_sim_seconds": args.hours * 3600,
        "simulation_speed_factor_requested": args.speed_factor,
        "traffic_cars_requested": args.traffic_cars,
        "continue_after_damage": args.continue_after_damage,
        "speed_profiles_kmh_red_black": args.speed_profiles_kmh,
        "vehicles": {vid: item.get("model") for vid, item in manifest["vehicles"].items()},
        "route_nodes": {vid: route["graph_nodes"] for vid, route in routes.items()},
        "controller": "BeamNG native waypoint AI; avoid-cars enabled",
        "perception_sensor": "red and black 360-degree LiDAR",
        "ego_auxiliary_sensors": ["wheel speed", "IMU"],
        "ground_truth_separate": True,
        "lidar_hz_requested_per_vehicle": args.lidar_hz,
        "state_hz_requested": args.state_hz,
        "damage_limit_per_leg": args.damage_limit,
        "damage_baseline_note": "Each leg's damage baseline is sampled after a 10-step parked warmup following reset; absolute damage is not comparable across vehicle models.",
        "speed_limit_guard_tolerance_kmh": 8.0,
        "legs": [], "state_rows": 0, "lidar_frames": 0,
        "collected_sim_seconds": 0.0,
    }
    report = out / "summary.json"

    def save_summary() -> None:
        report.write_text(json.dumps(jsonable(summary), indent=2) + "\n")

    save_summary()
    print("OUTPUT", out, flush=True)

    bng = BeamNGpy(args.host, args.port, quit_on_close=False, socket_timeout=60)
    vehicles: dict[str, Any] = {}
    background: dict[str, Any] = {}
    sensor_handles: dict[str, Any] = {}
    run_started_wall: float | None = None
    try:
        bng.open(launch=False)
        mission = bng.control.queue_lua_command("return getMissionFilename()", response=True)
        if "west_coast_usa" not in mission:
            raise RuntimeError(f"BeamNG is not on West Coast USA: {mission!r}")
        bng.control.pause()
        current = bng.vehicles.get_current(include_config=False)
        model_mismatch = any(
            vid not in current or current[vid].model != saved.get("model")
            for vid, saved in manifest["vehicles"].items()
        )
        if set(current) != expected or model_mismatch:
            candidates = [
                scenario
                for scenarios in bng.scenario.get_scenarios(["west_coast_usa"]).values()
                for scenario in scenarios
                if scene.name in str(scenario.path)
            ]
            if not candidates:
                raise RuntimeError(
                    f"Expected saved car models {[(vid, item.get('model')) for vid, item in manifest['vehicles'].items()]}; "
                    f"current cars are {[(vid, v.model) for vid, v in current.items()]}, "
                    f"and BeamNG has no installed scenario for {scene.name}"
                )
            bng.scenario.load(candidates[0], precompile_shaders=False)
            bng.scenario.start(restrict_actions=False)
            bng.control.pause()
            current = bng.vehicles.get_current(include_config=False)
        if set(current) != expected:
            raise RuntimeError(f"Expected saved cars {sorted(expected)}, found {sorted(current)}")

        for vid, saved in manifest["vehicles"].items():
            vehicle = current[vid]
            if vehicle.model != saved.get("model"):
                raise RuntimeError(
                    f"{vid} model mismatch: scenario expects {saved.get('model')!r}, "
                    f"BeamNG has {vehicle.model!r}"
                )
            vehicle.connect(bng)
            vehicle.ai.set_mode("disabled")
            vehicle.control(throttle=0, brake=1, parkingbrake=1)
            if not bng.vehicles.teleport(
                vehicle, saved["position_m"], rot_quat=saved["rotation_xyzw"],
                reset=True, safe_spawn=False,
            ):
                raise RuntimeError(f"Could not restore saved start position for {vid}")
            vehicle.sensors.poll("state")
            if math.dist(vehicle.state["pos"], saved["position_m"]) > 3:
                raise RuntimeError(f"{vid} failed saved-start position check")
            vehicles[vid] = vehicle

        if args.traffic_cars:
            bng.traffic.stop(stop=True)
            bng.traffic.spawn(max_amount=args.traffic_cars, police_ratio=0,
                              extra_amount=0, parked_amount=0)
            bng.control.resume()
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                current = bng.vehicles.get_current(include_config=False)
                background = {vid: v for vid, v in current.items() if vid not in vehicles}
                if len(background) >= args.traffic_cars:
                    break
                time.sleep(0.2)
            bng.control.pause()
            if len(background) < args.traffic_cars:
                raise RuntimeError(
                    f"Requested {args.traffic_cars} traffic cars, spawned {len(background)}"
                )
            background = dict(sorted(background.items())[:args.traffic_cars])
            bng.traffic.stop(stop=True)
            bng.traffic.start(list(background.values()))
            for vehicle in background.values():
                vehicle.connect(bng)
            summary["traffic_vehicles"] = {
                vid: vehicle.model for vid, vehicle in background.items()
            }
            print("TRAFFIC", json.dumps(summary["traffic_vehicles"]), flush=True)

        damage_names = {"thePlayer": f"hour_damage_red_{run_id}",
                        "clone0": f"hour_damage_black_{run_id}"}
        sensor_handles = attach_run_sensors(
            bng, vehicles["thePlayer"], vehicles["clone0"], run_id, args.lidar_hz
        )
        for vid, vehicle in vehicles.items():
            vehicle.sensors.attach(damage_names[vid], Damage())
        meta = {
            "manifest": manifest, "editor_session": session,
            "duration_target_sim_s": args.hours * 3600,
            "simulation_speed_factor_requested": args.speed_factor,
            "physics_steps_per_second": SIM_HZ,
            "traffic_vehicles": summary.get("traffic_vehicles", {}),
            "continue_after_damage": args.continue_after_damage,
            "speed_profiles_kmh_red_black": args.speed_profiles_kmh,
            "sensors": summary["perception_sensor"],
            "auxiliary": summary["ego_auxiliary_sensors"],
            "control": summary["controller"],
            "ground_truth": "separate ground_truth/ stream; do not use as perception input",
        }
        (out / "metadata.json").write_text(json.dumps(jsonable(meta), indent=2) + "\n")

        bng.settings.set_deterministic(SIM_HZ, speed_factor=args.speed_factor)
        bng.control.resume()
        run_started_wall = time.monotonic()
        summary["status"] = "running"
        save_summary()
        total = 0.0
        profile_index = 0
        state_period = 1.0 / args.state_hz
        lidar_period = 1.0 / args.lidar_hz
        global_frame = 0
        global_lidar = 0
        last_progress_wall = time.monotonic()

        with (out / "ground_truth/telemetry.jsonl").open("w") as gt, \
                (out / "sensor_index.jsonl").open("w") as sensor_log:
            while total < args.hours * 3600 and not stop_requested:
                profile = args.speed_profiles_kmh[profile_index % len(args.speed_profiles_kmh)]
                profile_index += 1
                leg_number = len(summary["legs"]) + 1
                print(f"LEG {leg_number} profile={profile_index - 1} "
                      f"red={profile[0]:g} black={profile[1]:g} km/h", flush=True)
                bng.control.pause()
                baselines: dict[str, float] = {}
                for vid, vehicle in vehicles.items():
                    vehicle.ai.set_mode("disabled")
                    vehicle.control(throttle=0, brake=1, parkingbrake=1)
                    saved = manifest["vehicles"][vid]
                    if not bng.vehicles.teleport(
                        vehicle, saved["position_m"], rot_quat=saved["rotation_xyzw"],
                        reset=True, safe_spawn=False,
                    ):
                        raise RuntimeError(f"Could not reset {vid} for leg {leg_number}")
                # Resetting a large truck can produce a stale first damage
                # sample while the chassis settles. Advance a short parked
                # warmup, then use its stable reading as this leg's baseline.
                bng.control.step(10)
                for vid, vehicle in vehicles.items():
                    vehicle.sensors.poll("state", damage_names[vid])
                    baselines[vid] = float(
                        vehicle.sensors[damage_names[vid]].get("damage", 0.0)
                    )
                set_route(vehicles["thePlayer"], routes["thePlayer"], session, profile[0])
                set_route(vehicles["clone0"], routes["clone0"], session, profile[1])
                bng.control.resume()

                leg_start_sim: float | None = None
                previous_sim: float | None = None
                last_state_sample = -1e9
                last_lidar_sample = -1e9
                reached = {vid: False for vid in vehicles}
                leg_damage = {vid: 0.0 for vid in vehicles}
                leg_max_speed_kmh = {vid: 0.0 for vid in vehicles}
                speed_over_since: dict[str, float | None] = {vid: None for vid in vehicles}
                leg_start_total = total
                leg_status = "running"

                while not stop_requested:
                    states: dict[str, dict[str, Any]] = {}
                    for vid, vehicle in vehicles.items():
                        state, damage = read_state(vehicle, damage_names[vid])
                        states[vid] = state
                        leg_damage[vid] = max(0.0, damage - baselines[vid])
                    sim_now = float(states["thePlayer"]["time"])
                    for vid, state in states.items():
                        velocity = state.get("vel", (0.0, 0.0, 0.0))
                        speed_kmh = 3.6 * math.sqrt(sum(float(axis) ** 2 for axis in velocity[:3]))
                        leg_max_speed_kmh[vid] = max(leg_max_speed_kmh[vid], speed_kmh)
                        target_kmh = profile[0] if vid == "thePlayer" else profile[1]
                        if speed_kmh > target_kmh + 8.0:
                            if speed_over_since[vid] is None:
                                speed_over_since[vid] = sim_now
                            elif sim_now - speed_over_since[vid] >= 1.0:
                                leg_status = "stopped_speed_guard"
                                stop_requested = True
                                break
                        else:
                            speed_over_since[vid] = None
                    if leg_status == "stopped_speed_guard":
                        break
                    if leg_start_sim is None:
                        leg_start_sim = sim_now
                        previous_sim = sim_now
                    assert previous_sim is not None
                    delta = max(0.0, sim_now - previous_sim)
                    elapsed_leg = sim_now - leg_start_sim
                    total += delta
                    previous_sim = sim_now

                    for vid, route in routes.items():
                        destination = node_positions[route["end_node"]]
                        if math.dist(states[vid]["pos"], destination) < 12:
                            reached[vid] = True

                    if sim_now - last_state_sample >= state_period:
                        gt.write(json.dumps(jsonable({
                            "frame": global_frame, "leg": leg_number,
                            "profile_index": (profile_index - 1) % len(args.speed_profiles_kmh),
                            "target_speed_kmh": {"thePlayer": profile[0], "clone0": profile[1]},
                            "elapsed_leg_sim_s": elapsed_leg,
                            "collected_sim_s": total,
                            "states": states,
                            "traffic_states": {
                                vid: (vehicle.sensors.poll("state") or dict(vehicle.state))
                                for vid, vehicle in background.items()
                            },
                            "damage_increase": leg_damage,
                            "speed_kmh": {
                                vid: 3.6 * math.sqrt(sum(float(axis) ** 2 for axis in states[vid].get("vel", (0.0, 0.0, 0.0))[:3]))
                                for vid in vehicles
                            },
                            "endpoint_proximity": reached,
                        })) + "\n")
                        gt.flush()
                        global_frame += 1
                        summary["state_rows"] = global_frame
                        last_state_sample = sim_now

                    if sim_now - last_lidar_sample >= lidar_period:
                        data = save_sensor_frame(sensor_handles, vehicles, out, global_lidar)
                        sensor_log.write(json.dumps(jsonable({
                            "frame": global_lidar, "leg": leg_number,
                            "sim_time_s": sim_now, "elapsed_leg_sim_s": elapsed_leg,
                            "collected_sim_s": total, **data,
                        })) + "\n")
                        sensor_log.flush()
                        global_lidar += 1
                        summary["lidar_frames"] = global_lidar
                        last_lidar_sample = sim_now

                    if any(value > args.damage_limit for value in leg_damage.values()):
                        leg_status = "stopped_damage_guard"
                        if not args.continue_after_damage:
                            stop_requested = True
                        break
                    if all(reached.values()):
                        leg_status = "both_endpoints_observed"
                        break
                    if elapsed_leg >= args.max_leg_seconds:
                        leg_status = "leg_time_limit_endpoint_unreached"
                        break
                    if total >= args.hours * 3600:
                        leg_status = "hour_complete"
                        break

                    if time.monotonic() - last_progress_wall >= 15:
                        print(f"PROGRESS sim={total:.0f}/{args.hours * 3600:.0f}s "
                              f"leg={leg_number} elapsed={elapsed_leg:.1f}s "
                              f"endpoints={reached} LiDAR={global_lidar}", flush=True)
                        summary["collected_sim_seconds"] = total
                        save_summary()
                        last_progress_wall = time.monotonic()
                    time.sleep(0.04)

                bng.control.pause()
                if stop_requested and leg_status == "running":
                    leg_status = "interrupted_mid_leg"
                leg_entry = {
                    "leg": leg_number,
                    "profile_index": (profile_index - 1) % len(args.speed_profiles_kmh),
                    "target_speed_kmh": {"thePlayer": profile[0], "clone0": profile[1]},
                    "elapsed_sim_seconds": max(0.0, total - leg_start_total),
                    "endpoint_proximity": reached,
                    "damage_increase": leg_damage,
                    "damage_baseline": baselines,
                    "max_speed_kmh": leg_max_speed_kmh,
                    "status": leg_status,
                }
                summary["legs"].append(leg_entry)
                summary["collected_sim_seconds"] = total
                save_summary()
                print("LEG_RESULT", json.dumps(jsonable(leg_entry)), flush=True)

                if leg_status == "stopped_damage_guard" and not args.continue_after_damage:
                    break
                if leg_status == "stopped_speed_guard":
                    break
                if total >= args.hours * 3600:
                    break

        summary["collected_sim_seconds"] = total
        if summary["legs"] and summary["legs"][-1]["status"] in {
            "stopped_damage_guard", "stopped_speed_guard"
        }:
            summary["status"] = summary["legs"][-1]["status"]
        else:
            summary["status"] = (
                "interrupted" if stop_requested and total < args.hours * 3600 else "complete"
            )
    except BaseException as exc:
        summary["status"] = "error"
        summary["error"] = repr(exc)
        raise
    finally:
        try:
            bng.control.pause()
        except Exception:
            pass
        try:
            bng.settings.set_nondeterministic()
        except Exception:
            pass
        if args.traffic_cars:
            try:
                bng.traffic.stop(stop=True)
            except Exception:
                pass
        for vid, vehicle in vehicles.items():
            try:
                vehicle.ai.set_mode("disabled")
                vehicle.control(throttle=0, brake=1, parkingbrake=1)
            except Exception:
                pass
        for vehicle in background.values():
            try:
                bng.vehicles.despawn(vehicle)
            except Exception:
                pass
        if vehicles:
            for name in (sensor_handles.get("electrics"),
                         damage_names.get("thePlayer") if "damage_names" in locals() else None,
                         damage_names.get("clone0") if "damage_names" in locals() else None):
                if name:
                    try:
                        vehicles["thePlayer"].sensors.detach(name)
                    except Exception:
                        pass
            if "damage_names" in locals() and "clone0" in vehicles:
                try:
                    vehicles["clone0"].sensors.detach(damage_names["clone0"])
                except Exception:
                    pass
        for key in ("lidar_red", "lidar_black", "imu"):
            sensor = sensor_handles.get(key)
            if sensor is not None:
                try:
                    sensor.remove()
                except Exception:
                    pass
        try:
            bng.disconnect()
        except Exception:
            pass
        if run_started_wall is not None:
            wall_elapsed = max(0.001, time.monotonic() - run_started_wall)
            summary["recording_wall_seconds"] = wall_elapsed
            summary["observed_simulation_speed_factor"] = (
                summary["collected_sim_seconds"] / wall_elapsed
            )
        if summary["status"] == "running":
            summary["status"] = "interrupted"
        save_summary()
        print("RESULT", json.dumps(jsonable(summary)), flush=True)
    return 0 if summary["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
