"""Strict client for Rust's maneuver-v2 contract; BeamNG-independent validation."""
import json
import math
import os
import time
import uuid

IDS = ('thePlayer', 'uriel_blue')
SCENARIO = 'headon-grid-v2'


def validate_plan(message, identity, frame_seq, sim_time, previous_seq=0):
    try:
        if (message['type'] != 'maneuver_plan' or message['protocol_version'] != 2
                or message['scenario_config_id'] != SCENARIO
                or any(message[k] != v for k,v in identity.items())
                or message['based_on_frame_seq'] != frame_seq
                or not isinstance(message['plan_seq'],int) or message['plan_seq'] <= previous_seq
                or not isinstance(message['maneuver_id'],str) or not 1 <= len(message['maneuver_id']) <= 96
                or message['status'] not in ('prepare','execute','pause','complete')):
            raise ValueError('Wrong plan identity, version, frame, sequence or phase')
        issued, expiry, wall = (message[k] for k in ('issued_sim_time_s','valid_until_sim_time_s','wall_freshness_s'))
        if (not all(math.isfinite(v) for v in (issued,expiry,wall)) or abs(issued-sim_time) > .001
                or not 0 < expiry-issued <= .500001 or not 0 < wall <= .5):
            raise ValueError('Invalid plan time or lease')
        recommendations=message['recommendations']
        if len(recommendations)!=2 or {r['vehicle_id'] for r in recommendations} != set(IDS):
            raise ValueError('Plan must include both distinct controlled cars')
        for r in recommendations:
            speed=r['speed_cap_mps']; points=r['path_xy_m']
            if not math.isfinite(speed) or not 0 <= speed <= 30/3.6+.000001:
                raise ValueError('Speed outside the bounded experiment')
            if r['action'] not in ('follow_path','pause') or not 3 <= len(points) <= 128:
                raise ValueError('Invalid maneuver action or path length')
            if any(len(p)!=2 or not all(math.isfinite(x) and abs(x)<=1000 for x in p) for p in points):
                raise ValueError('Invalid path coordinates')
            sign=1 if r['vehicle_id']==IDS[0] else -1
            if math.dist(points[0],[0,55*sign])>.01 or math.dist(points[-1],[0,-75*sign])>.01:
                raise ValueError('Path does not match prepared reference frame')
            if message['status'] in ('prepare','execute') and (r['action']!='follow_path' or speed<=0):
                raise ValueError('Active maneuver requires a positive-speed path')
        return message
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Malformed maneuver plan') from exc


class HeadonClient:
    def __init__(self, url, world_id, wire_path):
        from websockets.sync.client import connect
        self.identity={'world_id':world_id,'world_epoch':uuid.uuid4().hex}
        self.frame_seq=-1
        self.previous_seq=0
        self.plan=None
        self.geometry=None
        self.speeds=None
        self.deadline=0
        self.wire=wire_path.open('w')
        token=os.environ.get('ARC_TOKEN')
        try:
            self.socket=connect(url,open_timeout=2,close_timeout=.5,max_size=256*1024,
                                proxy=None,additional_headers={'Authorization':f'Bearer {token}'} if token else None)
            hello={'type':'hello','protocol_version':2,**self.identity,'scenario_config_id':SCENARIO,
                   'bridge_id':'beamng-headon-python','map_id':'smallgrid',
                   'capabilities':['path_origin_xy_v2','sim_pause_fallback']}
            ack,_=self._exchange(hello)
            if (ack.get('type')!='hello_ack' or ack.get('protocol_version')!=2
                    or any(ack.get(k)!=v for k,v in self.identity.items())
                    or ack.get('scenario_config_id')!=SCENARIO or ack.get('status')!='ready'
                    or not isinstance(ack.get('session_id'),str) or not ack['session_id']):
                raise ValueError('Rust handshake identity or capability mismatch')
            self.identity['session_id']=ack['session_id']
        except BaseException:
            if hasattr(self,'socket'):self.socket.close()
            self.wire.close()
            raise

    def _exchange(self, message, deadline=None):
        response_timeout(deadline)
        sent=time.monotonic()
        self.socket.send(json.dumps(message,allow_nan=False))
        reply=json.loads(self.socket.recv(timeout=response_timeout(deadline)))
        received=time.monotonic()
        response_timeout(deadline,received)
        self.wire.write(json.dumps({'sent_monotonic_s':sent,'received_monotonic_s':received,
                                    'request':message,'response':reply})+'\n')
        self.wire.flush()
        if not isinstance(reply,dict) or reply.get('type')=='error':
            raise ValueError(f'Rust rejected message: {reply}')
        if received-sent > .5:
            raise TimeoutError('Rust response exceeded the 500ms freshness budget')
        return reply,sent

    def request(self, data, dimensions):
        self.frame_seq+=1
        sim_time=max(data[k]['state']['time'] for k in IDS)
        vehicles=[]
        for name in IDS:
            s=data[name]['state']
            vehicles.append({'vehicle_id':name,'position_xyz_m':s['pos'],'velocity_xyz_mps':s['vel'],
                             'forward_xyz':s['dir'],'up_xyz':s['up'],'sensor_sim_time_s':s['time'],
                             'damage':data[name]['damage'].get('damage',0),**dimensions[name]})
        message={'type':'headon_state','protocol_version':2,**self.identity,'frame_seq':self.frame_seq,
                 'sim_time_s':sim_time,'vehicles':vehicles}
        old_deadline=self.deadline if self.plan and self.plan['status']=='execute' else None
        reply,sent=self._exchange(message,deadline=old_deadline)
        response_timeout(old_deadline)
        validate_plan(reply,self.identity,self.frame_seq,sim_time,self.previous_seq)
        geometry={r['vehicle_id']:r['path_xy_m'] for r in reply['recommendations']}
        if self.plan and (reply['maneuver_id']!=self.plan['maneuver_id'] or geometry!=self.geometry):
            raise ValueError('Rust changed a maneuver or its paths during the pass')
        speeds={r['vehicle_id']:r['speed_cap_mps'] for r in reply['recommendations']}
        if self.plan and reply['status'] in ('prepare','execute') and speeds!=self.speeds:
            raise ValueError('Rust changed speed within a fixed maneuver')
        self.plan=reply;self.geometry=geometry;self.speeds=speeds;self.previous_seq=reply['plan_seq']
        self.deadline=sent+reply['wall_freshness_s']
        return reply

    def accept_paths(self):
        if not self.plan or self.plan['status']!='prepare':
            raise ValueError('Only a prepared maneuver can be accepted')
        for name in IDS:
            reply,_=self._exchange({'type':'maneuver_ack','protocol_version':2,**self.identity,
                                   'plan_seq':self.plan['plan_seq'],'maneuver_id':self.plan['maneuver_id'],
                                   'vehicle_id':name,'status':'accepted','reason':None})
            if reply != {'type':'ack_result','vehicle_id':name,'status':'accepted'}:
                raise ValueError('Unexpected acknowledgement response')

    def close(self):
        self.socket.close()
        self.wire.close()


def response_timeout(deadline=None, now=None):
    if deadline is None:
        return .35
    budget=deadline-(time.monotonic() if now is None else now)-.1
    if budget<=0:
        raise TimeoutError('Previous Rust execution lease exhausted its 100ms pause margin')
    return min(.35,budget)
