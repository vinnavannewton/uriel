"""Crossing-v1 route export, strict Rust client and BeamNG speed-cap adapter.

No simulator connection is made by importing this module. The collector owns
physics and cleanup; any raised error must stop/pause that owner's trial.
"""
import hashlib
import json
import math
import os
import time
import uuid
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def validate_plan(message, identity, frame, sim_time, ids, max_speed, previous_seq):
    try:
        if (message['type'] != 'recommendation_batch' or message['protocol_version'] != 1
                or any(message[k] != value for k, value in identity.items())
                or message['based_on_frame_seq'] != frame
                or type(message['plan_seq']) is not int or message['plan_seq'] <= previous_seq
                or message['status'] not in ('coordinated', 'degraded')):
            raise ValueError('Wrong crossing plan identity, frame, sequence or status')
        issued, expiry = message['issued_sim_time_s'], message['valid_until_sim_time_s']
        if (not all(math.isfinite(x) for x in (issued, expiry))
                or abs(issued - sim_time) > .001 or not 0 < expiry - issued <= .500001):
            raise ValueError('Invalid crossing plan simulation lease')
        advice = message['recommendations']
        if len(advice) != len(ids) or {r['vehicle_id'] for r in advice} != set(ids):
            raise ValueError('Crossing plan must cover every distinct controlled car')
        for r in advice:
            cap = r['speed_cap_mps']
            if (type(cap) not in (int, float) or not math.isfinite(cap) or not 0 <= cap <= max_speed
                    or r['action'] not in ('proceed', 'yield', 'fallback')
                    or (r['action'] == 'fallback' and cap != 0)):
                raise ValueError('Invalid crossing speed cap or action')
        return message
    except (KeyError, TypeError, IndexError, OverflowError) as error:
        raise ValueError('Malformed crossing plan') from error


def _project(points, p):
    best = (0.0, float('inf'))
    prefix = 0.0
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length2 = dx*dx+dy*dy
        if length2 == 0:
            continue
        t = max(0.0, min(1.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2))
        error = math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)
        if error < best[1]:
            best = (prefix+t*math.sqrt(length2), error)
        prefix += math.sqrt(length2)
    return best


def scenario_from_paths(paths, saved, center, radius, max_speed=12.0):
    routes = []
    for name in sorted(paths):
        points = [list(p[:2]) for p in paths[name]['positions']]
        start = list(saved[name]['position_m'][:2])
        if math.dist(start, points[0]) > .05:
            points.insert(0, start)
        if len(points) < 2 or any(not math.isfinite(v) for p in points for v in p):
            raise ValueError('Invalid route coordinates')
        progress, deviation = _project(points, center)
        if progress <= radius + 2 or deviation > radius:
            raise ValueError(f'{name} does not cross the configured zone after its spawn')
        routes.append({'id': name, 'points_xy_m': points, 'zone_center_s_m': progress,
                       'yield_s_m': max(0.0, progress-radius-32),
                       'commit_s_m': max(0.0, progress-radius-17)})
    config = {'zone_half_extent_m': radius, 'margin_m': 2.0,
              'max_speed_mps': max_speed, 'routes': routes}
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]
    return {'id': 'wc-crossing-'+digest,
            'label': 'West Coast saved editor paths; provisional conflict-zone geometry', **config}


def vehicle_packet(row):
    heading = math.atan2(row['forward_y'], row['forward_x'])
    c, s = math.cos(heading), math.sin(heading)
    points = json.loads(row['bbox_world_json'])
    longitudinal = [p[0]*c+p[1]*s for p in points]
    lateral = [-p[0]*s+p[1]*c for p in points]
    return {'vehicle_id': row['vehicle_id'], 'route_id': row['vehicle_id'],
            'position_xy_m': [row['x_m'], row['y_m']],
            'velocity_xy_mps': [row['vx_mps'], row['vy_mps']],
            'acceleration_xy_mps2': [row['ax_mps2'] or 0.0, row['ay_mps2'] or 0.0],
            'heading_rad': heading, 'length_m': max(longitudinal)-min(longitudinal),
            'width_m': max(lateral)-min(lateral)}


class CrossingClient:
    def __init__(self, url, scenario, wire_path):
        from websockets.sync.client import connect
        self.scenario = scenario
        self.identity = {'world_id': 'crossing-'+uuid.uuid4().hex[:16],
                         'world_epoch': uuid.uuid4().hex}
        self.ids = {r['id'] for r in scenario['routes']}
        self.previous_seq = 0
        self.deadline = None
        self.wire = wire_path.open('w', encoding='utf-8')
        token = os.environ.get('ARC_TOKEN')
        try:
            endpoint = urlsplit(url)
            if endpoint.scheme not in ('ws','wss') or endpoint.path != '/ws/bridge':
                raise ValueError('Use a ws:// or wss:// crossing /ws/bridge endpoint')
            origin = ('https' if endpoint.scheme == 'wss' else 'http')+'://'+endpoint.netloc
            request = Request(origin+'/api/scenarios/'+scenario['id'],
                              headers={'Authorization':'Bearer '+token} if token else {})
            with urlopen(request,timeout=2) as response:
                if json.load(response) != scenario:
                    raise ValueError('Rust loaded a different route/zone configuration')
            self.socket = connect(url, open_timeout=2, close_timeout=.5, proxy=None,
                                  max_size=256*1024,
                                  additional_headers={'Authorization': 'Bearer '+token} if token else None)
            ack = self._exchange({'type':'hello','protocol_version':1,**self.identity,
                                  'scenario_config_id':scenario['id'],'bridge_id':'beamng-crossing-python'})
            if (ack.get('type') != 'hello_ack' or ack.get('protocol_version') != 1
                    or ack.get('status') != 'ready'
                    or any(ack.get(k) != value for k,value in self.identity.items())
                    or not isinstance(ack.get('session_id'),str) or not ack['session_id']
                    or not 0 < ack.get('wall_freshness_s',0) <= .5):
                raise ValueError('Crossing handshake rejected or mismatched')
            self.identity['session_id'] = ack['session_id']
        except BaseException:
            self.close()
            raise

    def _exchange(self, message):
        sent = time.monotonic()
        self.socket.send(json.dumps(message, allow_nan=False))
        reply = json.loads(self.socket.recv(timeout=.35))
        received = time.monotonic()
        self.wire.write(json.dumps({'request':message,'response':reply,
                                    'response_wall_s':received-sent}, allow_nan=False)+'\n')
        self.wire.flush()
        if received-sent > .35 or not isinstance(reply,dict) or reply.get('type') == 'error':
            raise ValueError(f'Stale or rejected crossing response: {reply}')
        return reply

    def request(self, frame, sim_time, vehicles):
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise TimeoutError('Previous crossing plan wall lease expired')
        sent = time.monotonic()
        reply = self._exchange({'type':'state_batch','protocol_version':1,**self.identity,
                                'scenario_config_id':self.scenario['id'],'frame_seq':frame,
                                'sim_time_s':sim_time,'vehicles':vehicles})
        validate_plan(reply,self.identity,frame,sim_time,self.ids,
                      self.scenario['max_speed_mps'],self.previous_seq)
        self.previous_seq = reply['plan_seq']
        self.deadline = sent+.5
        return reply

    def acknowledge(self, recommendation):
        self.socket.send(json.dumps({'type':'applied_result','protocol_version':1,**self.identity,
                                      'plan_seq':self.previous_seq,
                                      'vehicle_id':recommendation['vehicle_id'],'status':'applied',
                                      'applied_speed_cap_mps':recommendation['speed_cap_mps'],
                                      'rejection_reason':None}, allow_nan=False))

    def close(self):
        if hasattr(self,'socket'):
            self.socket.close()
        if hasattr(self,'wire'):
            self.wire.close()


class CrossingController:
    """Called only by the collector that owns physics and the saved AI paths."""
    def __init__(self, url, scenario, wire_path):
        self.client = CrossingClient(url,scenario,wire_path)
        self.stopped = set()
        self.yielding_ids = set()

    def update(self, rows, vehicles):
        if max(r['sim_time_s'] for r in rows)-min(r['sim_time_s'] for r in rows) > .05:
            raise ValueError('Crossing sensor times are not synchronized')
        frame = rows[0]['frame_id']
        plan = self.client.request(frame,max(r['sim_time_s'] for r in rows),
                                   [vehicle_packet(row) for row in rows])
        active = {r['vehicle_id'] for r in rows if r['ai_active']}
        targets = {r['vehicle_id']:r['target_speed_mps'] for r in rows}
        self.yielding_ids = {r['vehicle_id'] for r in plan['recommendations'] if r['action'] == 'yield'}
        current = {v.vid:v for v in vehicles}
        for recommendation in plan['recommendations']:
            name = recommendation['vehicle_id']
            if name not in active:
                continue  # Preserve the collector's parked, delayed launch state.
            vehicle = current[name]
            cap = min(recommendation['speed_cap_mps'], targets[name])
            if cap == 0:
                vehicle.control(throttle=0,brake=1,parkingbrake=0)
                self.stopped.add(name)
            elif name in self.stopped:
                vehicle.control(throttle=0,brake=0,parkingbrake=0)
                self.stopped.remove(name)
            vehicle.ai.set_speed(cap,mode='limit')
            self.client.acknowledge({**recommendation,'speed_cap_mps':cap})
        if any(r['action'] == 'fallback' for r in plan['recommendations']):
            raise RuntimeError('Rust crossing fallback requested; pause the trial')
        return plan

    def close(self):
        self.client.close()
