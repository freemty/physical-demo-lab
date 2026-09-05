"""Replay physical loading, in-tray transport and continuous parked delivery."""
import math
from gear_verify import multiply_quaternions, wrap, yaw_of


def norm(v):
    return math.sqrt(sum(x*x for x in v))


def local_position(position, carrier):
    q = carrier['orientation']
    inv = [q[0], -q[1], -q[2], -q[3]]
    delta = [a-b for a, b in zip(position, carrier['position'])]
    return multiply_quaternions(multiply_quaternions(inv, [0.]+delta), q)[1:]


def contained(food, carrier, spec):
    p = local_position(food['position'], carrier)
    # Conservative planar footprint: the box's XY diagonal fits regardless of yaw.
    half_diagonal = spec['size']/math.sqrt(2)
    return (abs(p[0])+half_diagonal < .16 and abs(p[1])+half_diagonal < .115
            and abs(p[2]-(.640+spec['size']/2)) < .015)


class DeliveryAudit:
    def __init__(self, manifest):
        self.manifest = manifest
        self.foods = {o['id']: o for o in manifest['objects'] if o.get('role') == 'meal'}
        self.initial = next(o['initial_position'] for o in manifest['objects'] if o['id'] == 'service_cart')
        self.lifted, self.loaded = set(), False
        self.finite, self.contained_in_transit, self.upright = True, True, True
        self.path, self.travel, self.wheel_rotation = 0., 0., 0.
        self.previous, self.previous_angles, self.stable_frames, self.transit_frames = None, None, 0, 0
        self.final = None

    def add(self, frame):
        objs = {o['id']: o for o in frame['objects_after_step']}
        cart, arm = objs['service_cart'], frame['robots'][0]
        foods = [objs[key] for key in self.foods]
        self.finite &= all(math.isfinite(x) for o in objs.values() for k in
                           ('position', 'orientation', 'linear_velocity', 'angular_velocity') for x in o[k])
        for food in foods:
            near = norm([a-b for a, b in zip(food['position'], arm['hand_position'][0])]) < .16
            if near and min(arm['joints'][0][-2:]) < .038 and food['position'][2]-self.foods[food['id']]['initial_position'][2] > .08:
                self.lifted.add(food['id'])
        inside = all(contained(food, cart, self.foods[food['id']]) for food in foods)
        released = min(arm['joints'][0][-2:]) > .03 and all(
            norm([a-b for a, b in zip(food['position'], arm['hand_position'][0])]) > .15 for food in foods)
        q = cart['orientation']
        self.upright &= 1-2*(q[1]**2+q[2]**2) > math.cos(.15)
        angles = frame['robots'][1]['joints'][0]
        if self.previous_angles is not None and frame['phase'] in ('navigate', 'final_settle'):
            self.wheel_rotation += sum(abs(wrap(a-b)) for a, b in zip(angles, self.previous_angles))/2
        self.previous_angles = angles
        if frame['phase'] in ('navigate', 'final_settle'):
            if not self.transit_frames:
                self.loaded = inside and released and self.lifted == set(self.foods)
            self.transit_frames += 1
            self.contained_in_transit &= inside and released
            if self.previous is not None:
                self.path += math.hypot(cart['position'][0]-self.previous[0], cart['position'][1]-self.previous[1])
            self.travel = math.hypot(cart['position'][0]-self.initial[0], cart['position'][1]-self.initial[1])
        self.previous = cart['position']
        at_goal = math.hypot(cart['position'][0]-self.manifest['delivery_goal'][0],
                             cart['position'][1]-self.manifest['delivery_goal'][1]) < .08
        quiet = all(norm(o['linear_velocity']) < .025 and norm(o['angular_velocity']) < .4 for o in [cart]+foods)
        stable = frame['phase'] == 'final_settle' and inside and released and at_goal and quiet
        self.stable_frames = self.stable_frames+1 if stable else 0
        self.final = {'at_goal': at_goal, 'inside': inside, 'quiet': quiet, 'released': released}

    def result(self):
        checks = {'finite': bool(self.finite), 'both_physically_lifted': self.lifted == set(self.foods),
                  'loaded_before_departure': bool(self.loaded),
                  'contained_through_transport': bool(self.transit_frames > 0 and self.contained_in_transit),
                  'cart_upright': bool(self.upright), 'net_travel_two_meters': self.travel > 2.,
                  'path_two_meters': self.path > 2., 'wheels_really_rotated': self.wheel_rotation > 15.,
                  'stable_delivery_three_seconds': self.stable_frames*self.manifest['physics_dt'] >= 3.}
        return {'success': all(checks.values()), 'checks': checks, 'lifted': sorted(self.lifted),
                'travel': self.travel, 'path': self.path, 'wheel_rotation': self.wheel_rotation,
                'stable_seconds': self.stable_frames*self.manifest['physics_dt'], 'transit_frames': self.transit_frames,
                'final': self.final}


def verify_delivery_trace(manifest, frames):
    verifier = DeliveryAudit(manifest)
    for frame in frames:
        verifier.add(frame)
    return verifier.result()
