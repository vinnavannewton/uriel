const byId = id => document.getElementById(id);
const set = (id, value) => { byId(id).textContent = value; };
const svgNS = 'http://www.w3.org/2000/svg';
let demo = false;
let demoMode = 'headon';
let selectedWorld = '';
let activeScenario = null;
const demoScenario = {
  id: 'headon-grid-v2', label: 'Plain Grid Plane head-on pass', zone_half_extent_m: 5,
  routes: [
    {id:'red · north to south',points_xy_m:[[0,55],[0,-75]]},
    {id:'blue · south to north',points_xy_m:[[0,-55],[0,75]]}
  ]
};
const demoWorld = {
  world_id:'preview-headon-grid', world_epoch:'preview-only', bridge_id:'dashboard-preview', protocol_version:2, scenario_config_id:'headon-grid-v2',
  frame_seq:0, sim_time_s:0, wall_age_ms:0, status:'connected', rejected:0, coalesced:0, acknowledgements:{thePlayer:'accepted',uriel_blue:'accepted'},
  vehicles:[
    {vehicle_id:'thePlayer',route_id:'north-south',position_xy_m:[0,55],velocity_xy_mps:[0,-8.33],heading_rad:-Math.PI/2,length_m:4.7,width_m:1.9},
    {vehicle_id:'uriel_blue',route_id:'south-north',position_xy_m:[0,-55],velocity_xy_mps:[0,8.33],heading_rad:Math.PI/2,length_m:4.7,width_m:1.9}
  ],
  reservations:[],
  last_plan:{type:'maneuver_plan',plan_seq:1,based_on_frame_seq:0,status:'execute',reason:'coordinated_left',maneuver_id:'preview-pass',valid_until_sim_time_s:.5,recommendations:[
    {vehicle_id:'thePlayer',speed_cap_mps:30/3.6,action:'follow_path',reason:'coordinated_left',path_xy_m:[]},
    {vehicle_id:'uriel_blue',speed_cap_mps:30/3.6,action:'follow_path',reason:'coordinated_left',path_xy_m:[]}
  ]}
};
const crossingDemoScenario={id:'demo-90-degree-crossing',label:'Synthetic 90-degree crossing',zone_half_extent_m:5,routes:[
  {id:'Car A · west to east',zone_center_s_m:50,points_xy_m:[[-50,0],[50,0]]},
  {id:'Car B · north to south',zone_center_s_m:50,points_xy_m:[[0,50],[0,-50]]}
]};
const crossingDemoWorld={world_id:'preview-90-degree-crossing',world_epoch:'preview-only',bridge_id:'dashboard-preview',protocol_version:1,scenario_config_id:crossingDemoScenario.id,preview_mode:'crossing90',frame_seq:0,sim_time_s:0,wall_age_ms:0,status:'connected',rejected:0,coalesced:0,reservations:[],vehicles:[
  {vehicle_id:'demo_red',route_id:'west-east',position_xy_m:[-50,0],velocity_xy_mps:[7,0],heading_rad:0,length_m:4.7,width_m:1.9,braking:false},
  {vehicle_id:'demo_blue',route_id:'north-south',position_xy_m:[0,50],velocity_xy_mps:[0,-10],heading_rad:-Math.PI/2,length_m:4.7,width_m:1.9,braking:false}
],last_plan:{type:'recommendation_batch',plan_seq:0,based_on_frame_seq:0,status:'approach',reason:'synthetic_demo',recommendations:[
  {vehicle_id:'demo_red',speed_cap_mps:7,action:'proceed',reason:'crossing_priority',path_xy_m:[[-50,0],[50,0]]},
  {vehicle_id:'demo_blue',speed_cap_mps:0,action:'yield',reason:'braking_for_crossing',path_xy_m:[[0,50],[0,-50]]}
]}};
let demoProgress=0;
let demoCompleteTicks=0;
let mapMotionWorld='';
let mapMotion=new Map();
let mapFrameAt=0;
let mapAnimation=0;
const presetIds=['preset-mode','preset-traffic','preset-traffic-speed','preset-subject-speed','preset-car-a','preset-car-b','preset-randomize'];
function readPreset(){
  const number=(id,min,max)=>Math.max(min,Math.min(max,Number(byId(id).value)||min));
  return {schema:'uriel.next-trial-preset.v1',controller_mode:byId('preset-mode').value,background_traffic:{count:number('preset-traffic',0,8),speed_cap_kmh:number('preset-traffic-speed',5,160)},subjects:[{slot:'A',model:byId('preset-car-a').value.trim()||'vivace',speed_cap_kmh:number('preset-subject-speed',5,160)},{slot:'B',model:byId('preset-car-b').value.trim()||'vivace',speed_cap_kmh:number('preset-subject-speed',5,160)}],randomize_between_trials:byId('preset-randomize').checked,apply_scope:'next_trial_only',live_beamng_control:false};
}
function renderPreset(){byId('preset-output').textContent=JSON.stringify(readPreset(),null,2);}
function loadPreset(){
  try{const saved=JSON.parse(localStorage.getItem('uriel-next-trial-preset-v1')||'null');if(saved){byId('preset-mode').value=saved.controller_mode||'baseline';byId('preset-traffic').value=String(saved.background_traffic?.count??0);byId('preset-traffic-speed').value=saved.background_traffic?.speed_cap_kmh??40;byId('preset-subject-speed').value=saved.subjects?.[0]?.speed_cap_kmh??30;byId('preset-car-a').value=saved.subjects?.[0]?.model||'vivace';byId('preset-car-b').value=saved.subjects?.[1]?.model||'vivace';byId('preset-randomize').checked=saved.randomize_between_trials!==false;}}catch(_error){}
  renderPreset();
}
for(const id of presetIds)byId(id).addEventListener('input',renderPreset);
byId('save-preset').addEventListener('click',()=>{localStorage.setItem('uriel-next-trial-preset-v1',JSON.stringify(readPreset()));byId('preset-status').textContent='Preset saved in this browser · start a new trial to use it';});
byId('copy-preset').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(byId('preset-output').textContent);byId('preset-status').textContent='Preset JSON copied · configure your next trial with these values';}catch(_error){byId('preset-status').textContent='Clipboard unavailable · select and copy the JSON below';}});
function updateDemo(){
  if(demoMode==='crossing90'){
    const blue=crossingDemoWorld.vehicles[1],red=crossingDemoWorld.vehicles[0];
    if(demoProgress>=19){demoProgress=0;crossingDemoWorld.sim_time_s=0;red.position_xy_m=[-50,0];red.velocity_xy_mps=[0,0];blue.position_xy_m=[0,50];blue.velocity_xy_mps=[0,0];blue.braking=false;}
    demoProgress+=.5;
    const t=demoProgress;
    const previousRedX=red.position_xy_m[0],previousBlueY=blue.position_xy_m[1];
    const redX=-50+9*Math.min(t,100/9);
    let blueY,phase;
    if(t<3.5){blueY=50-8*t;phase='approach';}
    else if(t<6){const brakeTime=t-3.5;blueY=22-8*brakeTime+1.6*brakeTime*brakeTime;phase='braking';}
    else if(t<7.4){blueY=12;phase='yielding';}
    else{const movingTime=t-7.4;blueY=movingTime<4?12-movingTime*movingTime:-4-8*(movingTime-4);blueY=Math.max(-50,blueY);phase='proceeding';}
    if(blueY<=-50)phase='complete';
    const braking=phase==='braking'||phase==='yielding';
    red.position_xy_m=[redX,0];red.velocity_xy_mps=[(redX-previousRedX)/.5,0];
    blue.position_xy_m=[0,blueY];blue.braking=braking;blue.velocity_xy_mps=[0,(blueY-previousBlueY)/.5];
    crossingDemoWorld.frame_seq++;crossingDemoWorld.sim_time_s+=.5;
    const redCleared=t>=7.4;
    crossingDemoWorld.last_plan={type:'recommendation_batch',plan_seq:crossingDemoWorld.frame_seq,based_on_frame_seq:crossingDemoWorld.frame_seq,status:phase,reason:braking?'braking_for_crossing':phase==='proceeding'?'crossing_cleared':'approaching_intersection',recommendations:[
      {vehicle_id:'demo_red',speed_cap_mps:8,action:'proceed',reason:'crossing_priority',path_xy_m:crossingDemoScenario.routes[0].points_xy_m},
      {vehicle_id:'demo_blue',speed_cap_mps:braking?0:Math.min(8,Math.abs(blue.velocity_xy_mps[1])),action:braking?'yield':'proceed',reason:braking?'braking_for_crossing':redCleared?'crossing_cleared':'approaching_intersection',path_xy_m:crossingDemoScenario.routes[1].points_xy_m}
    ]};
    crossingDemoWorld.reservations=redCleared?[{vehicle_id:'demo_blue',entry_sim_s:crossingDemoWorld.sim_time_s+1,exit_sim_s:crossingDemoWorld.sim_time_s+3,committed:false}]:[{vehicle_id:'demo_red',entry_sim_s:crossingDemoWorld.sim_time_s+1,exit_sim_s:crossingDemoWorld.sim_time_s+2,committed:false}];
    return;
  }
  if(demoProgress>=130){
    demoCompleteTicks++;
    if(demoCompleteTicks>6){demoProgress=0;demoCompleteTicks=0;demoWorld.sim_time_s=0;}
  }else{demoProgress=Math.min(130,demoProgress+4.17);demoWorld.sim_time_s+=.5;}
  demoWorld.frame_seq++;
  const blend=p=>p<=5?0:p<40?((p-5)/35)**2*(3-2*((p-5)/35)):p<=65?1:p<85?1-((p-65)/20)**2*(3-2*((p-65)/20)):0;
  const paths=[3.5,-3.5].map((offset,i)=>Array.from({length:66},(_,n)=>{
    const p=n*2;return [offset*blend(p),(55-p)*(i===0?1:-1)];
  }));
  for(let i=0;i<2;i++){
    const car=demoWorld.vehicles[i],travel=(i===0?-1:1)*demoProgress;
    car.position_xy_m=[[3.5,-3.5][i]*blend(demoProgress),(i===0?55:-55)+travel];
    demoWorld.last_plan.recommendations[i].path_xy_m=paths[i];
  }
  demoWorld.last_plan.status=demoProgress>=130?'complete':'execute';
  demoWorld.last_plan.plan_seq=demoWorld.frame_seq;
  demoWorld.last_plan.based_on_frame_seq=demoWorld.frame_seq;
}
function svgElement(name, attrs, parent) {
  const element = document.createElementNS(svgNS, name);
  for (const [key,value] of Object.entries(attrs)) element.setAttribute(key,value);
  parent.appendChild(element);
  return element;
}
function mapPosition(state, now) {
  if(!state||state.duration<=0)return state?.target||[0,0];
  const t=Math.max(0,Math.min(1,(now-state.started)/state.duration));
  return [state.from[0]+(state.target[0]-state.from[0])*t,state.from[1]+(state.target[1]-state.from[1])*t];
}
function animateMapCars() {
  const now=performance.now(),svg=byId('map');
  for(const group of svg.querySelectorAll('[data-car-id]')){
    const state=mapMotion.get(group.dataset.carId);
    if(!state)continue;
    const [x,y]=mapPosition(state,now),[cx,cy]=state.project(x,y);
    group.setAttribute('transform',`translate(${cx} ${cy}) rotate(${-state.heading*180/Math.PI})`);
  }
  if(now-mapFrameAt<1000)mapAnimation=requestAnimationFrame(animateMapCars);
  else mapAnimation=0;
}
function mapView(world, scenario) {
  const svg = byId('map'); svg.replaceChildren();
  // An open Grid Plane has no road routes; its measured cars and fixed
  // bounds still supply everything needed to draw the map.
  if (!scenario?.routes) return;
  const plan=world.last_plan, recommendations=plan?.recommendations||[];
  const isHeadon=world.protocol_version===2 || world.scenario_config_id==='headon-grid-v2';
  const animateVehicles=isHeadon||world.preview_mode==='crossing90';
  const routePoints=world.map_bounds_xy_m||scenario.routes.flatMap(route => route.points_xy_m);
  const all = [...routePoints,
    ...recommendations.flatMap(item=>item.path_xy_m||[]),
    ...world.vehicles.map(vehicle=>vehicle.position_xy_m)];
  if (!all.length) return;
  const xs = all.map(p=>p[0]), ys=all.map(p=>p[1]);
  const bounds = {minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)};
  const spanX=Math.max(1,bounds.maxX-bounds.minX),spanY=Math.max(1,bounds.maxY-bounds.minY);
  const centerX=(bounds.minX+bounds.maxX)/2,centerY=(bounds.minY+bounds.maxY)/2;
  // Head-on views use one metres-to-pixels scale on an open grid-plane floor.
  // Keeping XY proportional makes lateral movement honest and lets the cars
  // visibly travel across the grid instead of stretching a straight approach.
  const gridSpanX=Math.max(60,spanX+20),gridSpanY=Math.max(1,spanY+18);
  const gridScale=Math.min(640/gridSpanX,390/gridSpanY);
  const scaleX=isHeadon?gridScale:Math.min(620/spanX,390/spanY);
  const scaleY=isHeadon?gridScale:scaleX;
  const px = x => 360+(x-centerX)*scaleX;
  const py = y => 245-(y-centerY)*scaleY;
  if(animateVehicles){
    const identity=world.world_id||'headon';
    if(mapMotionWorld!==identity){mapMotionWorld=identity;mapMotion.clear();mapFrameAt=0;}
    const now=performance.now(),frame=world.frame_seq??plan?.based_on_frame_seq??0;
    for(const vehicle of world.vehicles){
      const id=vehicle.vehicle_id,position=vehicle.position_xy_m;
      let state=mapMotion.get(id);
      if(!state){state={from:position.slice(),target:position.slice(),started:now,duration:0,frame,heading:vehicle.heading_rad,project:(x,y)=>[px(x),py(y)]};mapMotion.set(id,state);mapFrameAt=now;}
      else if(frame!==state.frame||Math.hypot(position[0]-state.target[0],position[1]-state.target[1])>.03){
        state.from=mapPosition(state,now);state.target=position.slice();state.started=now;state.duration=500;state.frame=frame;state.heading=vehicle.heading_rad;state.project=(x,y)=>[px(x),py(y)];mapFrameAt=now;
      }else{state.heading=vehicle.heading_rad;state.project=(x,y)=>[px(x),py(y)];}
    }
  }else{mapMotionWorld='';mapMotion.clear();}
  if(isHeadon){
    const defs=svgElement('defs',{},svg),minor=scaleX*10,major=minor*5;
    const small=svgElement('pattern',{id:'grid-minor',width:minor,height:minor,patternUnits:'userSpaceOnUse',x:px(0),y:py(0)},defs);
    svgElement('path',{d:`M ${minor} 0 L 0 0 0 ${minor}`,fill:'none',stroke:'#294257','stroke-width':'.8',opacity:'.78'},small);
    const large=svgElement('pattern',{id:'grid-major',width:major,height:major,patternUnits:'userSpaceOnUse',x:px(0),y:py(0)},defs);
    svgElement('path',{d:`M ${major} 0 L 0 0 0 ${major}`,fill:'none',stroke:'#3b5d72','stroke-width':'1.2',opacity:'.7'},large);
    svgElement('rect',{x:0,y:0,width:720,height:490,fill:'#0c1925'},svg);
    svgElement('rect',{x:0,y:0,width:720,height:490,fill:'url(#grid-minor)'},svg);
    svgElement('rect',{x:0,y:0,width:720,height:490,fill:'url(#grid-major)'},svg);
    svgElement('line',{x1:px(0),x2:px(0),y1:0,y2:490,stroke:'#81a2b2','stroke-width':1,opacity:'.36'},svg);
    svgElement('line',{x1:0,x2:720,y1:py(0),y2:py(0),stroke:'#81a2b2','stroke-width':1,opacity:'.36'},svg);
    for(let x=Math.ceil((centerX-360/scaleX)/20)*20;x<=centerX+360/scaleX;x+=20){
      const label=svgElement('text',{x:px(x)+3,y:474,fill:'#71899c','font-size':10,'font-family':'DM Sans, sans-serif'},svg);label.textContent=`${x}m`;
    }
    for(let y=Math.ceil((centerY-240/scaleY)/20)*20;y<=centerY+240/scaleY;y+=20){
      const label=svgElement('text',{x:8,y:py(y)-4,fill:'#71899c','font-size':10,'font-family':'DM Sans, sans-serif'},svg);label.textContent=`${y}m`;
    }
  }
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
  for (const route of (isHeadon ? [] : scenario.routes)) {
    const points = route.points_xy_m.map(p=>`${px(p[0])},${py(p[1])}`).join(' ');
    if(isHeadon)svgElement('polyline',{points,fill:'none',stroke:'#77a9be','stroke-width':2,'stroke-dasharray':'3 12','stroke-linecap':'round',opacity:'.45'},svg);
    else{
      svgElement('polyline',{points,fill:'none',stroke:'#22516a','stroke-width':27,'stroke-linecap':'round','stroke-linejoin':'round'},svg);
      svgElement('polyline',{points,fill:'none',stroke:'#4a91ac','stroke-width':3,'stroke-dasharray':'13 11',opacity:'.9'},svg);
    }
    const first=route.points_xy_m[0];
    const label=svgElement('text',{x:px(first[0])+8,y:py(first[1])-19,fill:'#a9c9da','font-size':13,'font-family':'DM Sans, sans-serif'},svg);
    label.textContent=route.id;
  }
  if(!isHeadon)svgElement('rect',{x:px(center[0]-zone),y:py(center[1]+zone),width:zone*2*scaleX,height:zone*2*scaleY,rx:6,fill:'#b58650',opacity:'.38',stroke:'#e4b27c','stroke-width':2},svg);
  for(const item of (isHeadon ? [] : recommendations)){
    const path=item.path_xy_m||[];
    if(path.length<2)continue;
    const color=item.vehicle_id==='thePlayer'?'#ff827b':'#73baff';
    const line=svgElement('polyline',{points:path.map(p=>`${px(p[0])},${py(p[1])}`).join(' '),fill:'none',stroke:color,'stroke-width':4,'stroke-dasharray':'8 6','stroke-linecap':'round','stroke-linejoin':'round',opacity:'.95'},svg);
    const title=svgElement('title',{},line);title.textContent=`${item.vehicle_id} · server path · ${item.speed_cap_mps.toFixed(1)} m/s`;
  }
  for (const vehicle of world.vehicles) {
    const [x,y]=vehicle.position_xy_m, cx=px(x),cy=py(y);
    const color=vehicle.vehicle_id==='thePlayer'||vehicle.vehicle_id==='uriel_red'||vehicle.vehicle_id==='demo_red'?'#ff827b':vehicle.vehicle_id==='uriel_blue'||vehicle.vehicle_id==='demo_blue'?'#73baff':'#71e7ed';
    const car=svgElement('g',{'data-car-id':vehicle.vehicle_id,class:vehicle.braking?'braking-car':'',transform:`translate(${cx} ${cy}) rotate(${-vehicle.heading_rad*180/Math.PI})`},svg);
    for(const x of [-8,7])for(const y of [-8,6])
      svgElement('rect',{x:x-2,y,width:5,height:3,rx:1,fill:'#07111d'},car);
    // Local +X is the nose. The broad body, separate windows and four wheels
    // read as a top-down car at dashboard scale instead of a pointed marker.
    svgElement('path',{d:'M -14 -6 Q -12 -9 -7 -9 L 7 -9 Q 13 -9 16 -5 L 18 0 L 16 5 Q 13 9 7 9 L -7 9 Q -12 9 -14 6 Z',fill:color,stroke:'#eaf7ff','stroke-width':1},car);
    svgElement('path',{d:'M 3 -6 L 9 -6 Q 12 -5 14 -2 L 14 2 Q 12 5 9 6 L 3 6 Z',fill:'#102235',stroke:'#86a3b8','stroke-width':'.6',opacity:'.96'},car);
    svgElement('path',{d:'M -9 -6 L -2 -6 L 0 -4 L 0 4 L -2 6 L -9 6 Q -11 0 -9 -6 Z',fill:'#102235',stroke:'#86a3b8','stroke-width':'.6',opacity:'.88'},car);
    for(const y of [-5,3]){
      svgElement('rect',{x:15,y,width:2,height:2,rx:.5,fill:'#fff5c2'},car);
      svgElement('rect',{x:-13,y,width:2,height:2,rx:.5,fill:'#a52e4a',class:'brake-light'},car);
    }
    const title=svgElement('title',{},car);title.textContent=vehicle.vehicle_id;
  }
  if(animateVehicles&&world.status==='connected'&&performance.now()-mapFrameAt<1000&&!mapAnimation)mapAnimation=requestAnimationFrame(animateMapCars);
}
function fillSelect(worlds) {
  const select=byId('world');
  const selected=worlds.find(world=>world.world_id===selectedWorld);
  const liveObserver=worlds.find(world=>world.observation_only&&world.observation_mode==='crossing'&&world.status==='connected');
  const liveHeadon=worlds.find(world=>world.protocol_version===2&&world.status==='connected');
  if(liveObserver&&(!selected||selected.status!=='connected'))selectedWorld=liveObserver.world_id;
  else if(liveHeadon&&(!selected||(selected.protocol_version===2&&selected.status!=='connected')))
    selectedWorld=liveHeadon.world_id;
  else if(!selected)selectedWorld=worlds[0]?.world_id||'';
  select.replaceChildren();
  if (!worlds.length) { const option=document.createElement('option');option.textContent='No active worlds';select.appendChild(option);return; }
  for (const world of worlds) { const option=document.createElement('option');option.value=world.world_id;option.textContent=world.world_id;select.appendChild(option); }
  select.value=selectedWorld;
}
function renderWorld(world, scenario) {
  const plan=world.last_plan, advice=new Map((plan?.recommendations||[]).map(item=>[item.vehicle_id,item]));
  const isHeadon=world.protocol_version===2 || world.scenario_config_id==='headon-grid-v2';
  const crossingObserver=world.observation_only&&world.observation_mode==='crossing';
  const crossingPreview=world.preview_mode==='crossing90';
  set('page-title',crossingPreview?'90° crossing · preview':crossingObserver?'90-degree crossing · live observation':world.observation_only?(world.observation_mode==='dodge'?'Head-on dodge':'Head-on collision baseline'):isHeadon?'Head-on avoidance':'Intersection overview');
  set('page-subtitle',crossingPreview?'Synthetic preview · blue car brakes and yields, then proceeds after red clears.':crossingObserver?`Measured positions · ${world.vehicles.length} crossing cars · display only`:world.observation_only?(world.observation_mode==='dodge'?'Cooperative dodge · measured BeamNG positions':'Measured BeamNG positions · intentional collision · observation only'):isHeadon?'Two-car Grid Plane pass · live positions, server paths, and maneuver state.':'Vehicle positions, crossing order, and server guidance in one place.');
  set('map-title',crossingPreview?'90-degree crossing · yielding car blinks when braking':crossingObserver?`Live 90-degree crossing · ${world.vehicles.length} cars`:world.observation_only?'Live two-car observation':isHeadon?'Live two-car maneuver':'Live crossing map');
  set('map-label',isHeadon?'GRID MAP · LIVE XY · 10 M GRID':'SCHEMATIC · METRES');
  set('coordination-title',isHeadon?'Maneuver status':'Crossing order');
  byId('maneuver-summary').hidden=!isHeadon||world.observation_only;
  set('count',world.vehicles.length); set('plan-status',world.observation_only?'Observe only':plan?.status||'—');set('plan-sub',world.observation_only?'Observation only · no planner commands':plan?`Plan #${plan.plan_seq} · Frame ${plan.based_on_frame_seq}`:'Awaiting telemetry');
  set('frame',world.frame_seq??'—');set('age',`${world.wall_age_ms} ms since telemetry`);set('detail-world',world.world_id);set('bridge',world.bridge_id);set('epoch',world.world_epoch);
  set('sim-time',`${world.sim_time_s.toFixed(2)} s`);set('rejected',world.rejected);set('coalesced',world.coalesced);set('vehicle-count',`${world.vehicles.length} tracked`);
  set('side-scenario',crossingPreview?'90° crossing · synthetic preview':crossingObserver?'Small Grid · perpendicular approaches':scenario?.id||world.scenario_config_id);set('map-live',world.preview_mode?'Synthetic demo':world.status==='connected'?'Live telemetry':'Telemetry stale');
  if(isHeadon&&!world.observation_only){
    const summary=byId('maneuver-summary');summary.replaceChildren();
    const phase=document.createElement('strong');phase.className=`maneuver-phase ${plan?.status||'waiting'}`;phase.textContent=(plan?.status||'waiting for plan').replaceAll('_',' ');summary.appendChild(phase);
    const sub=document.createElement('p');sub.textContent=plan?`Plan ${plan.plan_seq} · ${plan.reason.replaceAll('_',' ')} · maneuver ${plan.maneuver_id.slice(0,8)}`:'Waiting for the BeamNG bridge to send vehicle state.';summary.appendChild(sub);
    for(const id of ['thePlayer','uriel_blue']){
      const row=document.createElement('div');row.className='ack-row';
      const dot=document.createElement('i');dot.className=`ack-dot ${id==='thePlayer'?'red':'blue'}`;
      const name=document.createElement('span');name.textContent=id;
      const state=document.createElement('b');state.textContent=world.acknowledgements?.[id]||'awaiting path';
      row.append(dot,name,state);summary.appendChild(row);
    }
  }
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
  set('page-title','Intersection overview');set('page-subtitle','Vehicle positions, crossing order, and server guidance in one place.');set('map-title','Live crossing map');set('map-label','SCHEMATIC · METRES');set('coordination-title','Crossing order');byId('maneuver-summary').hidden=true;
  for(const [id,value] of Object.entries({count:'0','plan-status':'—','plan-sub':'Awaiting telemetry',frame:'—',age:'No state received','detail-world':'—',bridge:'—',epoch:'—','sim-time':'—',rejected:'0',coalesced:'0','vehicle-count':'0 tracked','order-count':'0','map-live':'Waiting for data'}))set(id,value);
  byId('map').replaceChildren();byId('vehicles-body').innerHTML='<tr><td colspan="6" class="empty-cell">Waiting for vehicle telemetry</td></tr>';
  byId('order-list').innerHTML='<p class="empty">Plans will appear when a world sends telemetry.</p>';
  byId('activity-list').innerHTML='<p class="empty">No recommendations yet.</p>';
}
async function refresh(){
  set('clock',new Date().toLocaleTimeString());
  if(demo){updateDemo();const preview=demoMode==='crossing90'?crossingDemoWorld:demoWorld,scenario=demoMode==='crossing90'?crossingDemoScenario:demoScenario;byId('demo-banner').hidden=false;byId('demo-banner').textContent=demoMode==='crossing90'?'Synthetic 90° crossing · blue brakes/yields before the junction; red passes first. Brake lamps blink while stopped. Not BeamNG telemetry.':'Synthetic head-on preview · animated example cars and maneuver path. Not BeamNG telemetry.';byId('connection-pill').className='pill demo';set('connection-pill','●  Preview mode');set('uptime','Preview');set('server-version','Synthetic animation · not BeamNG data');fillSelect([preview]);renderWorld(preview,scenario);byId('demo-toggle').textContent='Stop demo';return;}
  byId('demo-toggle').textContent='Start demo';
  byId('demo-banner').hidden=true;
  try{
    const [statusResponse,worldResponse]=await Promise.all([fetch('/api/status'),fetch('/api/worlds')]);
    if(!statusResponse.ok||!worldResponse.ok)throw new Error('API unavailable');
    const status=await statusResponse.json(),worlds=await worldResponse.json();
    byId('connection-pill').className='pill online';set('connection-pill','●  Server online');set('uptime',`${Math.floor(status.uptime_s/60)}m ${status.uptime_s%60}s`);set('server-version',`Uriel v${status.version}`);
    fillSelect(worlds);const world=worlds.find(item=>item.world_id===selectedWorld);
    if(!world){resetView();return;}
    if(!activeScenario||activeScenario.id!==world.scenario_config_id){const response=await fetch(`/api/scenarios/${encodeURIComponent(world.scenario_config_id)}`);activeScenario=response.ok?await response.json():null;}
    renderWorld(world,activeScenario);
  }catch(error){byId('connection-pill').className='pill';set('connection-pill','●  Server offline');set('uptime','—');set('server-version','Start the Rust server');fillSelect([]);resetView();}
}
byId('world').addEventListener('change',event=>{selectedWorld=event.target.value;activeScenario=null;refresh();});
byId('demo-toggle').addEventListener('click',()=>{demo=!demo;demoProgress=0;demoCompleteTicks=0;demoWorld.frame_seq=0;demoWorld.last_plan.status='execute';crossingDemoWorld.frame_seq=0;crossingDemoWorld.sim_time_s=0;selectedWorld='';activeScenario=null;byId('demo-toggle').setAttribute('aria-pressed',String(demo));refresh();});
byId('demo-mode').addEventListener('change',event=>{demoMode=event.target.value;demoProgress=0;demoCompleteTicks=0;crossingDemoWorld.frame_seq=0;crossingDemoWorld.sim_time_s=0;if(demo)refresh();});
loadPreset();refresh();setInterval(refresh,500);
