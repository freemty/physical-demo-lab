import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from restaurant_verify import contained, verify_delivery_trace


def state(name, p):
    return {'id': name, 'position': p, 'orientation': [1., 0., 0., 0.],
            'linear_velocity': [0., 0., 0.], 'angular_velocity': [0., 0., 0.]}


def example():
    manifest = {'physics_dt': 1/60, 'delivery_goal': [2.7, 0.], 'objects': [
        {'id': 'meal_box', 'role': 'meal', 'size': .06, 'initial_position': [0., 0., .734]},
        {'id': 'drink_carton', 'role': 'meal', 'size': .052, 'initial_position': [.1, 0., .73]},
        {'id': 'service_cart', 'role': 'carrier', 'initial_position': [.4, 0., .13]}]}
    frames = []
    for i in range(304):
        x = .4+min(120, max(0, i-3))/120*2.3
        phase = 'lift' if i < 2 else 'navigate' if i < 124 else 'final_settle'
        foods = [state('meal_box', [x-.065, 0., .8]), state('drink_carton', [x+.065, 0., .796])]
        if i < 2:
            foods[i]['position'][2] = 1.
        arm_p = foods[i]['position'][:] if i < 2 else [0., -1., 1.2]
        arm_q = [[0.]*7+[.025, .025]] if i < 2 else [[0.]*7+[.04, .04]]
        robots = [{'joints': arm_q, 'hand_position': [arm_p]}, {'joints': [[i*.25, i*.25]]}]
        frames.append({'phase': phase, 'objects_after_step': foods+[state('service_cart', [x, 0., .13])], 'robots': robots})
    return manifest, frames


class DeliveryTest(unittest.TestCase):
    def test_complete_transport(self):
        m, frames = example()
        self.assertTrue(verify_delivery_trace(m, frames)['success'])

    def test_no_wheels_or_short_trip(self):
        m, frames = example()
        for f in frames:
            f['robots'][1]['joints'] = [[0., 0.]]
        result = verify_delivery_trace(m, frames)
        self.assertFalse(result['success'])
        self.assertFalse(result['checks']['wheels_really_rotated'])
        m, frames = example()
        self.assertFalse(verify_delivery_trace(m, frames[:120])['success'])

    def test_spill_or_unlifted_fails(self):
        m, frames = example()
        frames[80]['objects_after_step'][0]['position'][1] = .3
        self.assertFalse(verify_delivery_trace(m, frames)['checks']['contained_through_transport'])
        m, frames = example()
        frames[0]['robots'][0]['joints'][0][-2:] = [.04, .04]
        self.assertFalse(verify_delivery_trace(m, frames)['checks']['both_physically_lifted'])

    def test_last_frame_is_not_continuous_stability(self):
        m, frames = example()
        frames[-20]['objects_after_step'][0]['linear_velocity'] = [.3, 0., 0.]
        self.assertFalse(verify_delivery_trace(m, frames)['checks']['stable_delivery_three_seconds'])

    def test_rotated_tray_and_height(self):
        cart = state('service_cart', [1., 2., .13])
        cart['orientation'] = [2**-.5, 0., 0., 2**-.5]
        food = state('meal_box', [1., 2.07, .8])
        self.assertTrue(contained(food, cart, {'size': .06}))
        food['position'][2] += .05
        self.assertFalse(contained(food, cart, {'size': .06}))


if __name__ == '__main__':
    unittest.main()
