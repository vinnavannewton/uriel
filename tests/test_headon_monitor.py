import unittest
from scripts.headon_planner import guard_reason


def state(x, y, vy, timestamp=10):
    return {'pos': [x,y,.2], 'vel': [0,vy,0], 'up': [0,0,1], 'time': timestamp}


class MonitorTests(unittest.TestCase):
    def test_closing_without_lateral_clearance_triggers_braking(self):
        self.assertIsNotNone(guard_reason([state(0,5,-8), state(0,-5,8)], (2.9,2.9)))

    def test_pass_with_lateral_clearance_continues(self):
        self.assertIsNone(guard_reason([state(3.5,0,-8), state(-3.5,0,8)], (2.9,2.9)))

    def test_diverging_cars_do_not_trigger_closing_prediction(self):
        self.assertIsNone(guard_reason([state(0,-10,-8), state(0,10,8)], (2.9,2.9)))

    def test_skewed_telemetry_is_rejected(self):
        self.assertIsNotNone(guard_reason([state(0,55,0), state(0,-55,0,11)], (2.9,2.9)))

    def test_invalid_or_rolled_state_stops(self):
        bad=state(0,55,0); bad['pos'][0]=float('nan')
        self.assertIsNotNone(guard_reason([bad,state(0,-55,0)], (2.9,2.9)))
        bad=state(0,55,0); bad['up'][2]=.3
        self.assertIsNotNone(guard_reason([bad,state(0,-55,0)], (2.9,2.9)))
