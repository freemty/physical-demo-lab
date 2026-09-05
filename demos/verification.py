"""Simulator-independent, fail-closed physical outcome checks (SI units)."""
from math import isfinite, sqrt


def rotated_half_extents(quaternion, half_size):
    w, x, y, z = quaternion
    norm = sqrt(w*w + x*x + y*y + z*z)
    if norm < 1e-8:
        raise ValueError("zero quaternion")
    w, x, y, z = (v / norm for v in (w, x, y, z))
    rotation = [
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ]
    return [sum(abs(v)*half_size for v in row) for row in rotation]


def verify_object(state, destination):
    numbers = state['position'] + state['orientation'] + state['linear_velocity'] + state['angular_velocity']
    if not all(isfinite(v) for v in numbers):
        return {'success': False, 'checks': {'finite_state': False}}
    extents = rotated_half_extents(state['orientation'], state['size']/2)
    p, lower, upper = state['position'], destination['inner_lower'], destination['inner_upper']
    checks = {
        'correct_bin': state['color'] == destination['color'],
        'inside_bin_xy': all(lower[i] <= p[i]-extents[i] and p[i]+extents[i] <= upper[i] for i in (0, 1)),
        'above_bin_floor': p[2]-extents[2] >= lower[2]-0.008,
        'below_bin_rim': p[2]+extents[2] <= upper[2]+0.008,
        'settled_linear': sum(v*v for v in state['linear_velocity']) < 0.025**2,
        'settled_angular': sum(v*v for v in state['angular_velocity']) < 0.35**2,
        'physically_lifted': state['max_lift'] > 0.08,
        'belt_transport_observed': state['belt_displacement'] > 0.05,
        'released_and_retracted': bool(state['released_and_retracted']),
    }
    return {'success': all(checks.values()), 'checks': checks}
