"""Simulator-independent two-support bridge verification."""
import math


def verify_bridge(states, targets, participants):
    rows = []
    by_id = {state['id']: state for state in states}
    for target in targets:
        state = by_id.get(target['id'])
        if state is None:
            rows.append({'id': target['id'], 'success': False, 'checks': {'present': False}})
            continue
        p, q = state['position'], state['orientation']
        yaw = math.atan2(2*(q[0]*q[3]+q[1]*q[2]), 1-2*(q[2]**2+q[3]**2))
        yaw_error = abs((yaw+math.pi/2) % math.pi-math.pi/2)
        values = p+q+state['linear_velocity']+state['angular_velocity']
        checks = {
            'finite_state': all(math.isfinite(v) for v in values),
            'target_xy': math.hypot(p[0]-target['position'][0], p[1]-target['position'][1]) < .012,
            'supported_height': abs(p[2]-target['position'][2]) < .008,
            'level': math.acos(max(-1., min(1., 1-2*(q[1]**2+q[2]**2)))) < .10,
            'beam_heading': target['role'] != 'beam' or yaw_error < .12,
            'lifted': state['max_lift'] > .08,
            'settled_linear': sum(v*v for v in state['linear_velocity']) < .025**2,
            'settled_angular': sum(v*v for v in state['angular_velocity']) < .35**2,
            'released': state['released_and_retracted'],
        }
        rows.append({'id': state['id'], 'success': all(checks.values()), 'checks': checks})
    beam = next((by_id.get(t['id']) for t in targets if t['role'] == 'beam'), None)
    supported = beam is not None
    if beam:
        for target in targets:
            if target['role'] != 'pillar':
                continue
            pillar = by_id.get(target['id'])
            supported &= pillar is not None and abs(beam['position'][0]-pillar['position'][0]) < .115
            supported &= pillar is not None and abs(beam['position'][1]-pillar['position'][1]) < .022
            supported &= pillar is not None and abs(beam['position'][2]-.0225-(pillar['position'][2]+.030)) < .008
    checks = {'all_three_parts': len(states) == 3 and len(rows) == 3 and all(r['success'] for r in rows),
              'both_supports_covered': bool(supported), 'both_arms_participated': set(participants) == {0, 1}}
    return {'success': all(checks.values()), 'checks': checks, 'objects': rows}
