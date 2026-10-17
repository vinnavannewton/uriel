"""Record three road-following trials in the user's current West Coast setup."""
import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import uuid
import time
import sys
from beamngpy import BeamNGpy
from beamngpy.sensors import Damage, Electrics


def main():
    root=Path(__file__).resolve().parent/'runs'/('traffic-'+uuid.uuid4().hex)
    root.mkdir(parents=True)
    shutil.copyfile(__file__,root/'collector_source.py')
    meta={'status':'running','mode':'BeamNG-road-AI-with-background-traffic',
          'beamngpy':importlib.metadata.version('beamngpy'),
          'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'requested_background_vehicles':4,'duration_seconds':30,'sample_seconds':.1,
          'zone':{'centre':[-454,146,100],'radius_xy_m':8,'height_tolerance_m':4},
          'zone_definition':'approximate junction front-reference disk; not calibrated body occupancy',
          'targets':{'thePlayer':'DR193_2','clone':'DR602_5'},'trials':[],
          'limitations':['Traffic RNG is not seeded; trials are not paired deterministic comparisons.',
          'Damage increase is not a complete contact detector or collision attribution.',
          'Nearby traffic exposure is measured; spawning traffic does not guarantee an encounter.',
          'No Uriel coordinator, ML training or clearance acceptance.']}
    def save(): (root/'metadata.json').write_text(json.dumps(meta,indent=2))
    save(); print('OUTPUT',root,flush=True)
    b=BeamNGpy('localhost',25252); connected=False; tracked={}
    try:
        b.open(launch=False); connected=True; b.control.pause(); b.settings.set_deterministic(60)
        meta['map']=b.control.queue_lua_command('return getMissionFilename()',response=True)
        if 'west_coast_usa' not in meta['map']: raise RuntimeError('Current map is not West Coast USA')
        info=b.vehicles.get_current_info()
        initial={}
        for name in ('thePlayer','clone'):
            if name not in info: raise RuntimeError('Missing subject '+name)
        # Save full configurations on disk, not in console or wiki.
        (root/'initial_vehicle_configs.json').write_text(json.dumps(info,indent=2))
        vehicles=b.vehicles.get_current()
        for name in ('thePlayer','clone'):
            v=vehicles[name]; v.connect(b); v.sensors.poll()
            initial[name]={'model':v.model,'state':dict(v.state)}
        if len(sys.argv)>1:
            initial=json.loads(Path(sys.argv[1]).read_text())['initial_subjects']
            meta['reference_setup']=str(Path(sys.argv[1]).resolve())
        meta['initial_subjects']=initial; save()
        if len(vehicles)<6:
            b.traffic.spawn(max_amount=4,police_ratio=0,extra_amount=0,parked_amount=0)
        for attempt in range(100):
            b.control.pause()
            vehicles=b.vehicles.get_current()
            if len(vehicles)>=6:break
            b.control.step(6)
            time.sleep(.1)
        if len(vehicles)<6:raise RuntimeError('Four background vehicles not ready')
        b.traffic.stop(stop=True)
        for name,v in vehicles.items():
            v.connect(b); v.sensors.attach('damage',Damage()); v.sensors.attach('electrics',Electrics())
            tracked[name]=v
        subjects=['thePlayer','clone']; background=[n for n in tracked if n not in subjects]
        meta['background_ids']=background
        if not background: raise RuntimeError('No background traffic vehicles spawned')
        save(); print('TRAFFIC',background,flush=True)
        fields=['trial','vehicle','role','sim_time','elapsed','x','y','z','front_x','front_y','front_z',
                'vx','vy','vz','speed','ax','ay','az','dir_x','dir_y','dir_z',
                'qx','qy','qz','qw','throttle','brake','steering','damage','front_in_zone']
        for trial,(speed_a,speed_b) in enumerate([(8,8),(6,8),(8,6)],1):
            folder=root/f'trial-{trial}'; folder.mkdir()
            cfg={'trial':trial,'status':'running','speed_limits_mps':{'thePlayer':speed_a,'clone':speed_b}}
            meta['trials'].append(cfg);save()
            b.control.pause()
            b.traffic.start([tracked[n] for n in background])
            b.traffic.reset()
            for name in subjects:
                v=tracked[name];v.ai.set_mode('disabled')
                st=initial[name]['state']
                if not v.teleport(st['pos'],rot_quat=st['rotation'],reset=True):raise RuntimeError('Teleport failed '+name)
                v.control(throttle=0,brake=1,parkingbrake=1)
            b.control.step(30)
            cfg['verified_start_positions']={}
            for name in subjects:
                v=tracked[name];v.sensors.poll()
                actual=v.state['pos'];expected=initial[name]['state']['pos']
                cfg['verified_start_positions'][name]=actual
                if math.dist(actual,expected)>1:raise RuntimeError('Start position drift '+name+' '+str(actual))
                if v.sensors['damage'].get('damage',0)>1:raise RuntimeError('Damaged start '+name)
            save()
            for name,speed in zip(subjects,(speed_a,speed_b)):
                v=tracked[name];v.control(throttle=0,brake=0,parkingbrake=0)
                v.ai.drive_in_lane(True);v.ai.set_waypoint(meta['targets'][name]);v.ai.set_speed(speed,mode='limit')
            rows=[]; previous={}; start=None
            print('START',trial,flush=True)
            with (folder/'telemetry.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
                for sample in range(301):
                    if sample: b.control.step(6)
                    for name,v in tracked.items():
                        v.sensors.poll();st=v.state
                        if start is None:start=st['time']
                        p,front,vel,direction,quat=[st[k] for k in ('pos','front','vel','dir','rotation')]
                        e=v.sensors['electrics']; elapsed=st['time']-start
                        acc=[None]*3
                        if name in previous:
                            old=previous[name];dt=st['time']-old['time']
                            if dt>0:acc=[(a-c)/dt for a,c in zip(vel,old['vel'])]
                        previous[name]={'time':st['time'],'vel':vel}
                        r=dict(trial=trial,vehicle=name,role='subject' if name in subjects else 'background',
                            sim_time=st['time'],elapsed=elapsed,speed=math.sqrt(sum(a*a for a in vel)),
                            throttle=e.get('throttle'),brake=e.get('brake'),steering=e.get('steering'),
                            damage=v.sensors['damage'].get('damage'),
                            front_in_zone=math.hypot(front[0]+454,front[1]-146)<=8 and abs(front[2]-100)<=4)
                        for keys,values in [(('x','y','z'),p),(('front_x','front_y','front_z'),front),
                            (('vx','vy','vz'),vel),(('ax','ay','az'),acc),(('dir_x','dir_y','dir_z'),direction),
                            (('qx','qy','qz','qw'),quat)]:r.update(zip(keys,values))
                        w.writerow(r); rows.append(r)
                    f.flush()
            summary={}
            by_sample={}
            for r in rows:by_sample.setdefault(round(r['elapsed'],4),{})[r['vehicle']]=r
            arrivals={}
            for name in subjects:
                rr=[r for r in rows if r['vehicle']==name]
                arrival=next((r['elapsed'] for r in rr if r['front_in_zone']),None);arrivals[name]=arrival
                separation=[];exposed=set()
                for group in by_sample.values():
                    r=group[name]
                    for bg in background:
                        t=group[bg];d=math.dist([r[k] for k in ('x','y','z')],[t[k] for k in ('x','y','z')])
                        separation.append(d)
                        if d<=50:exposed.add(bg)
                summary[name]={'arrival_seconds':arrival,'censored':arrival is None,
                    'travel_distance_from_start_m':math.dist([rr[0][k] for k in ('x','y','z')],[rr[-1][k] for k in ('x','y','z')]),
                    'max_speed_mps':max(r['speed'] for r in rr),
                    'damage_increase':max(r['damage'] for r in rr)-rr[0]['damage'],
                    'initial_damage':rr[0]['damage'],
                    'nearest_background_reference_distance_m':min(separation),
                    'background_vehicles_within_50m':sorted(exposed),'samples':len(rr)}
            damage={n:max(r['damage'] for r in rows if r['vehicle']==n)-next(r['damage'] for r in rows if r['vehicle']==n) for n in tracked}
            (folder/'summary.json').write_text(json.dumps({'subjects':summary,'damage_increase_all_vehicles':damage},indent=2))
            with (folder/'arrival_labels.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['trial','vehicle','sim_time','remaining_seconds','censored']);w.writeheader()
                for r in rows:
                    if r['vehicle'] not in subjects:continue
                    arrival=arrivals[r['vehicle']]
                    if arrival is not None and r['elapsed']>arrival:continue
                    w.writerow(dict(trial=trial,vehicle=r['vehicle'],sim_time=r['sim_time'],
                        remaining_seconds=None if arrival is None else arrival-r['elapsed'],censored=arrival is None))
            cfg.update(status='complete',summary=summary,telemetry_rows=len(rows));save()
            for name in subjects:
                v=tracked[name];v.ai.set_mode('disabled');v.control(throttle=0,brake=1,parkingbrake=1)
            print('COMPLETE',trial,json.dumps(summary),flush=True)
        meta['status']='complete'
    except BaseException as error:
        meta.update(status='failed',error=repr(error));raise
    finally:
        save()
        if connected:
            try:b.control.pause()
            finally:b.disconnect()
        print('SAVED',root,meta['status'],flush=True)

if __name__=='__main__':main()
