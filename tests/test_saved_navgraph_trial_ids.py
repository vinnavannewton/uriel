import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_saved_navgraph_trial import (
    assign_background_routes,
    resolve_participant_ids,
    route_following_start_states,
)


class ResolveParticipantIdsTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "vehicles": {
                "thePlayer": {"role": "known_red_ego"},
                "clone0": {"role": "unknown_black_vehicle"},
            }
        }

    def test_defaults_to_saved_ids(self):
        result = resolve_participant_ids(
            self.manifest, None, None, {"thePlayer", "clone0"}
        )
        self.assertEqual(result, (
            "thePlayer", "clone0", {"thePlayer": "thePlayer", "clone0": "clone0"}
        ))

    def test_accepts_live_id_overrides(self):
        result = resolve_participant_ids(
            self.manifest, "ego1", "unknown7", {"ego1", "unknown7"}
        )
        self.assertEqual(result[2], {"thePlayer": "ego1", "clone0": "unknown7"})

    def test_missing_participant_error_lists_loaded_ids_and_guidance(self):
        with self.assertRaisesRegex(RuntimeError, r"BeamNG currently reports \['thePlayer'\]"):
            resolve_participant_ids(self.manifest, None, None, {"thePlayer"})

    def test_red_and_black_cannot_resolve_to_same_id(self):
        with self.assertRaisesRegex(RuntimeError, "same live vehicle"):
            resolve_participant_ids(
                self.manifest, "same", "same", {"same"}
            )


class AssignBackgroundRoutesTests(unittest.TestCase):
    def test_assignments_are_deterministic_and_alternate_saved_lanes(self):
        result = assign_background_routes(
            {"traffic-c", "traffic-a", "traffic-d", "traffic-b"},
            "thePlayer", "clone0",
        )
        self.assertEqual(result, {
            "traffic-a": "thePlayer",
            "traffic-b": "clone0",
            "traffic-c": "thePlayer",
            "traffic-d": "clone0",
        })

    def test_odd_count_differs_by_at_most_one(self):
        result = assign_background_routes(
            {"traffic-c", "traffic-a", "traffic-b"}, "red", "black"
        )
        self.assertEqual(list(result.values()).count("red"), 2)
        self.assertEqual(list(result.values()).count("black"), 1)

    def test_traffic_starts_repeatably_behind_route_starts(self):
        manifest = {"vehicles": {
            "red": {
                "position_m": [10.0, 20.0, 3.0],
                "direction": [0.6, 0.8, 0.0],
                "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            "black": {
                "position_m": [100.0, 200.0, 4.0],
                "direction": [1.0, 0.0, 0.0],
                "rotation_xyzw": [0.0, 0.0, 1.0, 0.0],
            },
        }}
        assignments = {"a": "red", "b": "black", "c": "red"}
        first = route_following_start_states(manifest, assignments)
        second = route_following_start_states(manifest, assignments)
        self.assertEqual(first, second)
        self.assertEqual(first["a"]["position_m"], [-5.0, 0.0, 3.0])
        self.assertEqual(first["c"]["position_m"], [-20.0, -20.0, 3.0])
        self.assertEqual(first["c"]["offset_behind_start_m"], 50.0)
        self.assertEqual(first["b"]["position_m"], [75.0, 200.0, 4.0])


if __name__ == "__main__":
    unittest.main()
