import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from restaurant_appearance import linear_color, physics_signature, RestaurantAppearance


class Attribute:
    def __init__(self, name, value): self.name, self.value = name, value
    def GetName(self): return self.name
    def Get(self): return self.value


class Prim:
    def __init__(self, path, schemas, attributes):
        self.path, self.schemas, self.attributes = path, schemas, attributes
    def GetAppliedSchemas(self): return self.schemas
    def GetAttributes(self): return [Attribute(k, v) for k, v in self.attributes.items()]
    def GetRelationships(self): return []
    def GetPath(self): return self.path


class Stage:
    def __init__(self, prims): self.prims = prims
    def Traverse(self): return iter(self.prims)


class AppearanceTest(unittest.TestCase):
    def test_color_conversion(self):
        self.assertEqual(linear_color('000000'), [0., 0., 0.])
        self.assertEqual(linear_color('FFFFFF'), [1., 1., 1.])
        self.assertLess(linear_color('808080')[0], .22)

    def test_visual_addition_does_not_change_physics_signature(self):
        body = Prim('/World/Body', ['PhysicsRigidBodyAPI'], {'physics:mass': .1, 'xformOp:translate': [0, 0, 1]})
        stage = Stage([body])
        before = physics_signature(stage)[0]
        body.attributes['primvars:displayColor'] = [1, 0, 0]
        body.schemas.append('MaterialBindingAPI')
        stage.prims.append(Prim('/World/Decor', [], {'xformOp:translate': [5, 5, 5]}))
        self.assertEqual(before, physics_signature(stage)[0])

    def test_mass_and_body_pose_changes_are_rejected(self):
        body = Prim('/World/Body', ['PhysicsRigidBodyAPI'], {'physics:mass': .1, 'xformOp:translate': [0, 0, 1]})
        stage = Stage([body])
        before = physics_signature(stage)[0]
        body.attributes['physics:mass'] = .2
        self.assertNotEqual(before, physics_signature(stage)[0])
        body.attributes['physics:mass'] = .1
        body.attributes['xformOp:translate'] = [0, 0, 2]
        self.assertNotEqual(before, physics_signature(stage)[0])

    def test_collider_addition_is_detected(self):
        stage = Stage([])
        before = physics_signature(stage)[0]
        stage.prims.append(Prim('/World/Decor', ['PhysicsCollisionAPI'], {'size': 1.}))
        self.assertNotEqual(before, physics_signature(stage)[0])

    def test_three_distinct_shots(self):
        self.assertEqual(set(RestaurantAppearance.SHOTS), {'loading', 'travel', 'arrival'})
        self.assertEqual(len({tuple(c['eye']) for c in RestaurantAppearance.SHOTS.values()}), 3)


if __name__ == '__main__':
    unittest.main()
