const byId = id => document.getElementById(id);
const set = (id, value) => { byId(id).textContent = value; };
const svgNS = 'http://www.w3.org/2000/svg';
let demo = false;
let selectedWorld = '';
let activeScenario = null;
const demoScenario = {
  id: 'crossing-v1', label: 'Schematic crossing', zone_half_extent_m: 5,
  routes: [
    {id:'west-east',points_xy_m:[[-100,0],[100,0]]},
    {id:'south-north',points_xy_m:[[0,-100],[0,100]]}
  ]
};
const demoWorld = {
  world_id:'demo-world', world_epoch:'trial-001', bridge_id:'fedora-bridge-a', scenario_config_id:'crossing-v1',
  frame_seq:42, sim_time_s:12.4, wall_age_ms:85, status:'connected', rejected:0, coalesced:0,
  vehicles:[
    {vehicle_id:'car-01',route_id:'west-east',position_xy_m:[-28,0],velocity_xy_mps:[7.2,0],heading_rad:0,length_m:4.5,width_m:1.8},
    {vehicle_id:'car-02',route_id:'south-north',position_xy_m:[0,-35],velocity_xy_mps:[0,5.8],heading_rad:1.57,length_m:4.5,width_m:1.8},
    {vehicle_id:'car-03',route_id:'west-east',position_xy_m:[-65,0],velocity_xy_mps:[4.5,0],heading_rad:0,length_m:4.5,width_m:1.8}
  ],
  reservations:[{vehicle_id:'car-01',entry_sim_s:16.1,exit_sim_s:18.2,committed:false},{vehicle_id:'car-02',entry_sim_s:19.2,exit_sim_s:21.3,committed:false},{vehicle_id:'car-03',entry_sim_s:22.3,exit_sim_s:24.4,committed:false}],
  acknowledgements:{'car-01':'applied','car-02':'applied'},
  last_plan:{type:'recommendation_batch',plan_seq:18,based_on_frame_seq:42,status:'coordinated',valid_until_sim_time_s:12.9,recommendations:[
    {vehicle_id:'car-01',speed_cap_mps:7.0,action:'proceed',reason:'clear_window',entry_window_sim_s:[16.1,16.6]},
    {vehicle_id:'car-02',speed_cap_mps:0,action:'yield',reason:'conflicting_reservation',entry_window_sim_s:[19.2,19.7]},
    {vehicle_id:'car-03',speed_cap_mps:0,action:'yield',reason:'following_headway',entry_window_sim_s:[22.3,22.8]}
  ]}
};
function svgElement(name, attrs, parent) {
  const element = document.createElementNS(svgNS, name);
  for (const [key,value] of Object.entries(attrs)) element.setAttribute(key,value);
  parent.appendChild(element);
  return element;
}
function mapView(world, scenario) {
  const svg = byId('map'); svg.replaceChildren();
  if (!scenario?.routes?.length) return;
  const all = scenario.routes.flatMap(route => route.points_xy_m);
  const xs = all.map(p=>p[0]), ys=all.map(p=>p[1]);
  const bounds = {minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)};
  const scale = Math.min(620/Math.max(1,bounds.maxX-bounds.minX),390/Math.max(1,bounds.maxY-bounds.minY));
  const px = x => 360+(x-(bounds.minX+bounds.maxX)/2)*scale;
  const py = y => 245-(y-(bounds.minY+bounds.maxY)/2)*scale;
  function pointAt(route, target) {
    let distance=0;
    for(let i=1;i<route.points_xy_m.length;i++){
      const a=route.points_xy_m[i-1],b=route.points_xy_m[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]);
      if(distance+length>=target){const t=(target-distance)/length;return [a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])];}
      distance+=length;
    }
    return route.points_xy_m.at(-1);
  }
  const centers=scenario.routes.filter(route=>Number.isFinite(route.zone_center_s_m)).map(route=>pointAt(route,route.zone_center_s_m));
  const center=centers.length?centers.reduce((acc,p)=>[acc[0]+p[0]/centers.length,acc[1]+p[1]/centers.length],[0,0]):[(bounds.minX+bounds.maxX)/2,(bounds.minY+bounds.maxY)/2];
  const zone = scenario.zone_half_extent_m || 5;
  for (const route of scenario.routes) {
    const points = route.points_xy_m.map(p=>`${px(p[0])},${py(p[1])}`).join(' ');
    svgElement('polyline',{points,fill:'none',stroke:'#22516a','stroke-width':27,'stroke-linecap':'round','stroke-linejoin':'round'},svg);
    svgElement('polyline',{points,fill:'none',stroke:'#4a91ac','stroke-width':3,'stroke-dasharray':'13 11',opacity:'.9'},svg);
    const first=route.points_xy_m[0];
    const label=svgElement('text',{x:px(first[0])+8,y:py(first[1])-19,fill:'#a9c9da','font-size':13,'font-family':'DM Sans, sans-serif'},svg);
    label.textContent=route.id;
  }
  svgElement('rect',{x:px(center[0]-zone),y:py(center[1]+zone),width:zone*2*scale,height:zone*2*scale,rx:6,fill:'#b58650',opacity:'.38',stroke:'#e4b27c','stroke-width':2},svg);
  for (const vehicle of world.vehicles) {
    const [x,y]=vehicle.position_xy_m, cx=px(x),cy=py(y);
    svgElement('circle',{cx,cy,r:17,fill:'#68d6e6',opacity:'.14'},svg);
    svgElement('circle',{cx,cy,r:10,fill:'#71e7ed',stroke:'#d0fbff','stroke-width':2},svg);
    svgElement('line',{x1:cx,y1:cy,x2:cx+Math.cos(vehicle.heading_rad)*17,y2:cy-Math.sin(vehicle.heading_rad)*17,stroke:'#e7ffff','stroke-width':3,'stroke-linecap':'round'},svg);
    const name=svgElement('text',{x:cx+15,y:cy-13,fill:'#e8f9ff','font-size':13,'font-weight':700,'font-family':'DM Sans, sans-serif'},svg);
    name.textContent=vehicle.vehicle_id;
  }
}
function fillSelect(worlds) {
  const select=byId('world');
  if (!worlds.some(world=>world.world_id===selectedWorld)) selectedWorld=worlds[0]?.world_id||'';
  select.replaceChildren();
  if (!worlds.length) { const option=document.createElement('option');option.textContent='No active worlds';select.appendChild(option);return; }
  for (const world of worlds) { const option=document.createElement('option');option.value=world.world_id;option.textContent=world.world_id;select.appendChild(option); }
  select.value=selectedWorld;
}
function renderWorld(world, scenario) {
  const plan=world.last_plan, advice=new Map((plan?.recommendations||[]).map(item=>[item.vehicle_id,item]));
  set('count',world.vehicles.length); set('plan-status',plan?.status||'—');set('plan-sub',plan?`Plan #${plan.plan_seq} · Frame ${plan.based_on_frame_seq}`:'Awaiting telemetry');
  set('frame',world.frame_seq??'—');set('age',`${world.wall_age_ms} ms since telemetry`);set('detail-world',world.world_id);set('bridge',world.bridge_id);set('epoch',world.world_epoch);
  set('sim-time',`${world.sim_time_s.toFixed(2)} s`);set('rejected',world.rejected);set('coalesced',world.coalesced);set('vehicle-count',`${world.vehicles.length} tracked`);
  set('side-scenario',scenario?.id||world.scenario_config_id);set('map-live',world.status==='connected'?'Live telemetry':'Telemetry stale');
  const table=byId('vehicles-body');table.replaceChildren();
  for(const vehicle of world.vehicles){
    const item=advice.get(vehicle.vehicle_id), row=document.createElement('tr');
    const speed=Math.hypot(...vehicle.velocity_xy_mps).toFixed(1);
    for(const value of [vehicle.vehicle_id,vehicle.route_id,`${speed} m/s`,item?`${item.speed_cap_mps.toFixed(1)} m/s`:'—',item?.action||'—',item?.reason?.replaceAll('_',' ')||'—']){
      const cell=document.createElement('td');cell.textContent=value;
      if(value===item?.action) {const badge=document.createElement('span');badge.className=`action ${item.action}`;badge.textContent=item.action;cell.replaceChildren(badge);}
      row.appendChild(cell);
    }
    table.appendChild(row);
  }
  if(!world.vehicles.length){const row=document.createElement('tr'),cell=document.createElement('td');cell.colSpan=6;cell.className='empty-cell';cell.textContent='Waiting for vehicle telemetry';row.appendChild(cell);table.appendChild(row);}
  const order=byId('order-list');order.replaceChildren();
  const reservations=[...world.reservations].sort((a,b)=>a.entry_sim_s-b.entry_sim_s);
  set('order-count',reservations.length);
  for(const [index,reservation] of reservations.entries()){
    const row=document.createElement('div');row.className='order-row';
    const rank=document.createElement('span');rank.className='order-rank';rank.textContent=index+1;
    const main=document.createElement('div');main.className='order-main';main.textContent=reservation.vehicle_id;
    const sub=document.createElement('small');sub.textContent=reservation.committed?'Committed':'Reserved';main.appendChild(sub);
    const time=document.createElement('div');time.className='order-time';time.textContent=`${reservation.entry_sim_s.toFixed(1)}–${reservation.exit_sim_s.toFixed(1)} s`;
    const detail=document.createElement('small');detail.textContent='Simulation time';time.appendChild(detail);row.append(rank,main,time);order.appendChild(row);
  }
  if(!reservations.length){const p=document.createElement('p');p.className='empty';p.textContent='Plans will appear when a world sends telemetry.';order.appendChild(p);}
  const activity=byId('activity-list');activity.replaceChildren();
  for(const item of (plan?.recommendations||[]).slice(0,5)){
    const row=document.createElement('div');row.className='activity-row';const dot=document.createElement('span');dot.className='activity-dot';
    const content=document.createElement('div');const title=document.createElement('strong');title.textContent=`${item.vehicle_id} · ${item.action}`;
    const detail=document.createElement('small');detail.textContent=`${item.reason.replaceAll('_',' ')} · Cap ${item.speed_cap_mps.toFixed(1)} m/s`;content.append(title,detail);row.append(dot,content);activity.appendChild(row);
  }
  if(!plan?.recommendations?.length){const p=document.createElement('p');p.className='empty';p.textContent='No recommendations yet.';activity.appendChild(p);}
  mapView(world,scenario);
}
function resetView(){
  for(const [id,value] of Object.entries({count:'0','plan-status':'—','plan-sub':'Awaiting telemetry',frame:'—',age:'No state received','detail-world':'—',bridge:'—',epoch:'—','sim-time':'—',rejected:'0',coalesced:'0','vehicle-count':'0 tracked','order-count':'0','map-live':'Waiting for data'}))set(id,value);
  byId('map').replaceChildren();byId('vehicles-body').innerHTML='<tr><td colspan="6" class="empty-cell">Waiting for vehicle telemetry</td></tr>';
  byId('order-list').innerHTML='<p class="empty">Plans will appear when a world sends telemetry.</p>';
  byId('activity-list').innerHTML='<p class="empty">No recommendations yet.</p>';
}
async function refresh(){
  set('clock',new Date().toLocaleTimeString());
  if(demo){byId('demo-banner').hidden=false;byId('connection-pill').className='pill demo';set('connection-pill','●  Preview mode');set('uptime','Preview');set('server-version','Example data');fillSelect([demoWorld]);renderWorld(demoWorld,demoScenario);return;}
  byId('demo-banner').hidden=true;
  try{
    const [statusResponse,worldResponse]=await Promise.all([fetch('/api/status'),fetch('/api/worlds')]);
    if(!statusResponse.ok||!worldResponse.ok)throw new Error('API unavailable');
    const status=await statusResponse.json(),worlds=await worldResponse.json();
    byId('connection-pill').className='pill online';set('connection-pill','●  Server online');set('uptime',`${Math.floor(status.uptime_s/60)}m ${status.uptime_s%60}s`);set('server-version',`Arc Angel v${status.version}`);
    fillSelect(worlds);const world=worlds.find(item=>item.world_id===selectedWorld);
    if(!world){resetView();return;}
    if(!activeScenario||activeScenario.id!==world.scenario_config_id){const response=await fetch(`/api/scenarios/${encodeURIComponent(world.scenario_config_id)}`);activeScenario=response.ok?await response.json():null;}
    renderWorld(world,activeScenario);
  }catch(error){byId('connection-pill').className='pill';set('connection-pill','●  Server offline');set('uptime','—');set('server-version','Start the Rust server');fillSelect([]);resetView();}
}
byId('world').addEventListener('change',event=>{selectedWorld=event.target.value;activeScenario=null;refresh();});
byId('demo-toggle').addEventListener('click',()=>{demo=!demo;selectedWorld='';activeScenario=null;byId('demo-toggle').setAttribute('aria-pressed',String(demo));refresh();});
refresh();setInterval(refresh,500);
