import unittest

from scripts.beamng_headon_collision import forward_selector_index, plan_dodge_paths


class CollisionLaunchTests(unittest.TestCase):
    def test_dct_selects_drive_instead_of_park(self):
        self.assertEqual(forward_selector_index('dctGearbox'), 2)

    def test_manual_selects_first_gear(self):
        self.assertEqual(forward_selector_index('manualGearbox'), 1)

    def test_unknown_drivetrain_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported Vivace gearbox'):
            forward_selector_index('missing')

    def test_dodge_paths_use_scene_center_and_separate_cars_before_returning(self):
        plan, paths = plan_dodge_paths((12, 120), (2.5, 2.5), 30 / 3.6)
        self.assertEqual(plan.offsets, (3.5, -3.5))
        self.assertEqual(paths[0][0], (12, 175))
        self.assertEqual(paths[1][0], (12, 65))
        self.assertGreater(paths[0][25][0], 12)
        self.assertLess(paths[1][25][0], 12)
        self.assertEqual(paths[0][-1], (12, 45))
        self.assertEqual(paths[1][-1], (12, 195))

    def test_dodge_rejects_speed_outside_planner_envelope(self):
        with self.assertRaises(ValueError):
            plan_dodge_paths((0, 0), (2.5, 2.5), 50 / 3.6)
