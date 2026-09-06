import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'demos'))
from castle_verify import check_castle, StableOracle


class CastleContract(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT/'assets/block_castle/scene_spec.json').read_text())
        self.blocks = [b for b in self.spec['objects'] if b.get('free')]
        self.states = [{'id':b['name'], 'position':b['target_pos'][:], 'orientation':[1,0,0,0],
                        'linear_velocity':[0,0,0], 'angular_velocity':[0,0,0]} for b in self.blocks]
        self.contacts = [{'body':b['name'],'other':s,'min_distance':0.} for b in self.blocks for s in b['supports']]

    def test_structure_is_twenty_free_boxes(self):
        self.assertEqual(len(self.blocks),20)
        seen = {'foundation'}
        for b in self.blocks:
            self.assertTrue(set(b['supports']) <= seen)
            seen.add(b['name'])
            solids = [g for g in b['geoms'] if g.get('collision')]
            self.assertEqual(len(solids),1)
            self.assertEqual(solids[0]['shape'],'box')

    def test_contacts_are_not_optional(self):
        self.assertTrue(check_castle(self.spec,self.states,self.contacts)['all_valid'])
        self.assertFalse(check_castle(self.spec,self.states,[])['all_valid'])
        for c in self.contacts:
            subset = [x for x in self.contacts if x is not c]
            self.assertFalse(check_castle(self.spec,self.states,subset)['all_valid'])

    def test_each_displaced_part_rejects(self):
        for i in range(20):
            states = copy.deepcopy(self.states)
            states[i]['position'][0] += .02
            self.assertFalse(check_castle(self.spec,states,self.contacts)['all_valid'])

    def test_release_rotation_speed_and_continuity(self):
        contacts = self.contacts+[{'body':'left_foot','other':'robot:panda_leftfinger','min_distance':0.}]
        self.assertFalse(check_castle(self.spec,self.states,contacts)['all_valid'])
        states = copy.deepcopy(self.states)
        states[0]['orientation'] = [0.70710678,0,0,0.70710678]
        self.assertFalse(check_castle(self.spec,states,self.contacts)['all_valid'])
        states = copy.deepcopy(self.states)
        states[0]['angular_velocity'][2] = .04
        self.assertFalse(check_castle(self.spec,states,self.contacts)['all_valid'])
        oracle = StableOracle(self.spec)
        self.assertFalse(oracle.update(0.,self.states,self.contacts)['success'])
        self.assertFalse(oracle.update(2.99,self.states,self.contacts)['success'])
        self.assertTrue(oracle.update(3.,self.states,self.contacts)['success'])
        self.assertFalse(oracle.update(3.01,self.states,[])['success'])


if __name__ == '__main__':
    unittest.main()
