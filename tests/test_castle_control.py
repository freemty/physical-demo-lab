import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"demos"))
from castle_control import bounded_targets, quaternion_error, LOW, HIGH


class CastleControlTests(unittest.TestCase):
    def test_quaternion_sign_equivalence(self):
        self.assertTrue(np.allclose(quaternion_error([0,1,0,0], [0,-1,0,0]), 0))
    def test_targets_finite_at_singularity(self):
        q = (LOW+HIGH)/2
        self.assertTrue(np.allclose(bounded_targets(q, np.zeros((6,7)), [1,1,1], [1,1,1]), q))
    def test_limit_and_error_bound(self):
        q = HIGH-.01
        target = bounded_targets(q, np.eye(6,7), [10,10,10], [10,10,10])
        self.assertTrue(np.all(target <= HIGH-.002))
        self.assertLessEqual(float(np.max(np.abs(target-q))), .12000001)
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            bounded_targets(LOW, np.eye(6,7), [float("nan"),0,0], [0,0,0])
