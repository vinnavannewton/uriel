import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect_west_coast_lidar_trial import LidarWriter


class LidarCaptureTests(unittest.TestCase):
    def test_cloud_round_trip_and_repeated_readings_keep_poll_times(self):
        points = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        colours = np.asarray([[1, 2, 3], [10, 20, 30]], dtype=np.uint8)
        sensor = SimpleNamespace(poll=lambda: {'pointCloud': points, 'colours': colours},
                                 get_position=lambda: (0, 0, 2))
        vehicle = SimpleNamespace(vid='clone12', model='van',
                                  state={'time': 10, 'pos': (0, 0, 0),
                                         'dir': (1, 0, 0), 'up': (0, 0, 1)})
        with tempfile.TemporaryDirectory() as directory:
            writer = LidarWriter(directory, {'clone12': sensor})
            writer('trial', 0, 0, [vehicle])
            vehicle.state['time'] = 10.4
            writer('trial', 2, .4, [vehicle])
            rows = [json.loads(s) for s in (Path(directory) / 'index.jsonl').read_text().splitlines()]
            self.assertEqual([r['status'] for r in rows], ['saved', 'repeated'])
            self.assertEqual(rows[1]['poll_sim_time_s'], 10.4)
            self.assertIsNone(rows[0]['acquisition_time_s'])
            self.assertEqual(rows[0]['file'], rows[1]['file'])
            with np.load(Path(directory) / rows[0]['file']) as scan:
                np.testing.assert_array_equal(scan['points'], points)
                np.testing.assert_array_equal(scan['colours'], colours)
            self.assertEqual(writer.stats['clone12']['scans'], 1)


if __name__ == '__main__':
    unittest.main()
