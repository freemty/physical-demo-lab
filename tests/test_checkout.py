import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from checkout_verify import verify_checkout


class CheckoutTest(unittest.TestCase):
    def setUp(self):
        self.bag = {'color': 'bag', 'inner_lower': [0, 0, .7], 'inner_upper': [.3, .3, .84]}
        self.states = [dict(id='a', color='bag', position=[.12, .12, .725], orientation=[1, 0, 0, 0],
                            size=.05, linear_velocity=[0]*3, angular_velocity=[0]*3,
                            max_lift=.2, belt_displacement=.3, released_and_retracted=True)]
        self.inventory = [{'id': 'a', 'price_cents': 450}]
        self.scans = [{'id': 'a', 'price_cents': 450, 'dwell_frames': 12, 'inside_volume': True}]

    def verify(self):
        return verify_checkout(self.states, self.bag, self.inventory, self.scans)['success']

    def test_success(self):
        self.assertTrue(self.verify())

    def test_scan_required(self):
        self.scans = []
        self.assertFalse(self.verify())

    def test_duplicate_scan(self):
        self.scans.append(copy.deepcopy(self.scans[0]))
        self.assertFalse(self.verify())

    def test_wrong_price(self):
        self.scans[0]['price_cents'] = 1
        self.assertFalse(self.verify())

    def test_no_real_dwell(self):
        self.scans[0]['dwell_frames'] = 1
        self.assertFalse(self.verify())

    def test_unreleased_or_not_lifted(self):
        self.states[0]['released_and_retracted'] = False
        self.assertFalse(self.verify())
        self.states[0]['released_and_retracted'] = True
        self.states[0]['max_lift'] = .01
        self.assertFalse(self.verify())
