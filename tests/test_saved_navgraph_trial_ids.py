import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_saved_navgraph_trial import resolve_participant_ids


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


if __name__ == "__main__":
    unittest.main()
