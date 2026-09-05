"""Replay contact, passive coupling, disengagement and free held-cap evidence."""
import math


def verify_cap_trace(manifest, frames):
    spec = manifest['thread']
    coefficient = spec['pitch']/(2*math.pi)
    last_yaw, angle, released_step = 0., 0., None
    max_error, max_force_residual, contact_rotation = 0., 0., 0.
    held_frames, best_held, contact_frames = 0, 0, 0
    finite, release_valid, no_reengagement, clock_valid = True, False, True, True
    links = manifest['contact_links']
    last = None
    for frame in frames:
        clock_valid &= frame['physics_steps'] == frame['step']+1 and math.isclose(
            frame['sim_time'], (frame['step']+1)*manifest['physics_dt'], abs_tol=1e-7)
        state, command = frame['objects_before_step'][0], frame['commands'][0]
        p, q = state['position'], state['orientation']
        values = p+q+state['linear_velocity']+state['angular_velocity']
        finite &= all(math.isfinite(v) for v in values)
        yaw = math.atan2(2*(q[0]*q[3]+q[1]*q[2]), 1-2*(q[2]*q[2]+q[3]*q[3]))
        delta = math.atan2(math.sin(yaw-last_yaw), math.cos(yaw-last_yaw))
        angle += delta
        last_yaw = yaw
        contact_fingers = set()
        for link, force in zip(links, command['finger_contact_forces']):
            if sum(v*v for v in force[0]) > .05**2:
                contact_fingers.add(link.rsplit('/', 1)[-1].split('_')[0])
        if contact_fingers:
            contact_frames += 1
            if released_step is None:
                contact_rotation += max(0., delta)
        if not command['thread_engaged'] and released_step is None:
            released_step = frame['step']
            release_valid = angle >= spec['release_angle'] and angle-delta < spec['release_angle']
        if released_step is not None:
            no_reengagement &= not command['thread_engaged']
        error = p[2]-spec['z0']-coefficient*angle
        if command['thread_engaged']:
            max_error = max(max_error, abs(error))
            expected_force = -spec['spring']*error-spec['damping']*(state['linear_velocity'][2]-coefficient*state['angular_velocity'][2])
            expected_torque = -coefficient*expected_force-spec['rotary_drag']*state['angular_velocity'][2]
        else:
            expected_force, expected_torque = 0., 0.
        max_force_residual = max(max_force_residual, abs(command['thread_force_z']-expected_force),
                                 abs(command['thread_torque_z']-expected_torque))
        if (released_step is not None and p[2]-spec['z0'] >= .1 and len(contact_fingers) >= 2
                and 'thumb' in contact_fingers
                and sum(v*v for v in state['linear_velocity']) < .03**2
                and sum(v*v for v in state['angular_velocity']) < .5**2):
            held_frames += 1
        else:
            held_frames = 0
        best_held = max(best_held, held_frames)
        last = state
    checks = {'finite_state': bool(finite and last is not None), 'trajectory_clock': clock_valid,
              'actual_half_turn_disengagement': release_valid,
              'passive_coupling_replayed': max_force_residual < 1e-6,
              'helix_error_under_6mm': max_error <= .006, 'no_reengagement': no_reengagement,
              'contact_driven_rotation': contact_rotation >= 2.5 and contact_frames >= 120,
              'held_free_above_bottle_two_seconds': held_frames*manifest['physics_dt'] >= 2.,
              'final_lift_over_100mm': last is not None and last['position'][2]-spec['z0'] >= .1}
    return {'success': all(checks.values()), 'checks': checks, 'released_step': released_step,
            'max_helix_error': max_error, 'max_force_replay_residual': max_force_residual,
            'contact_rotation': contact_rotation, 'contact_frames': contact_frames,
            'final_hold_seconds': held_frames*manifest['physics_dt'],
            'best_hold_seconds': best_held*manifest['physics_dt']}
