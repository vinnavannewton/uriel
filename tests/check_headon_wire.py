"""Explicit localhost protocol checks. No BeamNG or other simulator calls."""
import json
import os
from pathlib import Path
import sys
import urllib.request
import uuid
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
url=sys.argv[1] if len(sys.argv)>1 else 'ws://127.0.0.1:3000'
out=ROOT/'runs'/('protocol-check-'+uuid.uuid4().hex[:10]);out.mkdir()
headers={'Authorization':'Bearer '+os.environ['ARC_TOKEN']} if os.environ.get('ARC_TOKEN') else None
wire=[]

def exchange(ws,message):
    ws.send(json.dumps(message));response=json.loads(ws.recv(timeout=1))
    wire.append({'request':message,'response':response});return response

hello=json.loads((ROOT/'examples/headon-hello.json').read_text())
hello.update(world_id='wire-check-'+uuid.uuid4().hex[:10],world_epoch=uuid.uuid4().hex)
with connect(url+'/ws/headon',additional_headers=headers,proxy=None,open_timeout=2) as ws:
    ack=exchange(ws,hello);assert ack['type']=='hello_ack' and ack['protocol_version']==2
    with connect(url+'/ws/headon',additional_headers=headers,proxy=None,open_timeout=2) as other:
        denied=exchange(other,{**hello,'world_epoch':uuid.uuid4().hex})
        assert denied['type']=='error' and 'active bridge' in denied['detail']
    frame=json.loads((ROOT/'examples/headon-state.json').read_text())
    frame.update(world_id=hello['world_id'],world_epoch=hello['world_epoch'],session_id=ack['session_id'])
    prepared=exchange(ws,frame);assert prepared['status']=='prepare'
    for vehicle in ('thePlayer','uriel_blue'):
        accepted=exchange(ws,{'type':'maneuver_ack','protocol_version':2,'world_id':hello['world_id'],
            'world_epoch':hello['world_epoch'],'session_id':ack['session_id'],'plan_seq':prepared['plan_seq'],
            'maneuver_id':prepared['maneuver_id'],'vehicle_id':vehicle,'status':'accepted','reason':None})
        assert accepted['status']=='accepted'
    frame['frame_seq']=1
    execute=exchange(ws,frame);assert execute['status']=='execute'
    frame['frame_seq']=2
    frozen=exchange(ws,frame);assert frozen['status']=='pause' and frozen['reason']=='simulation_time_not_advancing'
with connect(url+'/ws/headon',additional_headers=headers,proxy=None,open_timeout=2) as ws:
    rejected=exchange(ws,hello)
    assert rejected['type']=='error' and 'reset epoch' in rejected['detail']
legacy=json.loads((ROOT/'examples/hello.json').read_text());legacy['world_id']='legacy-wire-'+uuid.uuid4().hex[:8]
with connect(url+'/ws/bridge',additional_headers=headers,proxy=None,open_timeout=2) as ws:
    ack=exchange(ws,legacy);assert ack['protocol_version']==1 and ack['type']=='hello_ack'
    state=json.loads((ROOT/'examples/state_batch.json').read_text())
    state.update(world_id=legacy['world_id'],session_id=ack['session_id'])
    legacy_plan=exchange(ws,state)
    assert legacy_plan['type']=='recommendation_batch' and legacy_plan['protocol_version']==1
    assert len(legacy_plan['recommendations'])==2
http=url.replace('ws://','http://').replace('wss://','https://')
with urllib.request.urlopen(http+'/api/worlds',timeout=2) as r:worlds=json.load(r)
with urllib.request.urlopen(http+'/api/status',timeout=2) as r:status=json.load(r)
assert status['world_count']==len(worlds) and status['headon_world_count']>=1
result={'kind':'synthetic protocol checks; no simulator commands',
        'headon_phases':[prepared['status'],execute['status'],frozen['status']],
        'active_owner_protected':True,'reset_epoch_enforced':True,'legacy_v1_compatible':True,
        'world_counts_match':True,'status':status}
(out/'wire.json').write_text(json.dumps(wire,indent=2))
(out/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2));print('EVIDENCE',out)
