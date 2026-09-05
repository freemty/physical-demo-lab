import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from gear_verify import verify_gear, multiply_quaternions


class GearTest(unittest.TestCase):
    def test_full_pose_correction(self):
        # A tilted part must need a correction even when its yaw is zero.
        q = [math.cos(.15), math.sin(.15), 0., 0.]
        inverse = [q[0], -q[1], -q[2], -q[3]]
        identity = multiply_quaternions(inverse, q)
        for actual, expected in zip(identity, [1., 0., 0., 0.]):
            self.assertAlmostEqual(actual, expected)

    def test_seated_and_failures(self):
        target = {'position': [.43, .25, .73], 'yaw': 0.}
        good = {'position': [.43, .25, .73], 'orientation': [1, 0, 0, 0],
                'linear_velocity': [0]*3, 'angular_velocity': [0]*3,
                'max_lift': .2, 'released_and_retracted': True}
        self.assertTrue(verify_gear(good, target)['success'])
        for key, value in [('position', [.44, .25, .73]), ('position', [.43, .25, .76]),
                           ('orientation', [.99875, 0, 0, .04998]), ('max_lift', .01),
                           ('linear_velocity', [.1, 0, 0]), ('released_and_retracted', False)]:
            with self.subTest(key=key, value=value):
                state = copy.deepcopy(good)
                state[key] = value
                self.assertFalse(verify_gear(state, target)['success'])
