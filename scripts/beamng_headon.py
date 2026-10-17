"""Run the explicitly requested two-car open-space avoidance demo.

Attach to an already-running smallgrid server; do not launch/close BeamNG.
Rust selects and leases paths by default; --standalone retains the earlier local mode.
Repairs and repositions only thePlayer and uriel_blue. No obstacles or ML.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import signal
import time
import uuid

from beamngpy import BeamNGpy
from beamngpy.sensors import Damage, Electrics
from headon_client import HeadonClient
from headon_planner import choose_plan, guard_reason, path, path_distance, matching_configs, front_aligned_path

ROOT = Path(__file__).resolve().parents[1]
IDS = ('thePlayer', 'uriel_blue')


def snapshot(vehicles):
    result = {}
    for v in vehicles:
        v.sensors.poll()
        result[v.vid] = {'state': dict(v.state),
                        'damage': dict(v.sensors['damage']),
                        'electrics': dict(v.sensors['electrics'])}
    return result


def stop(vehicles):
    errors = []
    for v in vehicles:
        try:
            v.ai.set_mode('disabled')
            v.control(throttle=0, brake=1, parkingbrake=1)
        except Exception as exc:
            errors.append(f'{v.vid}: {exc}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='repair/reposition and run the two cars')
    parser.add_argument('--port', type=int, default=64256)
    parser.add_argument('--server-url', default='ws://127.0.0.1:3000/ws/headon')
    parser.add_argument('--standalone', action='store_true', help='explicitly use the earlier local planner without Rust')
    args = parser.parse_args()
    if not args.run:
        print(json.dumps(asdict(choose_plan([])), indent=2))
        return
    out = ROOT / 'runs' / ('avoidance-' + uuid.uuid4().hex[:10])
    out.mkdir(parents=True)
    b = BeamNGpy('127.0.0.1', args.port, quit_on_close=False, socket_timeout=3)
    vehicles = []
    server = None
    summary = {'outcome': 'setup_failed', 'obstacles_spawned': 0}
    try:
        b.open(launch=False)
        level = b.control.queue_lua_command('return getMissionFilename()', response=True)
        if '/smallgrid/' not in str(level):
            raise RuntimeError(f'Expected flat Grid Plane (smallgrid), got {level}')
        info = b.vehicles.get_current_info()
        if set(info) != set(IDS) or any(info[k]['model'] != 'vivace' for k in IDS):
            raise RuntimeError('Expected exactly the two existing Vivaces; leaving other scenes alone')
        # Preserve their current poses/configurations as evidence before the reset.
        (out / 'before.json').write_text(json.dumps(info, indent=2))
        current = b.vehicles.get_current()
        for name in IDS:
            v = current[name]
            v.connect(b)
            # Vehicle sockets do not inherit the BeamNGpy GE timeout in 1.36.
            v.connection.skt.skt.settimeout(2)
            vehicles.append(v)
            v.sensors.attach('damage', Damage())
            v.sensors.attach('electrics', Electrics())
        stop_errors = stop(vehicles)
        if stop_errors:
            raise RuntimeError(stop_errors)
        # Match the exact same stored 160 DCT parts, preserving the player's name.
        # Existing paired cars were originally cloned; reject mismatched parts.
        if not matching_configs(info[IDS[0]]['config'], info[IDS[1]]['config']):
            raise RuntimeError('Vehicle configurations differ; match parts before this demo')
        b.control.pause()
        for name in IDS:
            b.control.queue_lua_command(f'scenetree.findObject({json.dumps(name)}):reset()', response=True)
        # Smallgrid is an empty plane; use a fixed local encounter centre for repeatability.
        cx, cy = 0., 0.
        for car, v in enumerate(vehicles):
            if not b.vehicles.teleport(v, (cx, cy + (55 if car == 0 else -55), .35),
                                       rot_quat=(0, 0, car, 1-car), reset=True):
                raise RuntimeError(f'Could not position {v.vid}')
            v.set_color((.95,.03,.02,1) if car == 0 else (.02,.15,.95,1))
            v.set_shift_mode('realistic_automatic')
            v.control(steering=0, throttle=0, brake=0, parkingbrake=1, gear=1)
        b.control.queue_lua_command('bullettime.pause(false); bullettime.set(1)', response=True)
        b.control.resume()
        time.sleep(1.5)
        b.control.pause()
        initial = snapshot(vehicles)
        radii = []
        dimensions = {}
        for car, v in enumerate(vehicles):
            s = initial[v.vid]['state']
            if abs(s['pos'][0]) > .2 or abs(s['pos'][1] - (55 if car == 0 else -55)) > .3:
                raise RuntimeError('Spawn moved away from the intended path')
            if s['dir'][1] * (-1 if car == 0 else 1) < .98:
                raise RuntimeError('Unexpected vehicle heading')
            if initial[v.vid]['damage'].get('damage', 0) > 5:
                raise RuntimeError('Vehicle repair did not clear damage')
            bbox=v.get_bbox()
            radii.append(max(math.dist(s['pos'][:2], p[:2]) for p in bbox.values()))
            dimensions[v.vid]={'length_m': math.dist(bbox['front_bottom_left'],bbox['rear_bottom_left']),
                               'width_m':math.dist(bbox['front_bottom_left'],bbox['front_bottom_right']),
                               'enclosing_radius_m':radii[-1]}
        speed = 30 / 3.6
        if args.standalone:
            plan = choose_plan([], tuple(radii), speed=speed)
            plan_data = asdict(plan)
            paths = [path(i, plan.offsets[i]) for i in (0,1)]
            feasible = plan.mode == 'pass'
            assigned_speeds={k:speed for k in IDS}
        else:
            server=HeadonClient(args.server_url,'headon-'+out.name,out/'bridge-wire.jsonl')
            plan_data=server.request(initial,dimensions)
            feasible=plan_data['status']=='prepare'
            paths=[server.geometry[k] for k in IDS]
            assigned_speeds={r['vehicle_id']:r['speed_cap_mps'] for r in plan_data['recommendations']}
        metadata = {'map': level, 'speed_target_mps': speed, 'initial': initial,
                    'vehicle_enclosing_radii_m': radii, 'dimensions':dimensions, 'plan':plan_data,
                    'obstacles': [], 'controller': 'BeamNG built-in AI explicit lines',
                    'learned_model': None, 'rust_coordinator_connected':server is not None,
                    'server_url':args.server_url if server else None,
                    'server_identity':server.identity if server else None,
                    'limitations': 'Flat plane, two matched cars, known empty scene; variable-rate sequential polling; no perception or general safety certification',
                    'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in (Path(__file__), Path(__file__).with_name('headon_planner.py'), Path(__file__).with_name('headon_client.py'))}}
        (out / 'metadata.json').write_text(json.dumps(metadata, indent=2))
        if not feasible:
            summary.update(outcome='paused_no_feasible_plan', reason=plan_data)
            return
        for i, v in enumerate(vehicles):
            coords = front_aligned_path(paths[i], initial[v.vid]['state'])
            b.debug.add_polyline(coords, (1,.1,.1,1) if i == 0 else (.1,.2,1,1))
            v.control(throttle=0, brake=0, parkingbrake=0, steering=0, gear=1)
            v.ai.set_avoid_cars(False)
            v.ai.set_line([{'pos': p, 'speed': assigned_speeds[v.vid]} for p in coords], cling=True)
            v.ai.set_speed(assigned_speeds[v.vid], mode='set')
        b.camera.set_free((cx+65, cy-65, 55), (-65, 65, -55))
        if server:
            server.accept_paths()
            start_plan=server.request(snapshot(vehicles),dimensions)
            if start_plan['status']!='execute':
                raise RuntimeError('Rust did not grant execution after both path acknowledgements')
        print('PLAN',plan_data.get('maneuver_id',plan_data.get('offsets')), 'RUST',server is not None,'RUN',out,flush=True)
        summary.update(outcome='timeout', samples=0, minimum_reference_distance_m=None,
                       minimum_enclosing_circle_clearance_m=None, maximum_damage_increase={k:0 for k in IDS})
        start = time.monotonic()
        last_times = [initial[k]['state']['time'] for k in IDS]
        last_progress = start
        min_gap = float('inf')
        if server and time.monotonic()>=server.deadline:
            raise TimeoutError('Rust execution lease expired before simulation start')
        b.control.resume()
        with (out / 'telemetry.jsonl').open('w') as f:
            while time.monotonic()-start < 28:
                tick = time.monotonic()
                if server and tick>=server.deadline:
                    b.control.pause()
                    summary.update(outcome='emergency_paused',reason='Rust execution lease expired')
                    break
                data = snapshot(vehicles)
                states = [data[k]['state'] for k in IDS]
                reason = guard_reason(states, radii)
                rust_plan = None
                if server:
                    if time.monotonic()>=server.deadline:
                        reason='Rust lease expired during telemetry acquisition'
                    elif reason is None:
                        rust_plan=server.request(data,dimensions)
                        if rust_plan['status'] not in ('execute','complete'):
                            reason='Rust requested pause: '+rust_plan['reason']
                if time.monotonic()-tick > .75:
                    reason = 'telemetry poll exceeded 750ms'
                times = [s['time'] for s in states]
                if all(a > z for a,z in zip(times,last_times)):
                    last_progress = time.monotonic()
                if time.monotonic()-last_progress > 1:
                    reason = 'simulation telemetry stopped advancing'
                last_times = times
                deviations = [path_distance(s['pos'][:2], paths[i]) for i,s in enumerate(states)]
                if max(deviations) > 1.25:
                    reason = 'vehicle deviated over 1.25m from assigned path'
                for k in IDS:
                    increase = data[k]['damage'].get('damage',0)-initial[k]['damage'].get('damage',0)
                    summary['maximum_damage_increase'][k] = max(summary['maximum_damage_increase'][k], increase)
                    if increase > 5:
                        reason = 'new vehicle damage detected'
                gap = math.dist(states[0]['pos'][:2], states[1]['pos'][:2])
                min_gap = min(min_gap, gap)
                summary['minimum_reference_distance_m'] = min_gap
                summary['minimum_enclosing_circle_clearance_m'] = min_gap-sum(radii)
                sample = {'elapsed_wall_s': time.monotonic()-start, 'vehicles': data,
                          'path_deviations_m': deviations, 'guard_reason': reason,
                          'rust_plan_seq':rust_plan['plan_seq'] if rust_plan else None,
                          'rust_status':rust_plan['status'] if rust_plan else None}
                f.write(json.dumps(sample)+'\n'); f.flush()
                summary['samples'] += 1
                if summary['samples'] % 20 == 0:
                    print('SAMPLE',round(sample['elapsed_wall_s'],2),'gap',round(gap,2),
                          'offsets',[round(s['pos'][0],2) for s in states], 'guard',reason, flush=True)
                if reason:
                    b.control.pause()
                    summary.update(outcome='emergency_paused', reason=reason)
                    break
                if (rust_plan and rust_plan['status']=='complete') or (server is None and states[0]['pos'][1] < -32 and states[1]['pos'][1] > 32):
                    summary.update(outcome='passed_and_returned')
                    break
                time.sleep(.06)
        b.control.pause()
        summary['scene_paused'] = True
        summary['brake_errors'] = stop(vehicles)
        summary['final'] = snapshot(vehicles)
        for k in IDS:
            increase = summary['final'][k]['damage'].get('damage',0)-initial[k]['damage'].get('damage',0)
            summary['maximum_damage_increase'][k] = max(summary['maximum_damage_increase'][k],increase)
            if increase > 5:
                summary.update(outcome='damage_detected')
        summary['elapsed_wall_s'] = time.monotonic()-start
        if server:
            summary['server_identity']=server.identity
            summary['maneuver_id']=server.plan['maneuver_id']
            summary['server_plans_received']=server.frame_seq+1
            summary['server_final_status']=server.plan['status']
        print('RESULT',json.dumps({k:v for k,v in summary.items() if k != 'final'}),flush=True)
    except BaseException as exc:
        summary.update(outcome='error', reason=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        # Freeze the completed scene: input acknowledgements alone do not prove a stop.
        try:
            if vehicles:
                b.control.pause()
                summary['scene_paused'] = True
        except Exception as exc:
            summary['pause_error'] = str(exc)
        summary['cleanup_brake_errors'] = stop(vehicles)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2))
        if server:
            try:
                server.close()
            except Exception:
                pass
        for v in vehicles:
            try:
                v.disconnect()
            except Exception:
                pass
        b.disconnect()
        print('EVIDENCE',out,flush=True)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt('run interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    main()
