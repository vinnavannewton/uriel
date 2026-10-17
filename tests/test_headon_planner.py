import math
import unittest
from scripts.headon_planner import Obstacle, choose_plan


class HeadonPlannerTests(unittest.TestCase):
    def test_open_space_selects_a_passing_pair_not_two_straight_paths(self):
        plan = choose_plan([])
        self.assertEqual(plan.mode, 'pass')
        self.assertGreater(plan.offsets[0] - plan.offsets[1], 6)

    def test_pole_on_red_left_keeps_red_straight_and_moves_blue_right(self):
        # Red faces -Y, so its left and blue's right both mean world +X.
        # Pole is beside red's approach, beyond blue's completed return.
        plan = choose_plan([Obstacle(4.5, 30, .45)])
        self.assertEqual(plan.mode, 'pass')
        self.assertEqual(plan.offsets[0], 0)
        self.assertGreater(plan.offsets[1], 6)
        self.assertTrue(any('obstacle' in r['reason'] for r in plan.rejected))

    def test_obstacle_on_blue_return_rejects_that_complete_path(self):
        plan = choose_plan([Obstacle(4.5, 30, .45), Obstacle(4.5, 15, .45)])
        self.assertEqual(plan.mode, 'pass')
        self.assertLess(plan.offsets[0], -6)
        self.assertEqual(plan.offsets[1], 0)

    def test_no_clear_corridor_brakes_both(self):
        self.assertEqual(choose_plan([Obstacle(0, 0, 20)]).mode, 'brake')

    def test_obstacle_touching_vehicle_envelope_blocks_even_if_center_is_clear(self):
        self.assertEqual(choose_plan([Obstacle(0, 55, .1)]).mode, 'brake')

    def test_invalid_geometry_and_unsupported_speed_are_rejected(self):
        for obstacle in [Obstacle(math.nan, 0, .4), Obstacle(0, 0, -1)]:
            with self.subTest(obstacle=obstacle), self.assertRaises(ValueError):
                choose_plan([obstacle])
        for radii in [(0, 2.9), (math.inf, 2.9)]:
            with self.subTest(radii=radii), self.assertRaises(ValueError):
                choose_plan([], radii=radii)
        with self.assertRaises(ValueError):
            choose_plan([], speed=30)


if __name__ == '__main__':
    unittest.main()
