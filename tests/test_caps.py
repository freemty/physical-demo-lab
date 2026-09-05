import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from cap_verify import verify_cap_trace


class CapTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {'physics_dt': 1/60, 'thread': {'pitch': .012, 'release_angle': math.pi,
            'z0': 1.01, 'spring': 1000., 'damping': 2., 'rotary_drag': .002},
            'contact_links': ['/World/Hand/thumb_link_3', '/World/Hand/index_link_3']}
        self.frames = []
        for step in range(400):
            angle = min(math.pi+.01, step*(math.pi+.01)/200)
            engaged = angle < math.pi
            z = 1.01+.012*angle/(2*math.pi) if engaged else 1.17
            self.frames.append({'step': step, 'physics_steps': step+1, 'sim_time': (step+1)/60,
                'objects_before_step': [{'position': [0, 0, z],
                'orientation': [math.cos(angle/2), 0, 0, math.sin(angle/2)],
                'linear_velocity': [0]*3, 'angular_velocity': [0]*3}],
                'commands': [{'thread_engaged': engaged, 'thread_force_z': 0., 'thread_torque_z': 0.,
                    'finger_contact_forces': [[[1., 0, 0]], [[-1., 0, 0]]]}]})

    def test_good(self):
        self.assertTrue(verify_cap_trace(self.manifest, self.frames)['success'])

    def test_early_or_no_disengagement(self):
        early = copy.deepcopy(self.frames)
        early[3]['commands'][0]['thread_engaged'] = False
        self.assertFalse(verify_cap_trace(self.manifest, early)['success'])
        self.assertFalse(verify_cap_trace(self.manifest, self.frames[:180])['success'])

    def test_contacts_and_model_required(self):
        for mutation in ('contact', 'force', 'helix', 'shaking'):
            frames = copy.deepcopy(self.frames)
            for row in frames:
                if mutation == 'contact':
                    row['commands'][0]['finger_contact_forces'] = [[[0., 0, 0]], [[0., 0, 0]]]
                elif mutation == 'force':
                    row['commands'][0]['thread_force_z'] = 1.
                elif mutation == 'helix':
                    row['objects_before_step'][0]['position'][2] += .02
                else:
                    row['objects_before_step'][0]['angular_velocity'] = [1., 0, 0]
            self.assertFalse(verify_cap_trace(self.manifest, frames)['success'], mutation)

    def test_empty_fails(self):
        self.assertFalse(verify_cap_trace(self.manifest, [])['success'])

    def test_clock_mismatch(self):
        self.frames[10]['physics_steps'] = 22
        self.assertFalse(verify_cap_trace(self.manifest, self.frames)['success'])
