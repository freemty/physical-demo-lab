"""Physically grasp and seat a holed compound gear beside a fixed meshing gear."""
import math
import traceback
from sim_runtime import Run

run = Run('gear_assembly', max_steps=5000)
try:
    import numpy as np
    from isaacsim.core.experimental.prims import RigidPrim
    from assembly_parts import gear, cylinder
    from gear_verify import verify_gear, multiply_quaternions

    run.box('/World/Floor', [0, 0, -.03], [5, 5, .06], [.40]*3)
    run.box('/World/RobotPedestal', [0, 0, .35], [.22, .22, .70], [.24]*3)
    run.box('/World/Table', [.49, 0, .66], [.74, 1.05, .08], [.47]*3)
    for i, x in enumerate([.2, .78]):
        for j, y in enumerate([-.44, .44]):
            run.box(f'/World/Leg{i}{j}', [x, y, .32], [.05, .05, .64], [.25]*3)
    target = {'position': [.43, .25, .730], 'yaw': 0.}
    run.box('/World/AssemblyBase', [.47, .25, .710], [.25, .19, .020], [.24, .27, .29])
    for i, x in enumerate([.43, .5115]):
        cylinder(run, f'/World/Axle_{i}', [x, .25, .7425], .005, .045, [.65]*3)
    gear(run, 'MountedGear', [.5115, .25, .730], dynamic=False, yaw=math.pi/20, color=(.57, .59, .61))
    initial = [float(.36+run.rng.uniform(-.015, .015)), float(-.29+run.rng.uniform(-.015, .015)), .714]
    mass = float(run.rng.uniform(.05, .08))
    gear(run, 'MovingGear', initial, mass=mass, color=(.72, .49, .18))
    obj = {'id': 'MovingGear', 'initial_position': initial, 'mass': mass, 'max_lift': 0.,
           'outer_radius': .0435, 'bore_radius': .009, 'disc_height': .020,
           'body': RigidPrim('/World/MovingGear')}
    run.objects.append(obj)
    robot = run.franka()
    run.camera(eye=(1.50, -1.75, 1.85), target=(.29, .0, .83))
    run.start({'target': target, 'control': 'privileged-pose IK with carried-part alignment feedback',
        'geometry': {'teeth': 20, 'tooth_width': .003, 'fixed_neighbor_center': [.5115, .25, .73], 'fixed_neighbor_yaw': math.pi/20,
                     'axle_radius': .005, 'hole_radius': .009, 'base_top': .72},
        'limitations': ['Compound box teeth, not involute gears.', 'Fixed neighbor; no loaded transmission test.',
                       'No visual perception, grasp attachment or object pose edits.']})
    phases = [('hover', 120), ('descend', 120), ('close', 90), ('lift', 120),
              ('transit', 140), ('above_axle', 140), ('align', 120), ('insert', 180),
              ('release', 90), ('retract', 120), ('settle', 180)]
    phase_idx, age, abort = 0, 0, None
    phase_start = robot.get_current_state()[1][0].copy()
    pick = np.array(run.state(obj)['position'])
    carry_offset = np.array([0., 0., .13])
    command, orientation = phase_start.copy(), [0., 1., 0., 0.]
    for _ in range(run.args.max_steps):
        states = run.observe()
        state = states[0]
        phase, duration = phases[phase_idx]
        q, ee, ee_quat = robot.get_current_state()
        targets = {'hover': [pick[0], pick[1], 1.08], 'descend': [pick[0], pick[1], pick[2]+.13],
                   'close': [pick[0], pick[1], pick[2]+.13], 'lift': [pick[0], pick[1], 1.12],
                   'transit': [.43, .0, 1.13], 'above_axle': [.43, .25, 1.13],
                   'align': np.array([.43, .25, .82])+carry_offset,
                   'insert': np.array(target['position'])+carry_offset,
                   'release': np.array(target['position'])+carry_offset,
                   'retract': [.43, .25, 1.13], 'settle': [.34, -.1, 1.16]}
        if phase in ('align', 'insert'):
            desired_part = np.array([.43, .25, .82]) if phase == 'align' else np.array(target['position'])
            targets[phase] = ee[0]+desired_part-np.array(state['position'])
            # Correct the carried part in all three rotational axes. Merely
            # keeping the palm downward leaves grasp-induced gear tilt intact.
            w, x, y, z = state['orientation']
            orientation = multiply_quaternions([w, -x, -y, -z], ee_quat[0])
        t = min(1., age/(duration*.8))
        t = t*t*(3-2*t)
        command = phase_start*(1-t)+np.array(targets[phase])*t
        closed = phase in ('close', 'lift', 'transit', 'above_axle', 'align', 'insert')
        robot.set_end_effector_pose(command, orientation)
        robot.close_gripper() if closed else robot.open_gripper()
        run.step(phase, [{'hand_target': command.tolist(), 'orientation': orientation, 'gripper_closed': closed}], states)
        age += 1
        if age >= duration:
            if phase == 'lift':
                if obj['max_lift'] < .08:
                    abort = 'gear_not_lifted'
                    break
                carry_offset = robot.get_current_state()[1][0]-np.array(run.state(obj)['position'])
            if phase == 'insert':
                carry_offset = robot.get_current_state()[1][0]-np.array(run.state(obj)['position'])
            phase_idx += 1
            if phase_idx == len(phases):
                break
            age = 0
            phase_start = robot.get_current_state()[1][0].copy()
            run.event('phase', phase=phases[phase_idx][0], active_object=0)
    else:
        abort = 'step_budget_exhausted'
    state = run.state(obj)
    q, ee, _ = robot.get_current_state()
    state['max_lift'] = obj['max_lift']
    state['released_and_retracted'] = bool(min(q[0][-2:]) > .03 and np.linalg.norm(np.array(state['position'])-ee[0]) > .15)
    verification = verify_gear(state, target)
    run.finish({'success': abort is None and phase_idx == len(phases) and verification['success'],
                'phase': 'done' if phase_idx == len(phases) else phases[phase_idx][0],
                'abort_reason': abort, 'objects': [state], 'verification': verification})
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type': type(error).__name__, 'message': str(error)})
    run.close(1)
