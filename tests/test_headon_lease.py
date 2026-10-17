import unittest
from scripts.headon_client import response_timeout


class LeaseTests(unittest.TestCase):
    def test_receive_budget_stays_inside_old_lease_with_pause_margin(self):
        self.assertAlmostEqual(response_timeout(deadline=10.25,now=10),.15)
        self.assertAlmostEqual(response_timeout(deadline=11,now=10),.35)

    def test_renewal_cannot_start_or_finish_after_pause_margin(self):
        for now in (10.2,10.26):
            with self.subTest(now=now),self.assertRaises(TimeoutError):
                response_timeout(deadline=10.25,now=now)
