import importlib.util
import json
from pathlib import Path
import unittest
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'crossing_client.py'
spec = importlib.util.spec_from_file_location('crossing_client', SCRIPT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)

IDENTITY = {'world_id':'test','world_epoch':'epoch','session_id':'session'}

def reply():
    return {'type':'recommendation_batch','protocol_version':1,**IDENTITY,
            'based_on_frame_seq':4,'plan_seq':5,'issued_sim_time_s':2.0,
            'valid_until_sim_time_s':2.5,'status':'coordinated',
            'recommendations':[{'vehicle_id':'a','speed_cap_mps':8.0,'action':'proceed'},
                               {'vehicle_id':'b','speed_cap_mps':3.0,'action':'yield'}]}

class CrossingClientTests(unittest.TestCase):
    def validate(self, value):
        return client.validate_plan(value, IDENTITY, 4, 2.0, {'a','b'}, 12.0, 4)

    def test_accepts_matching_plan_with_one_slowed_car(self):
        self.assertEqual(self.validate(reply())['recommendations'][1]['speed_cap_mps'],3.0)

    def test_rejects_wrong_session_old_frame_duplicate_missing_and_unsafe_caps(self):
        changes = [('session_id','other'),('based_on_frame_seq',3),('plan_seq',4),
                   ('valid_until_sim_time_s',2.0),('issued_sim_time_s',1.9),('status','unknown')]
        for key,value in changes:
            data=reply();data[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): self.validate(data)
        for cap in (float('nan'),-1.0,13.0):
            data=reply();data['recommendations'][0]['speed_cap_mps']=cap
            with self.subTest(cap=cap),self.assertRaises(ValueError): self.validate(data)
        for cars in ([reply()['recommendations'][0]]*2, reply()['recommendations'][:1]):
            data=reply();data['recommendations']=cars
            with self.assertRaises(ValueError): self.validate(data)

    def test_exported_scenario_projects_actual_conflict_point_on_each_route(self):
        paths={'a':{'positions':[[-40,0,0],[0,0,0],[40,0,0]]},
               'b':{'positions':[[0,-40,0],[0,0,0],[0,40,0]]}}
        saved={'a':{'position_m':[-50,0,0]},'b':{'position_m':[0,-50,0]}}
        scenario=client.scenario_from_paths(paths,saved,[0,0,0],5.0)
        self.assertEqual([r['zone_center_s_m'] for r in scenario['routes']],[50.0,50.0])
        self.assertTrue(all(r['yield_s_m']<=r['commit_s_m']<r['zone_center_s_m'] for r in scenario['routes']))
        self.assertEqual(scenario,client.scenario_from_paths(paths,saved,[0,0,0],5.0))

    def test_vehicle_packet_uses_measured_acceleration_and_oriented_box_dimensions(self):
        box=[[x,y,z] for x in (-2,2) for y in (-1,1) for z in (0,1.5)]
        row={'vehicle_id':'a','x_m':-20,'y_m':0,'vx_mps':8,'vy_mps':0,
             'ax_mps2':2,'ay_mps2':0,'forward_x':1,'forward_y':0,
             'bbox_world_json':json.dumps(box)}
        packet=client.vehicle_packet(row)
        self.assertEqual(packet['acceleration_xy_mps2'],[2,0])
        self.assertEqual(packet['length_m'],4)
        self.assertEqual(packet['width_m'],2)

    def test_adapter_keeps_delayed_car_parked_and_releases_brakes_when_yield_ends(self):
        commands=[]
        acknowledgements=[]
        plan=reply()
        plan['recommendations'][0].update(speed_cap_mps=0.0,action='yield')
        adapter=client.CrossingController.__new__(client.CrossingController)
        adapter.client=SimpleNamespace(request=lambda *args:plan,
            acknowledge=acknowledgements.append)
        adapter.stopped=set()
        adapter.yielding_ids=set()
        cars=[SimpleNamespace(vid=n,
            control=lambda _n=n,**kw:commands.append((_n,'control',kw)),
            ai=SimpleNamespace(set_speed=lambda cap,mode,_n=n:commands.append((_n,'cap',cap))))
            for n in ('a','b')]
        box=[[x,y,z] for x in (-2,2) for y in (-1,1) for z in (0,1.5)]
        rows=[{'vehicle_id':n,'x_m':-20,'y_m':0,'vx_mps':8,'vy_mps':0,
               'ax_mps2':0,'ay_mps2':0,'forward_x':1,'forward_y':0,
               'bbox_world_json':json.dumps(box),'sim_time_s':2.0,'frame_id':4,
               'ai_active':n=='a','target_speed_mps':6.0} for n in ('a','b')]
        adapter.update(rows,cars)
        self.assertTrue(all(command[0]=='a' for command in commands))
        self.assertEqual(commands[0],('a','control',{'throttle':0,'brake':1,'parkingbrake':0}))
        commands.clear()
        plan['recommendations'][0].update(speed_cap_mps=12.0,action='proceed')
        adapter.update(rows,cars)
        self.assertEqual(commands[0],('a','control',{'throttle':0,'brake':0,'parkingbrake':0}))
        self.assertEqual(commands[1],('a','cap',6.0))
        self.assertEqual(acknowledgements[-1]['speed_cap_mps'],6.0)

if __name__=='__main__': unittest.main()
