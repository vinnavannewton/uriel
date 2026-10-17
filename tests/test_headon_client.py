from copy import deepcopy
import unittest
from scripts.headon_client import validate_plan

IDENTITY={'world_id':'headon-test','world_epoch':'epoch-1','session_id':'session-1'}

def plan():
    return {'type':'maneuver_plan','protocol_version':2,**IDENTITY,'scenario_config_id':'headon-grid-v2',
            'based_on_frame_seq':3,'plan_seq':1,'maneuver_id':'maneuver-1',
            'issued_sim_time_s':10.,'valid_until_sim_time_s':10.5,'wall_freshness_s':.5,
            'status':'prepare','reason':'paired_left_paths','recommendations':[
                {'vehicle_id':'thePlayer','speed_cap_mps':30/3.6,'action':'follow_path','reason':'coordinated_left','path_xy_m':[[0,55],[3.5,0],[0,-75]]},
                {'vehicle_id':'uriel_blue','speed_cap_mps':30/3.6,'action':'follow_path','reason':'coordinated_left','path_xy_m':[[0,-55],[-3.5,0],[0,75]]}]}


class ClientValidationTests(unittest.TestCase):
    def test_valid_plan_is_accepted(self):
        self.assertEqual(validate_plan(plan(),IDENTITY,3,10.)['status'],'prepare')

    def test_wrong_version_identity_frame_or_expiry_is_rejected(self):
        for key,value in [('protocol_version',1),('session_id','other'),('world_epoch','other'),('based_on_frame_seq',2),
                          ('valid_until_sim_time_s',9.),('valid_until_sim_time_s',12.),('wall_freshness_s',2.),('status','unknown')]:
            p=plan();p[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                validate_plan(p,IDENTITY,3,10.)

    def test_old_plan_missing_car_and_nonfinite_path_are_rejected(self):
        with self.assertRaises(ValueError):validate_plan(plan(),IDENTITY,3,10.,previous_seq=1)
        p=plan();p['recommendations'].pop()
        with self.assertRaises(ValueError):validate_plan(p,IDENTITY,3,10.)
        p=plan();p['recommendations'][0]['path_xy_m'][1][0]=float('nan')
        with self.assertRaises(ValueError):validate_plan(p,IDENTITY,3,10.)

    def test_duplicate_car_and_excessive_speed_are_rejected(self):
        p=plan();p['recommendations'][1]['vehicle_id']='thePlayer'
        with self.assertRaises(ValueError):validate_plan(p,IDENTITY,3,10.)
        p=plan();p['recommendations'][0]['speed_cap_mps']=50
        with self.assertRaises(ValueError):validate_plan(p,IDENTITY,3,10.)

    def test_path_start_must_match_prepared_reference_origin(self):
        p=plan();p['recommendations'][0]['path_xy_m'][0]=[7,55]
        with self.assertRaises(ValueError):validate_plan(p,IDENTITY,3,10.)
