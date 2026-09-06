import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1]/"scripts/audit_castle.py"
spec = importlib.util.spec_from_file_location("castle_audit_test", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NativeLiftTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(id="piece", position=[0,0,.8], orientation=[1,0,0,0],
                          linear_velocity=[0,0,0], angular_velocity=[0,0,0])
        self.contacts = [dict(body="piece",other="robot:"+f,normal_force=1)
                         for f in ("panda_leftfinger","panda_rightfinger")]
    def test_hand_command_or_zero_force_is_not_a_lift(self):
        evidence = module.LiftEvidence(["piece"])
        evidence.update([self.state], self.contacts)
        self.state["position"][2] += .2
        evidence.update([self.state], [dict(c,normal_force=0) for c in self.contacts])
        self.assertEqual(evidence.verified_names(), set())
    def test_bilateral_loaded_lift(self):
        evidence = module.LiftEvidence(["piece"])
        evidence.update([self.state], [])
        self.state["position"][2] += .2
        evidence.update([self.state], self.contacts)
        self.assertEqual(evidence.verified_names(), {"piece"})
    def test_signed_native_normal_force_is_loaded(self):
        evidence = module.LiftEvidence(["piece"])
        evidence.update([self.state], [])
        self.state["position"][2] += .2
        evidence.update([self.state], [dict(c,normal_force=-3.5) for c in self.contacts])
        self.assertEqual(evidence.verified_names(), {"piece"})

    def test_duplicate_and_nonfinite_states_rejected(self):
        evidence = module.LiftEvidence(["piece"])
        with self.assertRaises(ValueError):
            evidence.update([self.state,self.state], [])
        self.state["position"][0] = float("nan")
        with self.assertRaises(ValueError):
            evidence.update([self.state], [])
