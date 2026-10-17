const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(name) { this.name=name; this.attrs={}; this.children=[]; this.dataset={}; }
  setAttribute(key,value) { this.attrs[key]=String(value); if(key==='data-car-id')this.dataset.carId=value; }
  appendChild(child) { this.children.push(child); }
  replaceChildren() { this.children=[]; }
  querySelectorAll() { return this.children.flatMap(child=>[...(child.dataset.carId?[child]:[]),...child.querySelectorAll()]); }
}
const svg = new Element('svg');
let now=1000;
const context=vm.createContext({document:{getElementById:()=>svg,createElementNS:(_,name)=>new Element(name)},performance:{now:()=>now},requestAnimationFrame:()=>1});
const source=fs.readFileSync('web/app.js','utf8');
vm.runInContext(source.slice(0,source.indexOf('function fillSelect')),context);
const world={world_id:'headon-collision-render-test',protocol_version:2,status:'connected',frame_seq:0,last_plan:null,
  map_bounds_xy_m:[[-30,-60],[30,60]],vehicles:[
    {vehicle_id:'thePlayer',position_xy_m:[0,50],heading_rad:-Math.PI/2},
    {vehicle_id:'uriel_blue',position_xy_m:[0,-50],heading_rad:Math.PI/2}]};
context.world=world;context.scenario={routes:[],zone_half_extent_m:0};
vm.runInContext('mapView(world,scenario)',context);
let cars=svg.querySelectorAll();
assert.equal(cars.length,2,'Grid Plane must draw both cars even without road routes');
assert.ok(cars.every(car=>car.children.every(child=>child.name!=='text')),'minimal car markers have no visible name labels');
const previous=cars[0].attrs.transform;
assert.ok(!previous.includes('NaN'),'projected car coordinates must be finite');
world.frame_seq=1;world.vehicles[0].position_xy_m=[0,10];
vm.runInContext('mapView(world,scenario)',context);now+=500;
vm.runInContext('animateMapCars()',context);
assert.notEqual(svg.querySelectorAll()[0].attrs.transform,previous,'advancing telemetry must move the car marker');
world.status='disconnected';vm.runInContext('mapView(world,scenario)',context);
assert.equal(svg.querySelectorAll().length,2,'completed runs must keep both final markers visible');
console.log('PASS: route-free Grid Plane draws two cars, updates marker positions, and retains finished-run markers');
