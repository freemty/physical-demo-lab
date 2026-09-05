"""Strict seated-gear checks, independent of the simulator interface."""
import math


def yaw_of(quaternion):
    w, x, y, z = quaternion
    return math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))


def wrap(angle):
    return (angle+math.pi) % (2*math.pi)-math.pi


def multiply_quaternions(a, b):
    w, x, y, z = a
    v, i, j, k = b
    return [w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j,
            w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v]


def verify_gear(state, target):
    p, q = state['position'], state['orientation']
    numbers = p+q+state['linear_velocity']+state['angular_velocity']
    if not all(math.isfinite(x) for x in numbers):
        return {'success': False, 'checks': {'finite_state': False}}
    yaw_error = abs(wrap(yaw_of(q)-target['yaw']))
    yaw_error = min(yaw_error % (2*math.pi/20), 2*math.pi/20-yaw_error % (2*math.pi/20))
    checks = {
        'centered_on_axle': math.hypot(p[0]-target['position'][0], p[1]-target['position'][1]) < .003,
        'seated_on_base': abs(p[2]-target['position'][2]) < .003,
        'axis_upright': math.acos(max(-1., min(1., 1-2*(q[1]**2+q[2]**2)))) < .10,
        'tooth_phase_aligned': yaw_error < .06,
        'physically_lifted': state['max_lift'] > .08,
        'settled_linear': sum(v*v for v in state['linear_velocity']) < .025**2,
        'settled_angular': sum(v*v for v in state['angular_velocity']) < .35**2,
        'released_and_retracted': bool(state['released_and_retracted']),
    }
    return {'success': all(checks.values()), 'checks': checks, 'yaw_error': yaw_error}
