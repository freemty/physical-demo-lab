"""Fixed-arm loading followed by a contact-driven differential service cart."""
import json
import math
import sys
import traceback
from sim_runtime import Run

zero_wheels = '--zero-wheels' in sys.argv
if zero_wheels:
    sys.argv.remove('--zero-wheels')
run = Run('restaurant', max_steps=7200)
try:
    import numpy as np
    from service_cart import ServiceCart
    from restaurant_verify import DeliveryAudit
    from gear_verify import yaw_of, wrap

    run.box('/World/Floor', [1.3, .5, -.03], [5., 4., .06], [.38]*3)
    run.box('/World/Counter', [.45, -.40, .66], [.85, .50, .08], [.56, .49, .38])
    run.box('/World/ArmPedestal', [0, -.32, .35], [.22, .22, .7], [.25]*3)
    arm = run.franka(position=(0, -.32, .7))
    for i, xy in enumerate([(.18, -.58), (.75, -.58)]):
        run.box('/World/CounterLeg'+str(i), [*xy, .32], [.07, .07, .64], [.26]*3)
    run.box('/World/DiningTable', [2.55, 1.49, .715], [.8, .55, .07], [.55, .46, .34])
    for i, xy in enumerate([(2.25, 1.3), (2.85, 1.7)]):
        run.box('/World/TableLeg'+str(i), [*xy, .34], [.06, .06, .68], [.25]*3)
    for i, x in enumerate([2.2, 2.9]):
        run.box('/World/ChairSeat'+str(i), [x, 1.99, .43], [.32, .32, .045], [.37]*3)
        run.box('/World/ChairBack'+str(i), [x, 2.13, .67], [.32, .045, .48], [.37]*3)
        run.box('/World/ChairBase'+str(i), [x, 1.99, .20], [.12, .12, .40], [.27]*3)
    food_inputs = [('meal_box', .36, -.43, .060, [.81, .53, .26]),
                   ('drink_carton', .60, -.45, .052, [.48, .66, .69])]
    for name, x, y, size, color in food_inputs:
        position = [float(x+run.rng.uniform(-.008, .008)), float(y+run.rng.uniform(-.008, .008)), .704+size/2]
        run.add_box(name, position, size, color, mass=float(run.rng.uniform(.07, .10)), role='meal')
    cart = ServiceCart(run, [.48, .17, .13])
    run.camera(eye=(4.15, -4.25, 3.50), target=(1.2, .35, .5))
    waypoints = [[1.2, .17], [1.9, .78], [2.65, .83]]
    run.start({'delivery_goal': waypoints[-1], 'waypoints': waypoints,
               'negative_zero_wheels': zero_wheels,
               'cart_model': {'wheel_radius': cart.RADIUS, 'track': cart.TRACK,
                              'mass_kg': 8., 'center_of_mass_local': [0, 0, .015],
                              'diagonal_inertia_kg_m2': [.16, .18, .15]},
               'limitations': ['Fixed loading arm plus a separate cart, not the reference mobile dual arm.',
                               'Known states and waypoints; rigid food containers, no fluid, vision, people or table unloading.',
                               'No grasp attachments, runtime body pose/velocity writes, or direct propulsion forces.']})
    verifier = DeliveryAudit(run.manifest)
    park = np.array([.25, -.58, 1.18])
    phases = [('hover', 100), ('descend', 100), ('close', 90), ('lift', 110),
              ('above_cart', 150), ('lower', 120), ('release', 90), ('retract', 110), ('park', 100)]
    active, phase_idx, age, waypoint, abort = 0, 0, 0, 0, None
    phase_start = arm.get_current_state()[1][0].copy()
    pick = np.array(run.state(run.objects[active])['position'])
    phase = 'hover'
    for _ in range(run.args.max_steps):
        states = run.observe()
        driving = active == 2
        linear, angular, closed = 0., 0., False
        if not driving:
            phase, duration = phases[phase_idx]
            # Tray is dynamic; destinations follow its observed pose, not an ideal reset.
            from gear_verify import multiply_quaternions
            c = states[2]
            local = [(-.065 if active == 0 else .065), 0, .640+run.objects[active]['size']/2]
            rot = multiply_quaternions(multiply_quaternions(c['orientation'], [0.]+local),
                                      [c['orientation'][0]]+[-x for x in c['orientation'][1:]])[1:]
            target = np.array(c['position'])+np.array(rot)
            dest = {'hover': [pick[0], pick[1], 1.18], 'descend': pick+[0, 0, .10],
                    'close': pick+[0, 0, .10], 'lift': [pick[0], pick[1], 1.18],
                    'above_cart': [target[0], target[1], 1.18], 'lower': target+[0, 0, .106],
                    'release': target+[0, 0, .106], 'retract': [target[0], target[1], 1.18], 'park': park}[phase]
            t = min(1., age/(duration*.8))
            t = t*t*(3-2*t)
            cmd = phase_start*(1-t)+np.array(dest)*t
            closed = phase in ('close', 'lift', 'above_cart', 'lower')
        else:
            cmd = park
            if waypoint < len(waypoints):
                phase = 'navigate'
                p, q = states[2]['position'], states[2]['orientation']
                dx, dy = waypoints[waypoint][0]-p[0], waypoints[waypoint][1]-p[1]
                distance, error = math.hypot(dx, dy), wrap(math.atan2(dy, dx)-yaw_of(q))
                if distance < .045:
                    waypoint += 1
                    run.event('waypoint_reached', waypoint=waypoint, position=p)
                else:
                    angular = float(np.clip(2.0*error, -.7, .7))
                    linear = min(.25, .8*distance)*max(0., math.cos(error)) if abs(error) < .6 else 0.
            else:
                phase = 'final_settle'
        arm.set_end_effector_pose(cmd, [0., 1., 0., 0.])
        arm.close_gripper() if closed else arm.open_gripper()
        speeds = cart.drive(0. if zero_wheels else linear, 0. if zero_wheels else angular)
        commands = [{'robot': 0, 'hand_target': cmd.tolist(), 'gripper_closed': closed, 'active_object': active},
                    {'robot': 1, 'wheel_targets_rad_s': speeds, 'waypoint_index': waypoint}]
        run.step(phase, commands, states)
        robots = []
        for robot in run.robots:
            q, p, orientation = robot.get_current_state()
            robots.append({'joints': q.tolist(), 'hand_position': p.tolist(), 'hand_orientation': orientation.tolist()})
        verifier.add({'phase': phase, 'robots': robots, 'objects_after_step': run.observe()})
        age += 1
        if not driving and age >= duration:
            if phase == 'lift' and run.objects[active]['max_lift'] < .08:
                abort = 'meal_not_lifted'
                break
            phase_idx += 1
            if phase_idx == len(phases):
                active, phase_idx = active+1, 0
                if active < 2:
                    pick = np.array(run.state(run.objects[active])['position'])
            age = 0
            phase_start = arm.get_current_state()[1][0].copy()
            run.event('phase', phase='navigate' if active == 2 else phases[phase_idx][0], active_object=active)
        if driving and verifier.result()['success']:
            phase = 'done'
            break
    else:
        abort = 'step_budget_exhausted'
    verification = verifier.result()
    run.finish({'success': phase == 'done' and abort is None and verification['success'],
                'phase': phase, 'abort_reason': abort, 'objects': run.observe(), 'verification': verification})
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type': type(error).__name__, 'message': str(error)})
    run.close(1)
