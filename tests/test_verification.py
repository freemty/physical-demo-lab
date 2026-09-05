import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'demos'))
from verification import verify_object


class VerificationTest(unittest.TestCase):
    def setUp(self):
        self.destination = {'color': 'red', 'inner_lower': [0, 0, 0.7], 'inner_upper': [0.24, 0.24, 0.82]}
        self.state = dict(color='red', position=[0.12, 0.12, 0.725], orientation=[1, 0, 0, 0],
                          size=0.05, linear_velocity=[0, 0, 0], angular_velocity=[0, 0, 0],
                          max_lift=0.2, belt_displacement=0.25, released_and_retracted=True)

    def test_success(self):
        self.assertTrue(verify_object(self.state, self.destination)['success'])

    def test_failures(self):
        for key, value in [('color', 'blue'), ('position', [0.01, 0.12, 0.725]),
                           ('position', [0.12, 0.12, 0.95]), ('position', [float('nan'), 0.12, 0.725]),
                           ('linear_velocity', [0.1, 0, 0]), ('angular_velocity', [0, 0, 0.5]),
                           ('max_lift', 0.01), ('belt_displacement', 0.0), ('released_and_retracted', False)]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(self.state)
                changed[key] = value
                self.assertFalse(verify_object(changed, self.destination)['success'])


if __name__ == '__main__':
    unittest.main()
