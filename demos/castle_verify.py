"""Simulator-independent castle oracle; contact evidence is mandatory."""
import math


def check_castle(spec, states, contacts):
    by_name = {s['id']: s for s in states}
    pairs = {}
    for c in contacts:
        pairs.setdefault(c['body'], {})[c['other']] = c
    checks = {}
    for block in spec['objects']:
        if not block.get('free'):
            continue
        name = block['name']
        state = by_name[name]
        p, goal = state['position'], block['target_pos']
        w, x, y, z = state['orientation']
        upright = 1-2*(x*x+y*y)
        yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        yaw_error = abs((yaw+math.pi/2) % math.pi-math.pi/2)
        xy = math.hypot(p[0]-goal[0], p[1]-goal[1])
        dz = abs(p[2]-goal[2])
        speed = math.sqrt(sum(v*v for v in state['linear_velocity']+state['angular_velocity']))
        actual = pairs.get(name, {})
        supported = all(s in actual and actual[s]['min_distance'] <= .0005 for s in block['supports'])
        released = not any(k.startswith('robot:') and c['min_distance'] <= .0005 for k, c in actual.items())
        checks[name] = {'xy_error': xy, 'z_error': dz, 'upright_cos': upright,
                        'yaw_error': yaw_error, 'speed': speed, 'supported': supported, 'released': released,
                        'valid': xy < .009 and dz < .006 and upright > math.cos(.07)
                        and yaw_error < .1 and speed < .035 and supported and released}
    return {'all_valid': len(checks) == 20 and all(c['valid'] for c in checks.values()), 'blocks': checks}


class StableOracle:
    def __init__(self, spec):
        self.spec, self.since, self.duration = spec, None, 0.

    def update(self, now, states, contacts):
        result = check_castle(self.spec, states, contacts)
        if result['all_valid']:
            self.since = now if self.since is None else self.since
            self.duration = now-self.since
        else:
            self.since, self.duration = None, 0.
        return dict(result, stable_seconds=self.duration, success=self.duration >= 3.)
