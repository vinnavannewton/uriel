#!/usr/bin/env python3
"""One measured, matched-car perpendicular crossing with local Rust hybrid control."""
import argparse,json,math,os,subprocess,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from beamngpy import BeamNGpy,Scenario,Vehicle
from beamngpy.sensors import Damage,Electrics
from crossing_client import CrossingClient
from collect_west_coast_arrival_trials import selector_for

ROOT=Path(__file__).resolve().parents[1]

def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',action='store_true');parser.add_argument('--dashboard-url',default='http://127.0.0.1:3000',help='read-only dashboard/API origin');parser.add_argument('--no-dashboard',action='store_true');args=parser.parse_args()
 out=ROOT/'runs'/(('grid-baseline-' if args.baseline else 'grid-hybrid-')+uuid.uuid4().hex[:10]);out.mkdir()
 print('EVIDENCE',out,flush=True)
 scenario={'id':'matched-grid-hybrid','label':'Matched perpendicular Grid Plane hybrid trial','zone_half_extent_m':3.,'margin_m':2.,'max_speed_mps':8.,'routes':[
  {'id':'red','points_xy_m':[[-80.,0.],[80.,0.]],'zone_center_s_m':80.,'yield_s_m':50.,'commit_s_m':65.},
  {'id':'blue','points_xy_m':[[0.,-80.],[0.,80.]],'zone_center_s_m':80.,'yield_s_m':50.,'commit_s_m':65.}]}
 dump(out/'scenario.json',scenario)
 dashboard_url=args.dashboard_url.rstrip('/')
 b=BeamNGpy('127.0.0.1',25252,quit_on_close=False,socket_timeout=20)
 processes=[];logs=[];vehicles=[];client=None;rows=[];summary={'outcome':'setup_failed','server_location':'none' if args.baseline else 'local','mode':'baseline' if args.baseline else 'hybrid','equal_requested_speed_mps':8.,'matching_config':'vehicles/vivace/vivace_160_DCT.pc','initial_speed_mps':0.,'limitations':'Measured body proxy clearance and damage; not a general collision guarantee. LinuxONE latency exceeds request budget.'}
 try:
  b.open(launch=False);b.control.pause()
  before=b.control.queue_lua_command("local a={map=getCurrentLevelIdentifier(),vehicles={}};for _,v in ipairs(getAllVehicles()) do local p=v:getPosition();a.vehicles[#a.vehicles+1]={name=v:getName(),model=v:getJBeamFilename(),pos={p.x,p.y,p.z}} end;return jsonEncode(a)",response=True)
  (out/'scene-before.json').write_text(before)
  # Fresh scenario changes the loaded map; the saved West Coast project remains on disk.
  scene=Scenario('smallgrid','uriel_hybrid_'+uuid.uuid4().hex[:8])
  for name,pos,q,color in [('red',(-40,0,.35),(0,0,-math.sqrt(.5),math.sqrt(.5)),(.95,.05,.03,1)),('blue',(0,-40,.35),(0,0,1,0),(.05,.2,.95,1))]:
   v=Vehicle(name,model='vivace',part_config='vehicles/vivace/vivace_160_DCT.pc',color=color)
   v.sensors.attach('damage',Damage());v.sensors.attach('electrics',Electrics());scene.add_vehicle(v,pos=pos,rot_quat=q);vehicles.append(v)
  scene.make(b);b.scenario.load(scene);b.scenario.start();b.control.pause();b.settings.set_deterministic(60,speed_factor=1)
  selectors={}
  for v in vehicles:
   v.ai.set_mode('disabled');v.set_shift_mode('realistic_automatic');selectors[v.vid]=selector_for(v);v.control(throttle=0,brake=1,parkingbrake=1,gear=selectors[v.vid])
  b.control.resume();time.sleep(.4);b.control.pause();b.control.step(30)
  dimensions={};initial={}
  for v in vehicles:
   v.sensors.poll();st=v.state;initial[v.vid]=dict(st)
   assert st['up'][2]>.98 and v.sensors['damage']['damage']<1
   axis=0 if v.vid=='red' else 1
   assert st['dir'][axis]>.98,(v.vid,st)
   box=v.get_bbox();pts=list(box.values());dimensions[v.vid]=(max(p[axis] for p in pts)-min(p[axis] for p in pts),max(p[1-axis] for p in pts)-min(p[1-axis] for p in pts))
  dump(out/'initial.json',initial)
  if not args.baseline:
   env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
   for name,cmd,e in [('worker',['/home/vinnavan/Projects/beamng-autonomous/.venv/bin/python','scripts/ml_worker.py','--models','runs/ml-arrival/combined-gpu-cf2bc118ec','--bind','127.0.0.1:3198'],env),('rust',['target/debug/arc-angel'],dict(env,ARC_BIND='127.0.0.1:3098',ARC_ML_ADDR='127.0.0.1:3198',ARC_ML_MODE='hybrid',ARC_SCENARIO=str(out/'scenario.json'),ARC_RUN_DIR=str(out/'server')))]:
    log=(out/(name+'.log')).open('w');logs.append(log);processes.append(subprocess.Popen(cmd,cwd=ROOT,env=e,stdout=log,stderr=subprocess.STDOUT))
   for _ in range(100):
    try:
     with urlopen('http://127.0.0.1:3098/health',timeout=.2):pass
     # Worker warms portable fixtures before listening.
     import socket
     with socket.create_connection(('127.0.0.1',3198),timeout=.2):break
    except OSError:time.sleep(.1)
  client=None if args.baseline else CrossingClient('ws://127.0.0.1:3098/ws/bridge',scenario,out/'wire.jsonl')
  b.camera.set_free((60,-70,70),(-60,70,-70))
  targets={'red':8.,'blue':8.};previous={};started=False;zero_speed=set();clear=set();yielded=set();min_sep=math.inf;dashboard_seq=0
  def publish_dashboard(finished=False):
   nonlocal dashboard_seq
   observed=[]
   for v in vehicles:
    v.sensors.poll();s=v.state;axis=0 if v.vid=='red' else 1
    observed.append({'vehicle_id':'uriel_red' if axis==0 else 'uriel_blue','position_xyz_m':list(s['pos']),'velocity_xyz_mps':list(s['vel']),'forward_xyz':list(s['dir']),'up_xyz':list(s['up']),'sensor_sim_time_s':float(s['time']),'damage':float(v.sensors['damage']['damage']),'length_m':dimensions[v.vid][axis],'width_m':dimensions[v.vid][1-axis]})
   frame={'world_id':observer_world,'frame_seq':dashboard_seq,'mode':'crossing','sim_time_s':max(v['sensor_sim_time_s'] for v in observed),'finished':finished,'vehicles':observed}
   headers={'Content-Type':'application/json'}
   if os.environ.get('ARC_TOKEN'):headers['Authorization']='Bearer '+os.environ['ARC_TOKEN']
   request=Request(dashboard_url+'/api/collision/telemetry',json.dumps(frame,allow_nan=False).encode(),headers)
   with urlopen(request,timeout=.5) as response:
    if response.status!=204:raise RuntimeError(f'dashboard returned HTTP {response.status}')
   dashboard_seq+=1
  observer_world='crossing-observer-'+uuid.uuid4().hex[:12]
  def packets():
   pp=[]
   for v in vehicles:
    v.sensors.poll();s=v.state;old=previous.get(v.vid);dt=float(s['time'])-old[0] if old else 0
    acc=[(s['vel'][i]-old[1][i])/dt if dt>1e-6 else 0. for i in (0,1)]
    previous[v.vid]=(float(s['time']),list(s['vel']))
    pp.append({'vehicle_id':v.vid,'route_id':v.vid,'position_xy_m':list(s['pos'][:2]),'velocity_xy_mps':list(s['vel'][:2]),'acceleration_xy_mps2':acc,'heading_rad':math.atan2(s['dir'][1],s['dir'][0]),'length_m':dimensions[v.vid][0],'width_m':dimensions[v.vid][1]})
   return pp
  start_sim=None
  for frame in range(1,451):
   packets_now=packets();sim=max(float(v.state['time']) for v in vehicles)
   if start_sim is None:start_sim=sim
   elapsed=sim-start_sim
   plan=client.request(frame,elapsed,packets_now) if client else {'recommendations':[{'vehicle_id':v.vid,'speed_cap_mps':8.,'action':'proceed','reason':'uncoordinated_baseline'} for v in vehicles]}
   for v in vehicles:
    advice=next(a for a in plan['recommendations'] if a['vehicle_id']==v.vid)
    if advice['action']=='fallback':raise RuntimeError('Rust fallback '+str(advice))
    cap=min(8.,advice['speed_cap_mps'])
    if advice['action']=='yield':yielded.add(v.vid)
    if not started:
     points=[(-40,0,.2),(0,0,.2),(75,0,.2)] if v.vid=='red' else [(0,-40,.2),(0,0,.2),(0,75,.2)]
     v.control(steering=0,throttle=0,brake=0,parkingbrake=0,gear=selectors[v.vid])
     # Omit per-node v fields: native manSpeed otherwise overrides routeSpeed.
     nodes=','.join('{x='+str(p[0])+',y='+str(p[1])+',z='+str(p[2])+'}' for p in points)
     v.queue_lua_command("ai.driveUsingPath{script={"+nodes+"},routeSpeed=8,routeSpeedMode='limit',avoidCars='off',aggression=0.3};return ai.mode",response=True)
    if cap<=.01:v.control(throttle=0,brake=1,parkingbrake=0);zero_speed.add(v.vid)
    elif v.vid in zero_speed:v.control(throttle=0,brake=0,parkingbrake=0);zero_speed.remove(v.vid)
    v.ai.set_speed(max(cap,.01),mode='limit')
    if client:client.acknowledge({**advice,'speed_cap_mps':cap})
    state=v.state;speed=math.sqrt(sum(x*x for x in state['vel']));axis=0 if v.vid=='red' else 1
    box=v.get_bbox();rear=min(p[axis] for p in box.values())
    if rear>5:clear.add(v.vid)
    rows.append({'frame':frame,'elapsed_s':elapsed,'vehicle_id':v.vid,'state':dict(state),'speed_mps':speed,'electrics':dict(v.sensors['electrics']),'damage':float(v.sensors['damage']['damage']),'advice':advice,'applied_cap_mps':cap})
    if not args.baseline and v.sensors['damage']['damage']>5:raise RuntimeError('Damage guard '+v.vid)
   if not args.no_dashboard:publish_dashboard()
   started=True
   sep=math.dist(vehicles[0].state['pos'],vehicles[1].state['pos']);min_sep=min(min_sep,sep)
   if frame%20==0:print('PROGRESS',round(elapsed,1),'yielded',sorted(yielded),'cleared',sorted(clear),flush=True)
   if args.baseline and any(v.sensors['damage']['damage']>5 for v in vehicles):
    summary['outcome']='damage_detected';break
   if len(clear)==2:summary['outcome']='both_cleared';break
   b.control.step(2)
  summary.update(simulated_seconds=elapsed,yielded=sorted(yielded),cleared=sorted(clear),minimum_reference_distance_m=min_sep,damage={v.vid:float(v.sensors['damage']['damage']) for v in vehicles},rows=len(rows))
 except BaseException as e:
  summary['outcome']='guarded_abort';summary['error']=repr(e);print('STOPPED',repr(e),flush=True)
 finally:
  for v in vehicles:
   try:v.ai.set_mode('disabled');v.control(throttle=0,brake=1,parkingbrake=1)
   except Exception:pass
  if b.connection:
   b.control.pause()
   for v in vehicles:
    try:
     v.sensors.poll();summary.setdefault('final_damage',{})[v.vid]=float(v.sensors['damage']['damage'])
    except Exception:pass
   if not args.no_dashboard:
    try:publish_dashboard(finished=True);summary['dashboard_world_id']=observer_world;summary['dashboard_url']=dashboard_url
    except Exception as publish_error:summary['dashboard_publish_error']=repr(publish_error)
   b.disconnect()
  if client:client.close()
  for p in reversed(processes):
   p.terminate();p.wait(timeout=5)
  for log in logs:log.close()
  with (out/'telemetry.jsonl').open('w') as f:
   for row in rows:f.write(json.dumps(row)+'\n')
  dump(out/'summary.json',summary);print('SUMMARY',json.dumps(summary),flush=True)
if __name__=='__main__':main()
