from copy import deepcopy
import unittest
from scripts.headon_planner import matching_configs


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.a={'model':'vivace','vars':{'boost':1},'partsTree':{'chosenPartName':'vivace','children':{'engine':{'chosenPartName':'stock','decisionMethod':'user'}}}}

    def test_selection_provenance_and_paint_do_not_change_physical_parts(self):
        b=deepcopy(self.a)
        b['partsTree']['children']['engine']['decisionMethod']='default'
        b['paints']=[{'baseColor':[0,0,1,1]}]
        self.assertTrue(matching_configs(self.a,b))

    def test_changed_engine_or_tuning_is_not_a_match(self):
        b=deepcopy(self.a);b['partsTree']['children']['engine']['chosenPartName']='race'
        self.assertFalse(matching_configs(self.a,b))
        b=deepcopy(self.a);b['vars']['boost']=2
        self.assertFalse(matching_configs(self.a,b))
