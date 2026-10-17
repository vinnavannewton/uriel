"""Fresh seeded Small Grid pilots. No Uriel coordination or model training."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import shutil
import traceback
import time
import uuid

from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import Damage, Electrics

ROOT = Path(__file__).resolve().parents[1]
DURATION = 25
TELEMETRY_HZ = 60
FIELDS = ['run_id','frame_id','sim_time','elapsed','vehicle_id','vehicle_role',
          'x','y','z','yaw','pitch','roll','vx','vy','vz','speed','ax','ay','az',
          'throttle','brake','steering','gear','ai_mode','target_speed','route_id','start_delay',
          'nearest_vehicle_id','relative_distance','relative_speed','damage',
          'verified_contact','lane_state','conflict_zone_state','route_deviation',
          'front_progress','rear_progress','bbox_json']


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False))


def configuration(seed, background):
    rng=random.Random(seed)
    result=[]
    defs=[('uriel_red','subject','x',0,-40,0),('uriel_blue','subject','y',0,-40,round(rng.uniform(0,2),3))]
    # Fixed four background route identities; randomize only along-route progress.
    for i,(axis,lane) in enumerate([('x',-12),('x',12),('y',-12),('y',12)]):
        defs.append((f'traffic_{i+1}','background',axis,lane,round(rng.uniform(-65,-45),3),round(rng.uniform(0,2),3)))
    for i,(name,role,axis,lane,progress,delay) in enumerate(defs):
        target=round(rng.uniform(5,10) if role=='subject' else rng.uniform(4,8),3)
        initial=round(rng.uniform(0,2),3)
        result.append(dict(vehicle_id=name,role=role,axis=axis,lane=lane,progress=progress,
            start_delay=delay,target_speed=target,initial_speed_requested=initial,
            model='etkc' if i<2 else background[i-2]['model'],
            source_background_id=None if i<2 else background[i-2]['name'],
            route_id=f'{axis}_lane_{lane}',color=(1,0,0,1) if i==0 else (0,.15,1,1) if i==1 else (.5,.5,.5,1)))
    return result


def position(c, progress=None):
    p=c['progress'] if progress is None else progress
    return (p,c['lane'],.5) if c['axis']=='x' else (c['lane'],p,.5)


def ai_line(c):
    return [dict(pos=position(c,p),speed=c['target_speed']) for p in (c['progress'], -20,0,20,60,100)]


def box_metrics(points, c):
    axis=0 if c['axis']=='x' else 1
    other=1-axis
    front=max(p[axis] for p in points); rear=min(p[axis] for p in points)
    lateral_min=min(p[other] for p in points); lateral_max=max(p[other] for p in points)
    overlap=front>=-3 and rear<=3 and lateral_max>=-3 and lateral_min<=3
    return front,rear,overlap


def derive_events(rows, configs):
    events=[];outcomes={}
    for c in configs:
        name=c['vehicle_id'];rr=[r for r in rows if r['vehicle_id']==name]
        entry=None;clearance=None;stopline=None;stopped=False;deviated=False
        baseline=rr[0]['damage'];last_damage=baseline;ambiguous=False
        for i,r in enumerate(rr):
            def add(kind,**extra):
                events.append(dict(run_id=r['run_id'],vehicle_id=name,event=kind,
                    sim_time=r['sim_time'],elapsed=r['elapsed'],frame_id=r['frame_id'],**extra))
            if r['damage']>last_damage+1e-6:
                add('damage_increase',delta=r['damage']-last_damage,verified_contact=None)
                last_damage=r['damage'];ambiguous=True
            if r['front_progress']>=-6 and stopline is None:
                stopline=r['elapsed'];add('stop_line_crossing',geometry='virtual plane at progress -6m')
            if r['conflict_zone_state']=='overlap' and entry is None:
                entry=r['elapsed'];add('front_boundary_entry',quality='ambiguous_damage' if ambiguous else 'spawn_OOBB_proxy')
            if entry is not None and clearance is None and r['rear_progress']>3 and r['conflict_zone_state']!='overlap':
                clearance=r['elapsed'];add('rear_boundary_clearance',quality='ambiguous_damage' if ambiguous else 'spawn_OOBB_proxy')
                add('completed_crossing',contact_status='unknown')
            if not stopped and entry is None and r['elapsed']>=.5 and r['front_progress']< -3 and r['speed']<.2:
                start=i
                while start>0 and r['elapsed']-rr[start]['elapsed']<.5:
                    start-=1
                if r['elapsed']-rr[start]['elapsed']>=.5-.00051 and all(x['speed']<.2 for x in rr[start:i+1]):
                    stopped=True;add('stopped_before_entry',minimum_duration_seconds=.5)
            if r['route_deviation'] and not deviated:
                deviated=True;add('route_deviation',threshold_m=2)
        if entry is None:
            r=rr[-1];events.append(dict(run_id=r['run_id'],vehicle_id=name,event='non_arrival',
                sim_time=r['sim_time'],elapsed=r['elapsed'],censored=True))
        outcomes[name]=dict(entry_seconds=entry,clearance_seconds=clearance,
            arrival_censored=entry is None,clearance_censored=clearance is None,
            stopped_before_entry=stopped,route_deviation=deviated,
            damage_increase=max(r['damage'] for r in rr)-baseline,
            verified_contact=None,contact_status='unavailable',
            geometry_quality='ambiguous_damage' if ambiguous else 'spawn_OOBB_proxy',
            max_speed=max(r['speed'] for r in rr),samples=len(rr))
    return sorted(events,key=lambda e:e['sim_time']),outcomes


def validate(rows,configs,outcomes,duration=DURATION,hz=TELEMETRY_HZ):
    issues=[];missing={};ids={r['vehicle_id'] for r in rows}
    if ids!={c['vehicle_id'] for c in configs}:issues.append('vehicle ID mismatch')
    for c in configs:
        rr=[r for r in rows if r['vehicle_id']==c['vehicle_id']]
        if len(rr)!=round(duration*hz)+1:issues.append('sample count '+c['vehicle_id'])
        for a,b in zip(rr,rr[1:]):
            if abs(b['sim_time']-a['sim_time']-1/hz)>.00051:issues.append('timestamp gap '+c['vehicle_id']);break
        if rr and any(abs((r['sim_time']-rr[0]['sim_time'])-i/hz)>.00051 for i,r in enumerate(rr)):
            issues.append('sample phase drift '+c['vehicle_id'])
        for key in FIELDS:
            n=sum(r.get(key) is None for r in rr)
            if n:missing.setdefault(c['vehicle_id'],{})[key]=n
        o=outcomes[c['vehicle_id']]
        entry=next((r['elapsed'] for r in rr if r['conflict_zone_state']=='overlap'),None)
        if entry!=o['entry_seconds']:issues.append('entry label mismatch')
        if o['clearance_seconds'] is not None:
            r=next(x for x in rr if x['elapsed']==o['clearance_seconds'])
            if r['rear_progress']<=3:issues.append('clearance label mismatch')
        for r in rr:
            if not all(math.isfinite(r[k]) for k in ('sim_time','x','y','z','vx','vy','vz','speed','damage')):
                issues.append('nonfinite telemetry');break
    return dict(status='PASS_WITH_LIMITATIONS' if not issues else 'FAIL',issues=issues,
        missing_fields=missing,sample_count=len(rows),target_hz=hz,
        geometry='virtual geometry configured; physical body occupancy uses spawn OOBB proxy',
        contact_detection='unavailable; damage is separate evidence',
        acceleration='first sample null; finite differences thereafter',outcomes=outcomes)


def collect(b, folder, run_id, seed, background, pool, duration=DURATION, hz=TELEMETRY_HZ, speed=2.0):
    configs=configuration(seed,background)
    geometry=dict(map='smallgrid',virtual_intersection=True,zone={'x':[-3,3],'y':[-3,3]},
        virtual_lane_half_width=1.8,route_deviation_reference_threshold_m=2,stop_line_progress=-6,
        subject_route_angle_degrees=90,
        body_detector='world spawn OOBB corners projected on fixed route axis; first sampled events, no interpolation',
        limitations=['Spawn OOBB is not a calibrated deforming body contact surface.',
            'Damage or route deviation can make entry/clearance labels ambiguous.',
            'Background routes at offsets +/-12m do not enter the central zone; their non-arrival there is not a failure.'],
        routes=[dict(route_id=c['route_id'],axis=c['axis'],lane=c['lane']) for c in configs])
    meta=dict(run_id=run_id,seed=seed,status='preparing',maximum_duration_seconds=duration,
        sampling=dict(deterministic_step_hz=hz,steps_per_sample=1,target_hz=hz),configuration=configs,
        requested_speed_multiplier=speed,
        speed_control='Fixed simulation stepping paced toward requested wall-clock multiplier; actual throughput is measured, not guaranteed.',
        beamngpy=importlib.metadata.version('beamngpy'),geometry_verified='virtual coordinates only; body proxy uncalibrated',
        control='BeamNG speed-polyline AI; no Uriel controller',
        shift_mode='realistic_automatic',
        initial_speed_semantics='Requested using supported set_velocity over one physics frame; measured initial speed saved. Delayed cars brake until AI launch.',
        randomization_bounds=dict(subject_target_mps=[5,10],background_target_mps=[4,8],initial_speed_mps=[0,2],
            blue_delay_seconds=[0,2],background_delay_seconds=[0,2],background_progress_m=[-65,-45]),
        unavailable=['verified vehicle contact detector','real road lanes/signals on Small Grid'])
    dump(folder/'metadata.json',meta);dump(folder/'geometry.json',geometry)
    (folder/'events.jsonl').touch();(folder/'telemetry.csv').touch()
    vehicles=[];event_rows=[]
    try:
        s=Scenario('smallgrid','uriel_fresh_'+uuid.uuid4().hex[:8])
        for i,c in enumerate(configs):
            config=None if i<2 else background[i-2].get('config')
            v=Vehicle(c['vehicle_id'],model=c['model'],color=c['color'],part_config=config)
            v.sensors.attach('damage',Damage());v.sensors.attach('electrics',Electrics())
            q=(0,0,-math.sqrt(.5),math.sqrt(.5)) if c['axis']=='x' else (0,0,1,0)
            s.add_vehicle(v,pos=position(c),rot_quat=q);vehicles.append(v)
        s.make(b);b.scenario.load(s);b.scenario.start();b.control.pause();b.settings.set_deterministic(60)
        for v in vehicles:
            v.ai.set_mode('disabled');v.set_shift_mode('realistic_automatic');v.control(throttle=0,brake=1,parkingbrake=1,gear=1)
        b.control.step(120)
        initial={};dimensions={}
        for v,c in zip(vehicles,configs):
            v.sensors.poll();st=v.state
            meta.setdefault('observed_setup_state',{})[v.vid]=dict(st);dump(folder/'metadata.json',meta)
            if math.dist(st['pos'][:2],position(c)[:2])>1:raise RuntimeError('Starting position mismatch '+v.vid)
            expected=st['dir'][0 if c['axis']=='x' else 1]
            if expected<.99:raise RuntimeError('Starting heading mismatch '+v.vid)
            if v.sensors['damage'].get('damage',0)>1:raise RuntimeError('Damaged initial vehicle '+v.vid)
            bbox=v.get_bbox();points=list(bbox.values())
            axis=0 if c['axis']=='x' else 1
            dimensions[v.vid]=dict(length=max(p[axis] for p in points)-min(p[axis] for p in points),
                width=max(p[1-axis] for p in points)-min(p[1-axis] for p in points),
                height=max(p[2] for p in points)-min(p[2] for p in points))
            v.control(throttle=0,brake=0,parkingbrake=0)
            v.set_velocity(c['initial_speed_requested'],dt=1/60)
        b.control.step(1)
        for v,c in zip(vehicles,configs):
            v.sensors.poll();initial[v.vid]=dict(v.state)
            measured=math.sqrt(sum(x*x for x in v.state['vel']));c['initial_speed_measured']=measured
            if abs(measured-c['initial_speed_requested'])>.6:raise RuntimeError('Initial speed initialization mismatch '+v.vid)
            v.control(throttle=0,brake=1,parkingbrake=1)
        if abs(dimensions['uriel_red']['length']-dimensions['uriel_blue']['length'])>.05:raise RuntimeError('Subject dimensions differ')
        meta.update(status='recording',verified_initial_state=initial,vehicle_dimensions=dimensions)
        geometry['measured_initial_vehicle_dimensions']=dimensions
        dump(folder/'geometry.json',geometry);dump(folder/'metadata.json',meta)
        ids=[v.vid for v in vehicles]
        lua='local out={}; for _,name in ipairs('+ '{'+','.join(json.dumps(n) for n in ids)+'}' +') do local v=scenetree.findObject(name); local box=v:getSpawnWorldOOBB(); local p={}; for i=0,7 do local a=box:getPoint(i); p[#p+1]={a.x,a.y,a.z} end; out[name]=p end; return jsonEncode(out)'
        b.settings.set_deterministic(hz)
        # Keep the deterministic frame limiter enabled: disabling it makes the
        # installed simulator's manual-step intervals drift. Small fixed steps
        # preserve every observation; pacing requests a wall-clock target only.
        active=set();rows=[];previous={};start=None
        recording_wall_start=time.perf_counter()
        print('START',run_id,'seed',seed,flush=True)
        with (folder/'telemetry.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
            for frame in range(round(duration*hz)+1):
                elapsed=frame/hz
                if frame:
                    remaining=recording_wall_start+elapsed/speed-time.perf_counter()
                    if remaining>0:time.sleep(remaining)
                    b.control.step(1)
                for v,c in zip(vehicles,configs):
                    if v.vid not in active and elapsed+1e-9>=c['start_delay']:
                        v.control(throttle=0,brake=0,parkingbrake=0);v.ai.set_line(ai_line(c))
                        active.add(v.vid);event_rows.append(dict(run_id=run_id,vehicle_id=v.vid,event='AI_launch_command',frame_id=frame,elapsed=elapsed,requested_delay=c['start_delay']))
                # Each vehicle has an independent socket; all polling finishes before physics advances.
                list(pool.map(lambda v:v.sensors.poll(),vehicles))
                boxes=json.loads(b.control.queue_lua_command(lua,response=True))
                if start is None:start=vehicles[0].state['time']
                for v,c in zip(vehicles,configs):
                    st=v.state;p=st['pos'];vel=st['vel'];direction=st['dir'];up=st['up'];e=v.sensors['electrics']
                    acc=[None]*3
                    if v.vid in previous:
                        old=previous[v.vid];dt=st['time']-old['time']
                        # Some manually advanced frames can report the same
                        # simulator timestamp. Preserve that sample; acceleration
                        # is undefined for a zero-time interval.
                        if dt>0:acc=[(a-z)/dt for a,z in zip(vel,old['vel'])]
                    previous[v.vid]={'time':st['time'],'vel':vel}
                    others=[u for u in vehicles if u.vid!=v.vid]
                    nearest=min(others,key=lambda u:math.dist(p,u.state['pos']))
                    distance=math.dist(p,nearest.state['pos'])
                    rv=[a-z for a,z in zip(nearest.state['vel'],vel)]
                    delta=[a-z for a,z in zip(nearest.state['pos'],p)]
                    relative=sum(a*z for a,z in zip(rv,delta))/distance if distance>0 else None
                    front,rear,overlap=box_metrics(boxes[v.vid],c)
                    other_axis=1 if c['axis']=='x' else 0
                    lateral=p[other_axis]-c['lane'];deviation=abs(lateral)>2
                    right=(direction[1],-direction[0],0)
                    roll=math.atan2(sum(a*z for a,z in zip(up,right)),up[2])
                    row=dict(run_id=run_id,frame_id=frame,sim_time=st['time'],elapsed=st['time']-start,
                        vehicle_id=v.vid,vehicle_role=c['role'],x=p[0],y=p[1],z=p[2],
                        yaw=math.atan2(direction[1],direction[0]),pitch=math.atan2(direction[2],math.hypot(*direction[:2])),roll=roll,
                        vx=vel[0],vy=vel[1],vz=vel[2],speed=math.sqrt(sum(a*a for a in vel)),ax=acc[0],ay=acc[1],az=acc[2],
                        throttle=e.get('throttle'),brake=e.get('brake'),steering=e.get('steering'),gear=e.get('gear_index',e.get('gear')),
                        ai_mode='speed_polyline_commanded' if v.vid in active else 'disabled_braked',target_speed=c['target_speed'],
                        route_id=c['route_id'],start_delay=c['start_delay'],nearest_vehicle_id=nearest.vid,
                        relative_distance=distance,relative_speed=relative,damage=v.sensors['damage'].get('damage'),verified_contact=None,
                        lane_state='within_virtual_lane' if abs(lateral)<=1.8 else 'outside_virtual_lane',
                        conflict_zone_state='overlap' if overlap else 'outside',route_deviation=deviation,
                        front_progress=front,rear_progress=rear,bbox_json=json.dumps(boxes[v.vid],separators=(',',':')))
                    writer.writerow(row);rows.append(row)
                f.flush()
                if frame and frame%(hz*10)==0:
                    elapsed_wall=time.perf_counter()-recording_wall_start
                    print('PROGRESS',run_id,round(elapsed,1),'sim s; achieved',round(elapsed/elapsed_wall,2),'x',flush=True)
        recording_wall_seconds=time.perf_counter()-recording_wall_start
        simulation_seconds=rows[-1]['sim_time']-rows[0]['sim_time']
        meta['timing']=dict(simulation_seconds=simulation_seconds,recording_wall_seconds=recording_wall_seconds,
            achieved_speed_multiplier=simulation_seconds/recording_wall_seconds,
            target_speed_reached=simulation_seconds/recording_wall_seconds>=speed*.95,
            measured_hz=round(duration*hz)/simulation_seconds,includes_setup=False)
        print('RATE',run_id,'requested',speed,'x; achieved',round(meta['timing']['achieved_speed_multiplier'],3),'x;',
            'speed target reached' if meta['timing']['target_speed_reached'] else 'below speed target; all samples retained',flush=True)
        events,outcomes=derive_events(rows,configs)
        for event in event_rows:
            sample=rows[event['frame_id']*len(configs)]
            event['sim_time']=sample['sim_time'];event['elapsed']=sample['elapsed']
        with (folder/'events.jsonl').open('w') as f:
            for event in sorted(events+event_rows,key=lambda e:e['sim_time']):f.write(json.dumps(event,allow_nan=False)+'\n')
        report=validate(rows,configs,outcomes,duration,hz);dump(folder/'validation_report.json',report)
        meta.update(status='complete' if report['status']!='FAIL' else 'failed_validation',outcomes=outcomes,
                    sample_count=len(rows),quality=report['status'])
        dump(folder/'metadata.json',meta)
        print('COMPLETE',run_id,json.dumps({n:o for n,o in outcomes.items() if n in ('uriel_red','uriel_blue')}),flush=True)
        return meta
    except BaseException as error:
        meta.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=repr(error),traceback=traceback.format_exc())
        dump(folder/'metadata.json',meta);dump(folder/'validation_report.json',dict(status='FAIL',reason=repr(error)))
        print('FAILED',run_id,repr(error),flush=True)
        if isinstance(error,(KeyboardInterrupt,SystemExit)):raise
        return meta
    finally:
        b.control.pause()
        for v in vehicles:
            try:v.ai.set_mode('disabled');v.control(throttle=0,brake=1,parkingbrake=1)
            except Exception:pass


def parse_args(argv=None):
    parser=argparse.ArgumentParser(description="Seeded 90-degree Small Grid crossing: two ETK cars, four traffic cars and recorded telemetry.")
    parser.add_argument('--trials',type=int,default=3,help='Number of trials (default: 3)')
    parser.add_argument('--speed',type=float,default=2.0,help='Requested simulation seconds per wall second; actual speed is measured (default: 2)')
    parser.add_argument('--telemetry-hz',type=int,choices=[30,60,120],default=60,help='Samples per SIMULATION second (default: 60)')
    parser.add_argument('--duration',type=float,default=25,help='Simulation seconds per trial (default: 25)')
    parser.add_argument('--seed',type=int,default=903101,help='First seed; successive runs increment it by one')
    parser.add_argument('--host',default='localhost')
    parser.add_argument('--port',type=int,default=25252)
    parser.add_argument('--output',type=Path,default=ROOT/'uriel_experiment',help='Parent directory; a new experiment UUID is always created')
    parser.add_argument('--background-config',type=Path,default=ROOT/'scenarios'/'smallgrid_background_configs.json')
    args=parser.parse_args(argv)
    if args.trials<1:parser.error('--trials must be positive')
    if not math.isfinite(args.speed) or args.speed<=0:parser.error('--speed must be finite and positive')
    if not math.isfinite(args.duration) or args.duration<=0:parser.error('--duration must be finite and positive')
    if abs(args.duration*args.telemetry_hz-round(args.duration*args.telemetry_hz))>1e-7:
        parser.error('--duration must contain a whole number of telemetry intervals')
    return args


def main():
    args=parse_args()
    backgrounds=json.loads(args.background_config.read_text())
    if len(backgrounds)!=4 or not all(c.get('model') and 'name' in c for c in backgrounds):
        raise ValueError('Background config must describe exactly four named vehicle models')
    exp=args.output/('experiment_'+uuid.uuid4().hex)
    exp.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,exp/'collector_source.py')
    dump(exp/'source_background_configs.json',backgrounds)
    manifest=dict(experiment_id=exp.name,first_seed=args.seed,trials_requested=args.trials,
        requested_speed_multiplier=args.speed,telemetry_hz=args.telemetry_hz,duration_seconds=args.duration,
        collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        dimensions_fixed_by='same model/config on every reload; measured dimensions per run',status='running')
    dump(exp/'experiment.json',manifest)
    print('EXPERIMENT',exp,flush=True)
    b=BeamNGpy(args.host,args.port);results=[];connected=False;settings_before=None
    try:
        b.open(launch=False);connected=True
        settings_before=json.loads(b.control.queue_lua_command(
            "return jsonEncode({fpsLimit=settings.getValue('fpsLimit'),fpsLimitEnabled=settings.getValue('fpsLimitEnabled'),fpsLimitBackgroundEnabled=settings.getValue('fpsLimitBackgroundEnabled')})",response=True))
        with ThreadPoolExecutor(max_workers=6) as pool:
            for i in range(args.trials):
                run_id=f'fresh_{i+1:03d}';folder=exp/run_id;folder.mkdir(exist_ok=False)
                results.append(collect(b,folder,run_id,args.seed+i,backgrounds,pool,args.duration,args.telemetry_hz,args.speed))
                write_summary(exp,results)
        manifest['status']='complete' if all(r['status']=='complete' for r in results) else 'completed_with_failures'
    except BaseException as error:
        manifest.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',error=repr(error))
        raise
    finally:
        manifest['runs']=[r['run_id'] for r in results]
        dump(exp/'experiment.json',manifest)
        if connected:
            try:
                b.control.pause();b.settings.set_deterministic(60)
                if settings_before is not None:
                    lua='local values=jsonDecode('+json.dumps(json.dumps(settings_before))+');for k,v in pairs(values) do settings.setValue(k,v) end'
                    b.control.queue_lua_command(lua,response=True)
            finally:b.disconnect()
        print('FINISHED',exp,manifest['status'],flush=True)
    return 0 if manifest['status']=='complete' else 1


def write_summary(exp,results):
    fields=['run_id','seed','status','quality','sample_count','red_initial_speed','blue_initial_speed','red_target','blue_target','blue_delay','background_parameters','red_entry','blue_entry','red_clearance','blue_clearance','red_damage_increase','blue_damage_increase','contact_evidence','telemetry_hz','requested_speed','achieved_speed','recording_wall_seconds']
    with (exp/'trial_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for m in results:
            a,z=m['configuration'][:2];o=m.get('outcomes',{});r=o.get('uriel_red',{});b=o.get('uriel_blue',{})
            w.writerow(dict(run_id=m['run_id'],seed=m['seed'],status=m['status'],quality=m.get('quality'),sample_count=m.get('sample_count'),
                red_initial_speed=a.get('initial_speed_measured'),blue_initial_speed=z.get('initial_speed_measured'),
                red_target=a['target_speed'],blue_target=z['target_speed'],blue_delay=z['start_delay'],background_parameters=json.dumps(m['configuration'][2:]),
                red_entry=r.get('entry_seconds'),blue_entry=b.get('entry_seconds'),red_clearance=r.get('clearance_seconds'),blue_clearance=b.get('clearance_seconds'),
                red_damage_increase=r.get('damage_increase'),blue_damage_increase=b.get('damage_increase'),contact_evidence='unavailable; inspect damage separately',telemetry_hz=m['sampling']['target_hz'],
                requested_speed=m['requested_speed_multiplier'],achieved_speed=m.get('timing',{}).get('achieved_speed_multiplier'),
                recording_wall_seconds=m.get('timing',{}).get('recording_wall_seconds')))

if __name__=='__main__':raise SystemExit(main())
