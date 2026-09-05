import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from blocks_verify import verify_bridge


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.targets = [{'id': 'a', 'role': 'pillar', 'position': [.39, 0, .73]},
                        {'id': 'b', 'role': 'pillar', 'position': [.55, 0, .73]},
                        {'id': 'c', 'role': 'beam', 'position': [.47, 0, .7825]}]
        self.states = [dict(id=t['id'], position=t['position'][:], orientation=[1, 0, 0, 0],
                            linear_velocity=[0]*3, angular_velocity=[0]*3,
                            max_lift=.2, released_and_retracted=True) for t in self.targets]

    def test_good(self):
        self.assertTrue(verify_bridge(self.states, self.targets, [0, 1])['success'])

    def test_missing_arm_and_support(self):
        self.assertFalse(verify_bridge(self.states, self.targets, [0])['success'])
        self.assertFalse(verify_bridge(self.states[:2], self.targets, [0, 1])['success'])

    def test_hanging_and_unreleased(self):
        for key, value in [('position', [.47, 0, .85]), ('position', [.47, .03, .7825]),
                           ('released_and_retracted', False), ('max_lift', .01)]:
            states = copy.deepcopy(self.states)
            states[2][key] = value
            self.assertFalse(verify_bridge(states, self.targets, [0, 1])['success'])
