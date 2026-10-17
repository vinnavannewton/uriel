import unittest
from scripts.headon_planner import front_aligned_path


class AlignmentTests(unittest.TestCase):
    def test_ai_front_path_preserves_the_planned_vehicle_reference_start(self):
        state={'pos':[0,55,.35], 'front':[.16,53.16,.905]}
        points=front_aligned_path([(0,55),(3.5,0)],state)
        self.assertAlmostEqual(points[0][0],.16)
        self.assertAlmostEqual(points[0][1],53.16)
        self.assertAlmostEqual(points[1][0],3.66)
        self.assertAlmostEqual(points[1][1],-1.84)
