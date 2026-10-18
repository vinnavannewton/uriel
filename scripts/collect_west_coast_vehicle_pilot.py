#!/usr/bin/env python3
"""Three-model operational pilot; preserve the editor save and audit route corrections."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import time
import uuid

from beamngpy import BeamNGpy, Vehicle
from beamngpy.sensors import Damage, Electrics
import collect_west_coast_arrival_trials as recorder

PILOT_ROUTES = {
    'clone12': ['junction1_wp3', 'junction1_wp8', 'junction1_wp12',
                'junction1_wp18', 'junction1_wp19'],
    'clone13': ['tunnel_city_A_58', 'tunnel_city_A_59', 'tunnel_city_A_60',
                'tunnel_city_A_61', 'tunnel_city_A_62', 'tunnel_city_A_63',
                'junction1_wp12', 'DR323_2'],
}
VIVACE = ('vivace', 'vehicles/vivace/vivace_160_DCT.pc')
ETK = ('etk800', 'vehicles/etk800/844_150_A.pc')
COVET = ('covet', 'vehicles/covet/15le_A.pc')
PAIRS = [(VIVACE, ETK), (ETK, COVET), (COVET, VIVACE)]

CAPTURE = """local mgr=require('editor/drivePathEditor/splineMgr');
local a={schema_version=1,save_name='extended 90 degree data collection',
mapName=getCurrentLevelIdentifier(),tool=mgr.getToolPrefixStr(),vehicles={},splines={}};
local names={};for _,v in ipairs(getAllVehicles()) do
local p,q,f,u=v:getPosition(),v:getRotation(),v:getDirectionVector(),v:getDirectionVectorUp();
names[v:getID()]=v:getName();a.vehicles[#a.vehicles+1]={name=v:getName(),id=v:getID(),
model=v:getJBeamFilename(),config=core_vehicle_partmgmt.getConfigOfVehicle(v:getID()),
position_m={p.x,p.y,p.z},rotation_quat_xyzw={q.x,q.y,q.z,q.w},
forward={f.x,f.y,f.z},up={u.x,u.y,u.z}} end;
for _,s in ipairs(mgr.getDrivePathSplines()) do local d=mgr.serializeDrivePathSpline(s);
d.linked_vehicle_name=names[s.linkVehId];a.splines[#a.splines+1]=d end;return jsonEncode(a)"""


def lua_json(b, chunk):
    return json.loads(b.control.queue_lua_command(chunk, response=True))


def place_upright(b):
    encoded = json.dumps(PILOT_ROUTES)
    return lua_json(b, "local routes=jsonDecode([==[" + encoded + "]==]);" + """
local g=map.getGraphpath().positions;local a={};for name,r in pairs(routes) do
local v=scenetree.findObject(name);assert(v,'missing '..name);local p,t=g[r[1]],g[r[2]];
local dir=vec3(p.x-t.x,p.y-t.y,0);dir:normalize();local q=quatFromDir(dir,vec3(0,0,1));
v:setPositionRotation(p.x,p.y,p.z+0.35,q.x,q.y,q.z,q.w);
v:queueLuaCommand([[ai.setMode('disabled');input.event('throttle',0,1);
input.event('brake',1,1);input.event('parkingbrake',1,1)]]);
a[name]={position_m={p.x,p.y,p.z+0.35},rotation_quat_xyzw={q.x,q.y,q.z,q.w},
forward={-dir.x,-dir.y,0},up={0,0,1}} end;return jsonEncode(a)""")


def wake_physics(b, vehicles):
    b.control.resume()
    time.sleep(0.15)
    b.control.pause()
    for v in vehicles:
        v.sensors.poll()
    before = [float(v.state['time']) for v in vehicles]
    b.control.step(1)
    for v in vehicles:
        v.sensors.poll()
    if any(float(v.state['time']) <= t for v, t in zip(vehicles, before)):
        raise RuntimeError('Physics clock is frozen before trial; no launch allowed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=8301)
    args = parser.parse_args()
    batch = recorder.ROOT / 'runs' / ('west-coast-model-pilot-' + uuid.uuid4().hex[:10])
    batch.mkdir()
    print('EVIDENCE', batch, flush=True)
    b = BeamNGpy('127.0.0.1', 25252, quit_on_close=False, socket_timeout=10)
    vehicles, summaries, failures = [], [], []
    saved, selectors = {}, {}
    try:
        b.open(launch=False)
        b.control.pause()
        original = lua_json(b, CAPTURE)
        if original.get('mapName') != 'west_coast_usa':
            raise RuntimeError('West Coast USA must be loaded')
        recorder.write_json(batch / 'live-editor-before.json', original)
        native = lua_json(b, "return jsonEncode(jsonReadFile('/gameplay/data.json'))")
        recorder.write_json(batch / 'gameplay-data-original.json', native)
        if recorder.SNAPSHOT.exists():
            (batch / 'snapshot-before.json').write_bytes(recorder.SNAPSHOT.read_bytes())
        encoded = json.dumps(PILOT_ROUTES)
        geometry = lua_json(b, "local routes=jsonDecode([==[" + encoded + "]==]);" + """
local g=map.getGraphpath().positions;local out={};for name,r in pairs(routes) do
local nodes={};for i=1,#r-1 do local section=map.getPath(r[i],r[i+1]);
assert(#section>1,'No road connection');for j,n in ipairs(section) do
if #nodes==0 or nodes[#nodes]~=n then nodes[#nodes+1]=n end end end;
local points={};for _,n in ipairs(nodes) do local p=g[n];points[#points+1]={p.x,p.y,p.z} end;
out[name]={waypoints=r,path=nodes,positions=points} end;return jsonEncode(out)""")
        for name, route in geometry.items():
            points = route['positions']
            if 'junction1_wp12' not in route['path']:
                raise RuntimeError(f'{name} road path misses the junction')
            if max(p[2] for p in points) - min(p[2] for p in points) > 5:
                raise RuntimeError(f'{name} route changes road deck')
            if len(set(route['path'])) != len(route['path']):
                raise RuntimeError(f'{name} route doubles back')
        recorder.write_json(batch / 'pilot-route-geometry.json', geometry)
        poses = place_upright(b)
        for item in original['vehicles']:
            if item['name'] in poses:
                item.update(poses[item['name']])
        original['captured_utc'] = datetime.now(timezone.utc).isoformat()
        original['restore_note'] = ('User editor routes preserved exactly. Restore upright poses AFTER '
                                    'native editor linking. Pilot ground routes are stored separately in ' + str(batch))
        recorder.write_json(recorder.SNAPSHOT, original)
        recorder.write_json(batch / 'saved-scene-updated.json', original)
        baseline = {v['name']: v for v in original['vehicles']}
        assert set(recorder.IDS).issubset(baseline)
        b.settings.set_deterministic(60, speed_factor=4)
        for index, pair in enumerate(PAIRS):
            for v in vehicles:
                v.disconnect()
            vehicles = []
            saved = copy.deepcopy(baseline)
            selectors = {}
            details = {}
            for name, (model, config_path) in zip(recorder.IDS, pair):
                color = (0.1, 0.25, 0.95, 1) if name == 'clone12' else (0.08, 0.08, 0.08, 1)
                v = Vehicle(name, model=model, part_config=config_path,
                            color=color, color2=color, color3=color)
                if not b.vehicles.replace(v, old_vehicle=name):
                    raise RuntimeError(f'Could not replace {name} with {model}')
                vehicles.append(v)
                v.sensors.attach('damage', Damage())
                v.sensors.attach('electrics', Electrics())
                v.ai.set_mode('disabled')
                selectors[name] = recorder.selector_for(v)
                v.set_shift_mode('realistic_automatic')
                v.control(throttle=0, brake=1, parkingbrake=1, gear=selectors[name])
                details[name] = {'model': model, 'config_path': config_path}
            poses = place_upright(b)
            wake_physics(b, vehicles)
            configs = lua_json(b, "local a={};for _,v in ipairs(getAllVehicles()) do a[v:getName()]=core_vehicle_partmgmt.getConfigOfVehicle(v:getID()) end;return jsonEncode(a)")
            for v in vehicles:
                saved[v.vid].update(poses[v.vid])
                saved[v.vid]['model'] = v.model
                saved[v.vid]['config'] = configs[v.vid]
                if v.state['up'][2] < 0.95 or abs(v.state['dir'][2]) > 0.15:
                    raise RuntimeError(f'{v.vid} is not upright')
            seed = args.seed + index
            recorder.write_json(batch / f'trial-{index+1:02d}-vehicles.json',
                                {'seed': seed, 'vehicles': saved, 'choices': details})
            print('STARTING', index+1, details, flush=True)
            summary = recorder.run_trial(b, vehicles, saved, selectors, batch, index,
                65, 4, PILOT_ROUTES, random.Random(seed), 18, 30, 4, recorder.SNAPSHOT)
            summary['seed'] = seed
            summary['vehicle_choices'] = details
            summaries.append(summary)
            folder = batch / summary['trial_id']
            meta = recorder.read_json(folder / 'metadata.json')
            meta.update(seed=seed, vehicle_choices=details, pilot_route_geometry='../pilot-route-geometry.json')
            recorder.write_json(folder / 'metadata.json', meta)
            recorder.write_json(folder / 'summary.json', summary)
            errors = recorder.stop_and_restore(b, vehicles, saved,
                       {'selectors': selectors, 'positions': True})
            if errors:
                raise RuntimeError(str(errors))
            if summary['outcome'] in ('damage_sensor_threshold', 'launch_failed_no_motion'):
                print('STOPPING_BATCH', summary['outcome'], flush=True)
                break
    except BaseException as exc:
        failures.append(repr(exc))
        print('PILOT_FAILED', repr(exc), flush=True)
    finally:
        if b.connection:
            if vehicles:
                recorder.stop_and_restore(b, vehicles, saved,
                    {'selectors': selectors, 'positions': bool(saved) and all(v.vid in saved for v in vehicles)})
            b.control.pause()
            # Preserve the user's live route definitions, remapping only vehicle IDs.
            b.control.queue_lua_command("local m=require('editor/drivePathEditor/splineMgr');local ids={};for _,v in ipairs(getAllVehicles()) do ids[v:getName()]=v:getID() end;for _,s in ipairs(m.getDrivePathSplines()) do local n=s.name=='black' and 'clone13' or 'clone12';s.linkVehId=ids[n];s.isVehicleLink=ids[n]~=nil end",response=True)
            b.disconnect()
        recorder.write_json(batch / 'batch_summary.json', {
            'trials_requested': 3, 'trials_recorded': len(summaries),
            'summaries': summaries, 'failures': failures, 'training_ready': False,
            'note': 'User route save preserved; pilot uses audited ground-road waypoints. Junction labels provisional.'})
        print('EVIDENCE', batch, flush=True)


if __name__ == '__main__':
    main()
