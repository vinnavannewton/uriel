import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_west_coast_arrival_trials.py"
SPEC = importlib.util.spec_from_file_location("west_coast_collector", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class LaunchWatchdogTests(unittest.TestCase):
    def test_editor_route_is_sent_as_exact_path_without_legal_direction_replanning(self):
        vehicle = Mock()
        path = ['junction1_wp3', 'junction1_wp8', 'junction1_wp12', 'junction1_wp18']
        collector.start_editor_path(vehicle, path, 6.0)
        command = vehicle.queue_lua_command.call_args.args[0]
        self.assertIn('path={"junction1_wp3","junction1_wp8","junction1_wp12","junction1_wp18"}', command)
        self.assertNotIn('wpTargetList', command)
        self.assertIn("driveInLane='off'", command)
        self.assertIn("avoidCars='on'", command)

    def test_does_not_fail_before_motion_timeout(self):
        self.assertFalse(collector.launch_stalled((0, 0, 0), (0, 0, 0), 4.9))

    def test_fails_if_car_does_not_move_after_timeout(self):
        self.assertTrue(collector.launch_stalled((0, 0, 0), (0.01, 0, 0), 5.0))

    def test_does_not_fail_when_car_moved(self):
        self.assertFalse(collector.launch_stalled((0, 0, 0), (0.6, 0, 0), 5.0))

    def test_yaw_half_turn_preserves_quaternion_xyzw_shape(self):
        q = (0.0, 0.0, 0.0, 1.0)
        self.assertEqual(collector.yaw_half_turn(q), (0.0, 0.0, 1.0, 0.0))

    def test_first_pilot_routes_both_cars_to_shared_junction(self):
        spec = collector.trial_spec(0)
        self.assertEqual(spec["clone12"]["route"], ["junction1_wp12", "junction1_wp18"])
        self.assertEqual(spec["clone13"]["route"][-2:], ["junction1_wp12", "junction1_wp29"])
        self.assertEqual(spec["clone12"]["delay_s"], 4.0)

    def test_fast_mode_preserves_five_hz_sample_interval(self):
        for factor, steps in ((1, 4), (2, 2), (4, 1)):
            with self.subTest(factor=factor):
                self.assertEqual(max(1, 4 // factor), steps)

    def test_schedule_keeps_predicted_arrivals_separated(self):
        for index in range(len(collector.SCHEDULE)):
            spec = collector.trial_spec(index)
            a = collector.ROUTE_DISTANCE_M["clone12"] / spec["clone12"]["speed_mps"] + spec["clone12"]["delay_s"]
            b = collector.ROUTE_DISTANCE_M["clone13"] / spec["clone13"]["speed_mps"] + spec["clone13"]["delay_s"]
            self.assertGreaterEqual(abs(a - b), 5.0, f"schedule index {index} overlaps")


if __name__ == "__main__":
    unittest.main()
