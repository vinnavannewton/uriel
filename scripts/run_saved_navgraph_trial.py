#!/usr/bin/env python3
"""Record configurable trials of the saved West Coast editor routes, without Rust."""
import argparse
import json
import math
import sys
import time
import uuid
from pathlib import Path

from beamngpy import BeamNGpy
from beamngpy.sensors import Damage
from collect_sensor_crossing import attach_sensors, sensor_frame, jsonable

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / 'scenarios/west_coast_red_black_20261018'
COLLISION_LAUNCH_DELAY_S = 12.5


def resolve_participant_ids(manifest, red_override, black_override, loaded_ids):
    """Map saved red/black roles to live BeamNG IDs and fail with setup guidance."""
    roles = {spec.get('role'): vehicle_id
             for vehicle_id, spec in manifest['vehicles'].items()}
    red_key = roles.get('known_red_ego', 'thePlayer')
    black_key = roles.get('unknown_black_vehicle', 'clone0')
    actual_ids = {
        red_key: red_override or red_key,
        black_key: black_override or black_key,
    }
    if actual_ids[red_key] == actual_ids[black_key]:
        raise RuntimeError('Red and black vehicle IDs resolve to the same live vehicle')
    missing = [(saved_key, live_id) for saved_key, live_id in actual_ids.items()
               if live_id not in loaded_ids]
    if missing:
        details = ', '.join(f'{saved_key} (looked for {live_id!r})'
                            for saved_key, live_id in missing)
        raise RuntimeError(
            f"Saved scenario participant(s) not loaded: {details}. "
            f"BeamNG currently reports {sorted(loaded_ids)}. Load the saved "
            f"scenario with both cars, or pass --red-id/--black-id if BeamNG "
            f"assigned different IDs. No trial frames were collected."
        )
    return red_key, black_key, actual_ids


def run_trial(args, out):
    manifest = json.loads((args.scene / 'manifest.json').read_text())
    session = json.loads((args.scene / 'drive-path-session.json').read_text())
    out.mkdir(parents=True, exist_ok=False)
    (out / 'ground_truth').mkdir()
    bng = BeamNGpy('localhost', 25252, quit_on_close=False, socket_timeout=8)
    vehicles, sensors, baseline, background = {}, {}, {}, {}
    red_key, black_key = 'thePlayer', 'clone0'
    actual_ids = {}
    summary = {'status': 'setup', 'output': str(out), 'frames': 0, 'lidar_frames': 0,
               'minimum_reference_separation_m': None, 'controller': 'native BeamNG waypoint AI',
               'guard': 'ground-truth damage/proximity monitor; not LiDAR control',
               'verified_contact': None}
    print('OUTPUT', out, flush=True)
    try:
        bng.open(launch=False)
        mission = bng.control.queue_lua_command('return getMissionFilename()', response=True)
        if 'west_coast_usa' not in mission:
            raise RuntimeError('Current map is not West Coast USA')
        bng.control.pause()
        current = bng.vehicles.get_current(include_config=False)
        red_key, black_key, actual_ids = resolve_participant_ids(
            manifest, args.red_id, args.black_id, current.keys())
        for vid, saved in manifest['vehicles'].items():
            v = current[actual_ids[vid]]
            v.connect(bng)
            vehicles[vid] = v
            if args.reset_start:
                v.ai.set_mode('disabled')
                v.control(throttle=0, brake=1, parkingbrake=1)
                if not bng.vehicles.teleport(v, saved['position_m'],
                        rot_quat=saved['rotation_xyzw'], reset=True, safe_spawn=False):
                    raise RuntimeError(f'Could not reset {vid}')
            v.sensors.poll('state')
            if math.dist(v.state['pos'], saved['position_m']) > 3:
                raise RuntimeError(f'{vid} is not at the saved start; trial not started')
        if args.traffic:
            for v in vehicles.values():
                v.ai.set_mode('disabled')
                v.control(throttle=0, brake=1, parkingbrake=1)
            bng.traffic.stop(stop=True)
            background = {k:v for k,v in current.items()
                          if k not in actual_ids.values()}
            if len(background)<args.traffic:
                bng.traffic.spawn(max_amount=args.traffic, police_ratio=0,
                                  extra_amount=0, parked_amount=0)
                bng.control.resume()
                deadline = time.monotonic()+30
                while time.monotonic()<deadline:
                    current = bng.vehicles.get_current(include_config=False)
                    background = {k:v for k,v in current.items()
                                  if k not in actual_ids.values()}
                    if len(background)>=args.traffic:
                        break
                    time.sleep(.2)
            bng.control.pause()
            bng.traffic.stop(stop=True)
            if len(background)<args.traffic:
                raise RuntimeError('Traffic spawn did not finish; trial not started')
            background = dict(sorted(background.items())[:args.traffic])
            # Explicitly restrict the traffic manager to background vehicles.
            bng.traffic.start(list(background.values()))
            bng.traffic.reset()
            for v in background.values():
                v.connect(bng)
            print('TRAFFIC', sorted(background), flush=True)
            summary['traffic_vehicle_ids'] = sorted(background)
        bng.control.pause()
        for vid, v in vehicles.items():
            v.ai.set_mode('stopping' if args.collision_mode and vid == red_key else 'disabled')
            v.control(throttle=0, brake=1, parkingbrake=1)
            v.sensors.attach('navgraph_trial_damage', Damage())
        # Reset/teleport can return a stale first damage value (especially on
        # the MD70). Let the parked vehicles settle before capturing baselines.
        bng.control.step(10)
        for vid, v in vehicles.items():
            v.sensors.poll('navgraph_trial_damage')
            baseline[vid] = v.sensors['navgraph_trial_damage'].get('damage', 0)
        sensors = attach_sensors(bng, vehicles[red_key], sample_hz=5)
        meta = {'scenario': manifest, 'editor_session': session, 'duration_limit_sim_s': 45,
                'wall_timeout_s': 180, 'sensors': 'red LiDAR + wheel speed + IMU; no cameras',
                'control': 'BeamNG native AI; no Rust', 'baseline_damage': baseline,
                'collision_mode': args.collision_mode,
                'participant_vehicle_ids': actual_ids,
                'target_speed_kmh': {red_key: args.red_speed_kmh,
                                     black_key: args.black_speed_kmh},
                'collision_launch_delay_s': (args.collision_launch_delay_s
                                             if args.collision_mode else None),
                'traffic_requested': args.traffic,
                'traffic_vehicles': {vid:v.model for vid,v in background.items()}}
        (out / 'metadata.json').write_text(json.dumps(meta, indent=2)+'\n')
        route_items = list(manifest['navigation_graph']['routes'].items())
        if args.collision_mode:
            # Approximate crossing alignment from saved route geometry and
            # chosen speed caps; telemetry records whether it was achieved.
            route_items.sort(key=lambda item: item[0] == red_key)
        def start_route(vid, route):
            v = vehicles[vid]
            s = next(s for s in session['splines'] if s['id'] == route['spline_id'])
            target_kmh = args.red_speed_kmh if vid == red_key else args.black_speed_kmh
            route_options = {}
            if target_kmh is not None:
                route_options.update(
                    wp_speeds={node: target_kmh / 3.6 for node in route['graph_nodes']},
                    route_speed=target_kmh / 3.6,
                    route_speed_mode='limit',
                )
            v.control(throttle=0, brake=0, parkingbrake=0)
            v.ai.drive_using_waypoints(
                route['graph_nodes'], wp_speeds=route_options.pop(
                    'wp_speeds', dict(zip(route['graph_nodes'], s['vels']))),
                no_of_laps=s['numLaps'], drive_in_lane=s['isDriveInLane'],
                aggression=s['aggression'],
                avoid_cars=(s['isAvoidCars'] and not args.collision_mode),
                **route_options)
        if args.collision_mode:
            black_route = next((r for vid, r in route_items if vid == black_key), None)
            red_route = next((r for vid, r in route_items if vid == red_key), None)
            if black_route is None or red_route is None:
                raise RuntimeError('Collision mode requires saved red and black routes')
            start_route(black_key, black_route)
            # A saved editor route can remain active on the player car after
            # teleport/reset. Explicitly disable and brake it during the black
            # lead-in, then reject the trial if it drifts before release.
            vehicles[red_key].ai.set_mode('stopping')
            vehicles[red_key].control(throttle=0, brake=1, parkingbrake=1)
            bng.control.resume()
            vehicles[black_key].sensors.poll('state')
            launch_time = float(vehicles[black_key].state['time'])
            red_start = manifest['vehicles'][red_key]['position_m']
            while True:
                vehicles[black_key].sensors.poll('state')
                vehicles[red_key].sensors.poll('state')
                red_state = vehicles[red_key].state
                red_drift = math.dist(red_state['pos'], red_start)
                if red_drift > 3:
                    raise RuntimeError(
                        f'red car moved before release (drift={red_drift:.1f} m); '
                        'aborting trial')
                if (float(vehicles[black_key].state['time']) - launch_time
                        >= args.collision_launch_delay_s):
                    break
                time.sleep(.02)
            start_route(red_key, red_route)
        else:
            for vid, route in route_items:
                start_route(vid, route)
        bng.control.resume()
        summary['status'] = 'running'
        start_wall = time.monotonic()
        start_sim, last_sensor, last_progress = None, -1, -1
        reached = {vid: False for vid in vehicles}
        with (out/'ground_truth/telemetry.jsonl').open('w') as gt, (out/'sensor_index.jsonl').open('w') as si:
            while time.monotonic()-start_wall < 180:
                states = {}
                for vid,v in vehicles.items():
                    v.sensors.poll('state', 'navgraph_trial_damage')
                    states[vid] = dict(v.state)
                now = float(states[red_key]['time'])
                if start_sim is None: start_sim = now
                elapsed = now-start_sim
                separation = math.dist(states[red_key]['pos'], states[black_key]['pos'])
                old = summary['minimum_reference_separation_m']
                summary['minimum_reference_separation_m'] = separation if old is None else min(old,separation)
                damages = {vid:max(0,v.sensors['navgraph_trial_damage'].get('damage',0)-baseline[vid]) for vid,v in vehicles.items()}
                traffic_states = {}
                for vid,v in background.items():
                    v.sensors.poll('state')
                    traffic_states[vid] = dict(v.state)
                gt.write(json.dumps(jsonable({'frame':summary['frames'],'elapsed_s':elapsed,'states':states,'traffic_states':traffic_states,'damage_increase':damages}))+'\n'); gt.flush()
                summary['frames'] += 1
                summary['elapsed_sim_s'] = elapsed
                summary['damage_increase'] = damages
                # A conservative monitor ends this trial before close approach. It is not a perception controller.
                p=[states[black_key]['pos'][i]-states[red_key]['pos'][i] for i in range(3)]
                vel=[states[black_key]['vel'][i]-states[red_key]['vel'][i] for i in range(3)]
                vv=sum(x*x for x in vel)
                ttc=max(0,min(2,-sum(a*c for a,c in zip(p,vel))/vv)) if vv>0.01 else 0
                closest=math.sqrt(sum((a+ttc*c)**2 for a,c in zip(p,vel)))
                if any(d>1 for d in damages.values()):
                    summary['status']='stopped_damage_guard';break
                if not args.collision_mode and (separation<12 or (ttc>0 and separation<35 and closest<10)):
                    summary['status']='stopped_proximity_guard';break
                if now-last_sensor >= .2:
                    data=sensor_frame(sensors,vehicles[red_key],out,summary['lidar_frames'])
                    si.write(json.dumps(jsonable({'sim_time_s':now,'elapsed_s':elapsed,**data}))+'\n');si.flush()
                    summary['lidar_frames'] += 1;last_sensor=now
                for vid,route in manifest['navigation_graph']['routes'].items():
                    dest=manifest['navigation_graph']['node_positions_m'][route['end_node']]
                    if math.dist(states[vid]['pos'],dest)<12: reached[vid]=True
                summary['reached_endpoint_proximity']=reached
                if all(reached.values()): summary['status']='completed_endpoint_proximity';break
                if elapsed>=45: summary['status']='completed_time_limit';break
                if elapsed-last_progress>=5:
                    print(f'TRIAL elapsed={elapsed:.1f}s separation={separation:.1f}m lidar={summary["lidar_frames"]}',flush=True);last_progress=elapsed
                time.sleep(.08)
            else: summary['status']='stopped_wall_timeout'
    except BaseException as exc:
        summary['status']='error';summary['error']=repr(exc)
        raise
    finally:
        try:bng.control.pause()
        except Exception:pass
        if args.traffic:
            try:bng.traffic.stop(stop=True)
            except Exception:pass
        for v in vehicles.values():
            try:
                v.ai.set_mode('disabled');v.control(throttle=0,brake=1,parkingbrake=1)
            except Exception:pass
        for sensor in sensors.values():
            try:sensor.remove()
            except Exception:pass
        (out/'summary.json').write_text(json.dumps(jsonable(summary),indent=2)+'\n')
        try:bng.disconnect()
        except Exception:pass
        print('RESULT',json.dumps(jsonable(summary)),flush=True)
    return summary


def positive_int(value):
    count = int(value)
    if count < 1:
        raise argparse.ArgumentTypeError('must be at least 1')
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, default=SCENE,
                        help='saved scenario directory containing manifest and editor session')
    parser.add_argument('--red-id', help='live BeamNG ID for the saved red participant (default: saved ID)')
    parser.add_argument('--black-id', help='live BeamNG ID for the saved black participant (default: saved ID)')
    parser.add_argument('--trials', type=positive_int, default=1,
                        help='number of trials (default: 1); reset cars before each trial')
    parser.add_argument('--traffic', type=int, default=0, choices=range(0, 9),
                        help='background traffic count (default: 0)')
    parser.add_argument('--collision-mode', action='store_true',
                        help='disable native AI avoid-cars on the two saved routes')
    parser.add_argument('--red-speed-kmh', type=float, default=None,
                        help='cap the red car route speed in km/h')
    parser.add_argument('--black-speed-kmh', type=float, default=None,
                        help='cap the black car route speed in km/h')
    parser.add_argument('--collision-launch-delay-s', type=float,
                        default=COLLISION_LAUNCH_DELAY_S,
                        help='seconds after black starts before red starts in collision mode')
    parser.add_argument('--reset-start', action=argparse.BooleanOptionalAction, default=True,
                        help='restore saved car positions (default: enabled)')
    args = parser.parse_args(argv)
    for name in ('red_speed_kmh', 'black_speed_kmh'):
        value = getattr(args, name)
        if value is not None and not 0 < value <= 120:
            parser.error(f'--{name.replace("_", "-")} must be within (0, 120]')
    if args.collision_launch_delay_s < 0:
        parser.error('--collision-launch-delay-s must be nonnegative')
    if args.trials > 1 and not args.reset_start:
        parser.error('multiple trials require --reset-start')
    batch_dir = ROOT / 'runs/sensor-crossing' / ('navgraph-batch-' + uuid.uuid4().hex[:12])
    batch_dir.mkdir(parents=True, exist_ok=False)
    batch = {'status': 'running', 'requested_trials': args.trials,
             'traffic_count': args.traffic, 'reset_start': args.reset_start,
                'collision_mode': args.collision_mode,
                'collision_launch_delay_s': args.collision_launch_delay_s if args.collision_mode else None,
             'scene': str(args.scene.resolve()), 'trials': []}
    report = batch_dir / 'batch_summary.json'

    def save_batch():
        report.write_text(json.dumps(batch, indent=2)+'\n')

    save_batch()
    print('BATCH', batch_dir, flush=True)
    index, trial_dir = 0, None
    try:
        for index in range(1, args.trials+1):
            print(f'TRIAL {index}/{args.trials}', flush=True)
            trial_dir = batch_dir / f'trial-{index:03d}'
            result = run_trial(args, trial_dir)
            batch['trials'].append({'trial': index, **result})
            save_batch()
        batch['status'] = 'finished'
    except KeyboardInterrupt as exc:
        batch['status'] = 'interrupted'
        batch['error'] = repr(exc)
        # The trial runner persists partial data and its failure in finally.
        failed_report = trial_dir / 'summary.json' if trial_dir is not None else None
        if failed_report is not None and failed_report.exists():
            batch['trials'].append({'trial': index, **json.loads(failed_report.read_text())})
        return 130
    except Exception as exc:
        batch['status'] = 'error'
        batch['error'] = str(exc)
        failed_report = trial_dir / 'summary.json' if trial_dir is not None else None
        if failed_report is not None and failed_report.exists():
            batch['trials'].append({'trial': index, **json.loads(failed_report.read_text())})
        print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        return 1
    finally:
        save_batch()


if __name__=='__main__':
    raise SystemExit(main())
