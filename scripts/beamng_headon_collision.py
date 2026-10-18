"""Run a cooperative two-Vivace head-on dodge on plain Grid Plane.

BeamNG must already be open with its BeamNGpy server listening. This script
does not launch or close BeamNG. Without --run it only prints the run settings.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RED_ID = 'thePlayer'
BLUE_ID = 'uriel_blue'


class CollisionObserver:
    def __init__(self, url, world_id, dimensions, mode="collision", vehicle_ids=(RED_ID, BLUE_ID)):
        self.url = url.rstrip('/') + '/api/collision/telemetry'
        self.world_id = world_id
        self.dimensions = dimensions
        self.mode = mode
        self.vehicle_ids = vehicle_ids
        self.frame_seq = 0
        self.latest = None

    def publish(self, data, finished=False):
        self.latest = data
        vehicles = []
        for name, display_id in zip(self.vehicle_ids, (RED_ID, BLUE_ID)):
            state = data[name]['state']
            vehicles.append({'vehicle_id': display_id, 'position_xyz_m': state['pos'],
                             'velocity_xyz_mps': state['vel'], 'forward_xyz': state['dir'],
                             'up_xyz': state['up'], 'sensor_sim_time_s': state['time'],
                             'damage': data[name]['damage'].get('damage', 0),
                             **self.dimensions[name]})
        body = {'world_id': self.world_id, 'frame_seq': self.frame_seq, 'mode': self.mode,
                'sim_time_s': max(v['sensor_sim_time_s'] for v in vehicles),
                'finished': finished, 'vehicles': vehicles}
        headers = {'Content-Type': 'application/json'}
        if os.environ.get('ARC_TOKEN'):
            headers['Authorization'] = 'Bearer ' + os.environ['ARC_TOKEN']
        request = Request(self.url, json.dumps(body, allow_nan=False).encode(), headers)
        with urlopen(request, timeout=.75) as response:
            if response.status != 204:
                raise RuntimeError(f'Dashboard rejected telemetry: HTTP {response.status}')
        self.frame_seq += 1


def forward_selector_index(gearbox_type):
    # BeamNG's realistic DCT selector uses 1=P and 2=D, unlike a manual
    # gearbox where 1 selects first gear. Do not guess for unknown drivetrains.
    if gearbox_type == 'dctGearbox':
        return 2
    if gearbox_type == 'manualGearbox':
        return 1
    raise ValueError(f'Unsupported Vivace gearbox type: {gearbox_type!r}')


def plan_dodge_paths(center, radii, speed):
    if __package__:
        from .headon_planner import choose_plan, path
    else:
        from headon_planner import choose_plan, path
    plan = choose_plan([], tuple(radii), speed=speed)
    if plan.mode != 'pass':
        raise RuntimeError('No feasible open-grid dodge for these vehicle envelopes')
    paths = [[(x + center[0], y + center[1]) for x, y in path(i, plan.offsets[i])]
             for i in (0, 1)]
    return plan, paths


def snapshot(vehicles):
    data = {}
    for vehicle in vehicles:
        vehicle.sensors.poll()
        data[vehicle.vid] = {
            'state': dict(vehicle.state),
            'damage': dict(vehicle.sensors['damage']),
            'electrics': dict(vehicle.sensors['electrics']),
        }
    return data


def stop(vehicles):
    errors = []
    for vehicle in vehicles:
        try:
            vehicle.ai.set_mode('disabled')
            vehicle.control(throttle=0, brake=1, parkingbrake=1)
        except Exception as exc:  # Preserve other cleanup attempts if one socket fails.
            errors.append(f'{vehicle.vid}: {type(exc).__name__}: {exc}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='reposition both cars and execute the cooperative dodge')
    parser.add_argument('--dashboard-url', default='http://127.0.0.1:3001', help='dashboard HTTP origin (default: http://127.0.0.1:3001)')
    parser.add_argument('--no-dashboard', action='store_true', help='run without dashboard telemetry')
    parser.add_argument('--port', type=int, default=64256, help='BeamNGpy server port (default: 64256)')
    parser.add_argument('--separation-m', type=float, default=110.0, help='prepared dodge separation (110 m)')
    parser.add_argument('--speed-kmh', type=float, default=30.0, help='AI target speed for both cars (default: 30; maximum: 36)')
    parser.add_argument('--duration-s', type=float, default=20.0, help='maximum driving duration (default: 20)')
    parser.add_argument('--impact-threshold', type=float, default=5.0, help='stop after this much new damage on either car (default: 5)')
    args = parser.parse_args()

    if args.separation_m != 110:
        parser.error('The prepared dodge paths require --separation-m 110')
    if not (10 <= args.speed_kmh <= 36):
        parser.error('--speed-kmh must be between 10 and 36 for the dodge')
    if not (2 <= args.duration_s <= 30):
        parser.error('--duration-s must be between 2 and 30')
    if not (0 < args.impact_threshold <= 1000):
        parser.error('--impact-threshold must be in (0, 1000]')

    red_id, blue_id = RED_ID, BLUE_ID
    settings = {'map': 'smallgrid', 'vehicles': [red_id, blue_id],
                'separation_m': args.separation_m, 'speed_kmh': args.speed_kmh,
                'duration_s': args.duration_s, 'impact_threshold': args.impact_threshold,
                'dashboard_url': None if args.no_dashboard else args.dashboard_url,
                'mode': 'cooperative dodge; Python paired-path planner; empty grid; no ML'}
    if not args.run:
        print(json.dumps({'dry_run': True, 'settings': settings,
                          'command_to_start': 'python scripts/beamng_headon_collision.py --run'}, indent=2))
        print('No BeamNG connection made. Add --run only when you are ready for the dodge.')
        return

    from beamngpy import BeamNGpy, Vehicle
    from beamngpy.sensors import Damage, Electrics

    run_dir = ROOT / 'runs' / ('headon-dodge-' + uuid.uuid4().hex[:10])
    run_dir.mkdir(parents=True)
    out = {'outcome': 'setup_failed', 'samples': 0, 'damage_increase': {},
           'minimum_reference_distance_m': None, 'scene_paused': False, 'cleanup_errors': []}
    bng = BeamNGpy('127.0.0.1', args.port, quit_on_close=False, socket_timeout=3)
    vehicles = []
    opened = False
    safe_to_pause = False
    observer = None
    try:
        bng.open(launch=False)
        opened = True
        level = bng.control.queue_lua_command('return getMissionFilename()', response=True)
        if '/smallgrid/' not in str(level):
            raise RuntimeError(f'Expected Grid Plane / smallgrid; found {level!r}. No vehicles changed.')

        info = bng.vehicles.get_current_info()
        present = set(info)
        if present == {'red', 'blue'}:
            red_id, blue_id = 'red', 'blue'
        elif present not in ({red_id}, {red_id, blue_id}):
            raise RuntimeError(f'Expected only {RED_ID} or the pair {RED_ID}/{BLUE_ID}, or the loaded red/blue pair; found {sorted(present)}. No vehicles changed.')
        settings['vehicles'] = [red_id, blue_id]
        if info[red_id].get('model') != 'vivace':
            raise RuntimeError(f'{red_id} must be a Vivace; found {info[red_id].get("model")!r}.')
        spawned_blue = blue_id not in info
        if not spawned_blue:
            if info[blue_id].get('model') != 'vivace':
                raise RuntimeError(f'{blue_id} must be a Vivace; found {info[blue_id].get("model")!r}.')
            from headon_planner import matching_configs
            if not matching_configs(info[red_id]['config'], info[blue_id]['config']):
                raise RuntimeError('The two Vivace configurations differ. Match their physical parts before running.')

        safe_to_pause = True
        bng.control.pause()
        current = bng.vehicles.get_current()
        red = current[red_id]
        red.connect(bng)
        red.connection.skt.skt.settimeout(2)
        vehicles.append(red)
        if not spawned_blue:
            blue = current[blue_id]
            blue.connect(bng)
            blue.connection.skt.skt.settimeout(2)
            vehicles.append(blue)
        else:
            config = dict(info[red_id]['config'])
            config.pop('paints', None)
            blue = Vehicle(blue_id, model='vivace', part_config=config,
                           color=(.02, .15, .95, 1), color2=(.02, .15, .95, 1),
                           color3=(.02, .15, .95, 1))
            vehicles.append(blue)

        for vehicle in vehicles:
            vehicle.sensors.attach('damage', Damage())
            vehicle.sensors.attach('electrics', Electrics())
            vehicle.ai.set_mode('disabled')

        red.sensors.poll()
        center_x, center_y, _ = red.state['pos']
        half = args.separation_m / 2
        z = .35
        starts = {red_id: (center_x, center_y + half, z),
                  blue_id: (center_x, center_y - half, z)}
        rotations = {red_id: (0, 0, 0, 1), blue_id: (0, 0, 1, 0)}

        red.set_color((.95, .03, .02, 1))
        if not bng.vehicles.teleport(red, starts[red_id], rot_quat=rotations[red_id], reset=True):
            raise RuntimeError('Could not position the red car.')
        if spawned_blue:
            if not bng.vehicles.spawn(blue, starts[blue_id], rot_quat=rotations[blue_id], safe_spawn=False):
                raise RuntimeError('Could not spawn the blue matching Vivace.')
        elif not bng.vehicles.teleport(blue, starts[blue_id], rot_quat=rotations[blue_id], reset=True):
            raise RuntimeError('Could not position the blue car.')

        blue.set_color((.02, .15, .95, 1))
        forward_selectors = {}
        for vehicle in vehicles:
            gearbox_type = vehicle.queue_lua_command(
                "local g = powertrain.getDevice('gearbox'); return g and g.type or 'missing'",
                response=True)
            forward_selectors[vehicle.vid] = forward_selector_index(gearbox_type)
            vehicle.set_shift_mode('realistic_automatic')
            vehicle.control(steering=0, throttle=0, brake=0, parkingbrake=1,
                            gear=forward_selectors[vehicle.vid])

        bng.control.queue_lua_command('bullettime.pause(false); bullettime.set(1)', response=True)
        bng.control.resume()
        time.sleep(1.2)
        bng.control.pause()
        initial = snapshot(vehicles)
        dimensions = {}
        for vehicle in vehicles:
            box = vehicle.get_bbox()
            dimensions[vehicle.vid] = {
                'length_m': math.dist(box['front_bottom_left'], box['rear_bottom_left']),
                'width_m': math.dist(box['front_bottom_left'], box['front_bottom_right']),
                'enclosing_radius_m': max(math.dist(initial[vehicle.vid]['state']['pos'], p)
                                          for p in box.values())}
        if not args.no_dashboard:
            observer = CollisionObserver(args.dashboard_url, run_dir.name, dimensions, mode="dodge", vehicle_ids=(red_id, blue_id))
            observer.publish(initial)
            print(f'DASHBOARD {args.dashboard_url} (live dodge telemetry)', flush=True)
        for vehicle_id, sign in ((red_id, -1), (blue_id, 1)):
            state = initial[vehicle_id]['state']
            expected_y = starts[vehicle_id][1]
            if abs(state['pos'][0] - center_x) > .5 or abs(state['pos'][1] - expected_y) > .5:
                raise RuntimeError(f'{vehicle_id} drifted from the planned start; refusing to drive.')
            if state['dir'][1] * sign < .9:
                raise RuntimeError(f'{vehicle_id} is not facing its opposing direction; refusing to drive.')
            if initial[vehicle_id]['damage'].get('damage', 0) > 5:
                raise RuntimeError(f'{vehicle_id} did not reset to a repaired state; refusing to drive.')

        from headon_planner import front_aligned_path, guard_reason, path_distance
        speed = args.speed_kmh / 3.6
        radii = [dimensions[name]['enclosing_radius_m'] for name in (red_id, blue_id)]
        dodge_plan, paths = plan_dodge_paths((center_x, center_y), radii, speed)
        for i, vehicle_id in enumerate((red_id, blue_id)):
            vehicle = next(v for v in vehicles if v.vid == vehicle_id)
            state = initial[vehicle_id]['state']
            line = [{'pos': p, 'speed': speed}
                    for p in front_aligned_path(paths[i], state)]
            vehicle.ai.set_avoid_cars(False)
            vehicle.ai.set_line(line, cling=True)
            vehicle.ai.set_speed(speed, mode='set')

        # The setup hold above deliberately parks the cars while BeamNG is
        # paused. Queue a release before starting the AI. Electrics readbacks
        # remain frozen while physics is paused, so validate launch from live
        # position samples after resuming instead of checking stale brake data.
        for vehicle in vehicles:
            vehicle.control(steering=0, throttle=0, brake=0, parkingbrake=0,
                            gear=forward_selectors[vehicle.vid])

        bng.camera.set_free((center_x + 65, center_y - 65, 45), (-65, 65, -45))
        metadata = {
            **settings, 'map_file': str(level), 'beamngpy_port': args.port,
            'spawned_blue_this_run': spawned_blue, 'start_states': initial,
            'dodge_offsets_m': dodge_plan.offsets, 'dodge_paths_xy_m': paths,
            'forward_selector_indices': forward_selectors,
            'vehicle_config': info[red_id]['config'],
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'collision_detection': 'damage sensor increase; not a synchronized contact label',
        }
        (run_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2))
        out.update(outcome='running', damage_increase={v.vid: 0.0 for v in vehicles})
        print(f'RUNNING cooperative head-on dodge: {run_dir}', flush=True)
        print(f'Both Vivaces target {args.speed_kmh:g} km/h from {args.separation_m:g} m apart. Press Ctrl+C to stop early.', flush=True)

        baselines = {vehicle_id: initial[vehicle_id]['damage'].get('damage', 0.0)
                     for vehicle_id in (red_id, blue_id)}
        start_positions = {vehicle_id: initial[vehicle_id]['state']['pos'][:]
                           for vehicle_id in (red_id, blue_id)}
        started = time.monotonic()
        event = None
        # Physics was paused after positioning; queued controls and AI paths
        # cannot take effect until the scene is resumed.
        bng.control.resume()
        with (run_dir / 'telemetry.jsonl').open('w') as telemetry:
            while time.monotonic() - started < args.duration_s:
                elapsed = time.monotonic() - started
                sample = snapshot(vehicles)
                states = {vehicle_id: sample[vehicle_id]['state'] for vehicle_id in (red_id, blue_id)}
                distance = math.dist(states[red_id]['pos'], states[blue_id]['pos'])
                previous_min = out['minimum_reference_distance_m']
                out['minimum_reference_distance_m'] = distance if previous_min is None else min(previous_min, distance)
                increases = {vehicle_id: max(0.0, sample[vehicle_id]['damage'].get('damage', 0.0) - baselines[vehicle_id])
                             for vehicle_id in (red_id, blue_id)}
                record = {'elapsed_wall_s': elapsed, 'reference_distance_m': distance,
                          'vehicles': sample, 'damage_increase': increases}
                telemetry.write(json.dumps(record) + '\n')
                telemetry.flush()
                if observer:
                    observer.publish(sample)
                out['samples'] += 1
                out['damage_increase'] = increases
                if out['samples'] % 10 == 0:
                    print(f'SAMPLE {elapsed:.1f}s gap={distance:.1f}m damage={increases}', flush=True)
                if max(increases.values(), default=0.0) >= args.impact_threshold:
                    event = 'damage_sensor_threshold'
                    break
                reason = guard_reason([states[name] for name in (red_id, blue_id)], radii)
                if reason is None and any(path_distance(states[name]['pos'][:2], paths[i]) > 1.2
                                          for i, name in enumerate((red_id, blue_id))):
                    reason = 'vehicle deviated from assigned dodge path'
                if reason:
                    bng.control.pause()
                    out['reason'] = reason
                    event = 'emergency_paused'
                    break
                if (states[red_id]['pos'][1] < center_y - 30
                        and states[blue_id]['pos'][1] > center_y + 30
                        and all(abs(states[name]['pos'][0] - center_x) < .6
                                for name in (red_id, blue_id))):
                    event = 'passed_and_returned'
                    break
                if elapsed >= 2.5 and any(
                        math.dist(states[vehicle_id]['pos'], start_positions[vehicle_id]) < 1.0
                        for vehicle_id in (red_id, blue_id)):
                    event = 'launch_failed_no_motion'
                    out['launch_diagnostics'] = {
                        vehicle_id: {key: sample[vehicle_id]['electrics'].get(key)
                                     for key in ('gear', 'parkingbrake_input',
                                                 'throttle_input', 'rpm')}
                        for vehicle_id in (red_id, blue_id)}
                    break
                time.sleep(.08)

        bng.control.pause()
        out['scene_paused'] = True
        out['outcome'] = ('impact_detected' if event == 'damage_sensor_threshold' else
                          'launch_failed_no_motion' if event == 'launch_failed_no_motion' else
                          event if event in ('passed_and_returned', 'emergency_paused') else
                          'duration_elapsed_incomplete_dodge')
        out['impact_signal'] = event
        out['elapsed_wall_s'] = time.monotonic() - started
        out['final'] = snapshot(vehicles)
        for vehicle_id in (red_id, blue_id):
            out['damage_increase'][vehicle_id] = max(
                out['damage_increase'].get(vehicle_id, 0.0),
                max(0.0, out['final'][vehicle_id]['damage'].get('damage', 0.0) - baselines[vehicle_id]))
        print('RESULT ' + json.dumps({k: v for k, v in out.items() if k != 'final'}), flush=True)
    except KeyboardInterrupt:
        out.update(outcome='interrupted_by_operator', reason='Ctrl+C')
        print('Interrupted; pausing and disabling both AI drivers.', flush=True)
    except Exception as exc:
        out.update(outcome='error', reason=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        if opened and safe_to_pause:
            try:
                bng.control.pause()
                out['scene_paused'] = True
            except Exception as exc:
                out['pause_error'] = f'{type(exc).__name__}: {exc}'
        out['cleanup_errors'] = stop(vehicles)
        if observer and observer.latest is not None:
            try:
                observer.publish(observer.latest, finished=True)
            except Exception as exc:
                out['dashboard_close_error'] = f'{type(exc).__name__}: {exc}'
        out['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (run_dir / 'summary.json').write_text(json.dumps(out, indent=2))
        for vehicle in vehicles:
            try:
                vehicle.disconnect()
            except Exception:
                pass
        if opened:
            bng.disconnect()
        print(f'EVIDENCE {run_dir}', flush=True)


if __name__ == '__main__':
    main()
