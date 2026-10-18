#!/usr/bin/env python3
"""One randomized truck/car trial with exact editor paths and two roof LiDARs."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import uuid

import numpy as np
from beamngpy import BeamNGpy, Vehicle
from beamngpy.sensors import Damage, Electrics, Lidar
import collect_west_coast_arrival_trials as rec
import collect_west_coast_vehicle_pilot as pilot

TRUCKS = {'pickup': 'vehicles/pickup/d15_A.pc',
          'van': 'vehicles/van/deliverytruck.pc'}
CARS = {'vivace': 'vehicles/vivace/vivace_160_DCT.pc',
        'etk800': 'vehicles/etk800/844_150_A.pc',
        'covet': 'vehicles/covet/15le_A.pc',
        'bastion': 'vehicles/bastion/base_v6_A.pc'}


class LidarWriter:
    def __init__(self, folder, sensors, byte_limit=256 * 1024 * 1024):
        self.folder = Path(folder)
        self.folder.mkdir(exist_ok=True)
        self.sensors = sensors
        self.byte_limit = byte_limit
        self.bytes = 0
        self.last = {}
        self.stats = {name: {'polls': 0, 'scans': 0, 'empty': 0, 'repeated': 0,
                             'points': 0} for name in sensors}

    def __call__(self, trial_id, frame, elapsed, vehicles):
        if frame % 2:
            return
        by_name = {v.vid: v for v in vehicles}
        for name, sensor in self.sensors.items():
            reading = sensor.poll()
            points = np.asarray(reading['pointCloud'], dtype=np.float32)
            colours = np.asarray(reading['colours'], dtype=np.uint8)
            stat = self.stats[name]
            stat['polls'] += 1
            row = {'trial_id': trial_id, 'frame_id': frame, 'vehicle_id': name,
                   'vehicle_model': by_name[name].model,
                   'poll_elapsed_s': elapsed, 'poll_sim_time_s': float(by_name[name].state['time']),
                   'acquisition_time_s': None}
            if not points.size:
                stat['empty'] += 1
                row['status'] = 'empty'
            else:
                if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
                    raise RuntimeError('Malformed or nonfinite LiDAR point cloud')
                if colours.shape != points.shape:
                    raise RuntimeError('LiDAR point/colour count mismatch')
                signature = hashlib.sha256(points.tobytes() + colours.tobytes()).hexdigest()
                row['point_count'] = len(points)
                if name in self.last and signature == self.last[name][0]:
                    stat['repeated'] += 1
                    row.update(status='repeated', file=self.last[name][1])
                else:
                    self.bytes += points.nbytes + colours.nbytes
                    if self.bytes > self.byte_limit:
                        raise RuntimeError('LiDAR recording exceeded bounded raw data budget')
                    filename = f'{name}-{frame:05d}.npz'
                    position = np.asarray(sensor.get_position(), dtype=np.float64)
                    state = by_name[name].state
                    np.savez_compressed(self.folder / filename, points=points, colours=colours,
                        sensor_world_position=position, vehicle_position=np.asarray(state['pos']),
                        vehicle_forward=np.asarray(state['dir']), vehicle_up=np.asarray(state['up']),
                        poll_sim_time_s=row['poll_sim_time_s'], poll_elapsed_s=elapsed)
                    self.last[name] = (signature, filename)
                    stat['scans'] += 1
                    stat['points'] += len(points)
                    row.update(status='saved', file=filename, sensor_world_position=position.tolist())
            with (self.folder / 'index.jsonl').open('a') as f:
                f.write(json.dumps(row, allow_nan=False) + '\n')


def main():
    scene_settings = rec.read_json(rec.SNAPSHOT).get('collection_settings', {})
    black_multiplier = float(scene_settings.get('black_speed_multiplier', 1.1))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=scene_settings.get('seed_next', 9302))
    parser.add_argument('--speed-factor', type=float, default=2.0,
                        help='BeamNG deterministic physics speed factor (default: 2x)')
    parser.add_argument('--no-lidar', action='store_true',
                        help='Collect vehicle telemetry only; do not create or poll LiDAR sensors')
    args = parser.parse_args()
    if not 1.0 <= args.speed_factor <= 8.0:
        parser.error('--speed-factor must be between 1 and 8')
    rng = random.Random(args.seed)
    truck, car = rng.choice(list(TRUCKS)), rng.choice(list(CARS))
    choices = {'clone12': (truck, TRUCKS[truck]), 'clone13': (car, CARS[car])}
    run_prefix = 'west-coast-telemetry-' if args.no_lidar else 'west-coast-lidar-'
    folder = rec.ROOT / 'runs' / (run_prefix + uuid.uuid4().hex[:10])
    folder.mkdir()
    print('EVIDENCE', folder, flush=True)
    print('RANDOM VEHICLES', choices, flush=True)
    b = BeamNGpy('127.0.0.1', 25252, quit_on_close=False, socket_timeout=15)
    vehicles, sensors, selectors, saved = [], {}, {}, {}
    result, writer = None, None
    status = {'seed': args.seed, 'choices': choices, 'black_speed_multiplier': black_multiplier,
              'simulation_speed_factor': args.speed_factor,
              'lidar_enabled': not args.no_lidar,
              'selection': 'one random truck/commercial vehicle plus one random passenger car',
              'lidar_timing': ('not collected' if args.no_lidar else
                  'asynchronous latest readings; polling timestamps supplied; acquisition timestamps unavailable'),
              'point_coordinates': 'raw native XYZ; sensor world position and vehicle pose retained per saved scan',
              'training_ready': False}
    try:
        b.open(launch=False)
        b.control.pause()
        original = pilot.lua_json(b, pilot.CAPTURE)
        assert original['mapName'] == 'west_coast_usa'
        rec.write_json(folder / 'scene-before.json', original)
        routes = {s['linked_vehicle_name']: s['graphNodes'] for s in original['splines']
                  if s.get('isEnabled') and s.get('linked_vehicle_name') in rec.IDS}
        assert set(routes) == set(rec.IDS)
        links = {s['id']: s.get('linked_vehicle_name') for s in original['splines']}
        for name in rec.IDS:
            model, config = choices[name]
            color = (.08, .25, .95, 1) if name == 'clone12' else (.06, .06, .06, 1)
            v = Vehicle(name, model=model, part_config=config, color=color, color2=color, color3=color)
            if not b.vehicles.replace(v, old_vehicle=name):
                raise RuntimeError(f'Could not replace {name}')
            vehicles.append(v)
            v.sensors.attach('damage', Damage())
            v.sensors.attach('electrics', Electrics())
            v.ai.set_mode('disabled')
            selectors[name] = rec.selector_for(v)
            v.set_shift_mode('realistic_automatic')
            v.control(steering=0, throttle=0, brake=1, parkingbrake=1, gear=selectors[name])
        links_json = json.dumps(links)
        b.control.queue_lua_command("local links=jsonDecode([==[" + links_json + "]==]);" +
            "local m=require('editor/drivePathEditor/splineMgr');local ids={};for _,v in ipairs(getAllVehicles()) do ids[v:getName()]=v:getID() end;for _,s in ipairs(m.getDrivePathSplines()) do s.linkVehId=ids[links[s.id]];s.isVehicleLink=s.linkVehId~=nil end;m.getActiveVehicles(true);m.relinkAllVehiclesToSplines()", response=True)
        pilot.PILOT_ROUTES = routes
        poses = pilot.place_upright(b)
        b.settings.set_deterministic(60, speed_factor=args.speed_factor)
        pilot.wake_physics(b, vehicles)
        current = pilot.lua_json(b, pilot.CAPTURE)
        saved = {v['name']: v for v in current['vehicles']}
        for name in rec.IDS:
            saved[name].update(poses[name])
        for v in vehicles:
            assert v.state['up'][2] > .95 and v.sensors['damage']['damage'] <= 5
        mounts = {}
        if not args.no_lidar:
            boxes = pilot.lua_json(b, rec.get_box_lua())
            for v in vehicles:
                roof_z = max(p[2] for p in boxes[v.vid])
                height = roof_z - float(v.state['pos'][2]) + .3
                initial_height = height
                for attempt in range(2):
                    sensor = Lidar('uriel_' + folder.name[-10:] + '_' + v.vid, b, v,
                        pos=(0, 0, height), vertical_resolution=16, vertical_angle=30,
                        frequency=5, requested_update_time=.2, max_distance=70, density=100,
                        is_using_shared_memory=False, is_visualised=False, is_360_mode=True)
                    sensors[v.vid] = sensor
                    actual_position = sensor.get_position()
                    if actual_position[2] >= roof_z + .2:
                        break
                    height += roof_z + .3 - actual_position[2]
                    sensor.remove()
                    del sensors[v.vid]
                if v.vid not in sensors:
                    raise RuntimeError(f'{v.vid} could not obtain an above-roof LiDAR mount')
                mounts[v.vid] = {'mount_local_m': [0, 0, height], 'roof_world_z_m': roof_z,
                                'mount_height_calibration_m': height - initial_height,
                                'vertical_channels': 16, 'vertical_fov_degrees': 30,
                                'range_m': 70, 'density': 100, 'requested_update_s': .2,
                                'annotation_mode': False, 'is_static': False}
            pilot.wake_physics(b, vehicles)
            for name, sensor in sensors.items():
                readings = sensor.poll()
                for _ in range(4):
                    if len(readings['pointCloud']):
                        break
                    b.control.step(1)
                    readings = sensor.poll()
                if not len(readings['pointCloud']):
                    raise RuntimeError(f'{name} LiDAR produced no points before launch')
                world_pos = sensor.get_position()
                if world_pos[2] < mounts[name]['roof_world_z_m']:
                    raise RuntimeError(f'{name} LiDAR is below the roof')
                mounts[name].update(initial_point_count=len(readings['pointCloud']),
                                    initial_sensor_world_position=list(world_pos))
                print('LIDAR READY', name, mounts[name], flush=True)
        else:
            print('LIDAR DISABLED; collecting vehicle telemetry only', flush=True)
        status['lidar_sensors'] = mounts
        rec.write_json(folder / 'lidar-setup.json', status)
        current['lidar_configuration'] = mounts if mounts else None
        current['collection_settings'] = dict(scene_settings, seed_next=args.seed + 1,
                                               black_speed_multiplier=black_multiplier)
        if rec.SNAPSHOT.exists():
            (folder / 'previous-snapshot.json').write_bytes(rec.SNAPSHOT.read_bytes())
        rec.write_json(rec.SNAPSHOT, current)
        rec.write_json(folder / 'trial-scene.json', current)
        writer = LidarWriter(folder / 'lidar', sensors) if sensors else None
        trial_mode = 'TELEMETRY-ONLY' if args.no_lidar else 'TELEMETRY + LIDAR'
        print(f'STARTING {trial_mode} TRIAL; BLACK SPEED MULTIPLIER {black_multiplier:.3f}', flush=True)
        result = rec.run_trial(b, vehicles, saved, selectors, folder, 0, 50, args.speed_factor,
            routes, random.Random(args.seed + 1), 20, 22, 2, rec.SNAPSHOT,
            sample_callback=writer, speed_scales={'clone13': black_multiplier})
        status['result'] = result
        meta_path = folder / result['trial_id'] / 'metadata.json'
        metadata = rec.read_json(meta_path)
        metadata.update(seed=args.seed, lidar_index='../lidar/index.jsonl',
                        lidar_setup='../lidar-setup.json', black_speed_multiplier=black_multiplier)
        rec.write_json(meta_path, metadata)
    except BaseException as exc:
        status['failure'] = repr(exc)
        print('STOPPED', repr(exc), flush=True)
    finally:
        status['lidar_counts'] = writer.stats if writer else {}
        for sensor in sensors.values():
            try:
                sensor.remove()
            except Exception as exc:
                status.setdefault('sensor_cleanup_errors', []).append(repr(exc))
        if b.connection:
            if vehicles:
                status['vehicle_cleanup_errors'] = rec.stop_and_restore(b, vehicles, saved,
                    {'selectors': selectors, 'positions': bool(saved) and
                     (result is None or result.get('outcome') != 'damage_sensor_threshold')})
            b.control.pause()
            b.disconnect()
        status['sensors_removed_after_recording'] = True
        rec.write_json(folder / 'summary.json', status)
        print('LIDAR COUNTS', status['lidar_counts'], flush=True)
        print('EVIDENCE', folder, flush=True)


if __name__ == '__main__':
    main()
