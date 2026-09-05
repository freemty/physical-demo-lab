"""Two Frankas take turns physically building a two-pillar wooden bridge."""
import traceback
from sim_runtime import Run

run = Run('dual_blocks', max_steps=7000)
try:
    import numpy as np
    from isaacsim.core.experimental.prims import RigidPrim
    from blocks_verify import verify_bridge

    run.box('/World/Floor', [0, 0, -.03], [5, 5, .06], [.36]*3)
    run.box('/World/Table', [.48, 0, .66], [.84, 1.55, .08], [.47, .39, .29])
    for i, y in enumerate([-.43, .43]):
        run.box(f'/World/Pedestal{i}', [0, y, .35], [.22, .22, .7], [.24]*3)
        run.franka(f'/World/Franka{i}', (0, y, .7))
    for i, x in enumerate([.2, .8]):
        for j, y in enumerate([-.65, .65]):
            run.box(f'/World/Leg{i}{j}', [x, y, .32], [.05, .05, .64], [.25]*3)
    targets = [
        {'id': 'pillar_left', 'role': 'pillar', 'position': [.39, 0, .73]},
        {'id': 'pillar_right', 'role': 'pillar', 'position': [.55, 0, .73]},
        {'id': 'beam', 'role': 'beam', 'position': [.47, 0, .7825]},
    ]
    inputs = [(.37, -.43), (.42, .43), (.63, -.45)]
    for i, (target, (x, y)) in enumerate(zip(targets, inputs)):
        size = [.06]*3 if i < 2 else [.26, .055, .045]
        position = [float(x+run.rng.uniform(-.01, .01)), float(y+run.rng.uniform(-.01, .01)), .704+size[2]/2]
        mass = float(run.rng.uniform(.045, .065)) if i < 2 else float(run.rng.uniform(.075, .095))
        name = target['id']
        run.box('/World/'+name, position, size, [.73, .59, .37], True, mass, 1.2)
        run.objects.append({'id': name, 'initial_position': position, 'dimensions': size, 'mass': mass,
                            'max_lift': 0., 'owner': [0, 1, 0][i], 'body': RigidPrim('/World/'+name)})
    run.camera(eye=(2.1, -2.35, 2.25), target=(.28, 0, .83))
    run.start({'targets': targets, 'control': 'two world-pose IK arms with sequential workspace reservation',
               'limitations': ['Known states, not visual or learned control.', 'Sequential work; no handover or joint grasp.',
                               'No state edits or attachment constraints; support is geometry plus gravity stability.']})
    parks = [np.array([.30, -.64, 1.18]), np.array([.30, .64, 1.18])]
    phases = [('hover', 120), ('descend', 110), ('close', 90), ('lift', 120),
              ('above_target', 160), ('lower', 130), ('release', 90), ('retract', 120), ('park', 100)]
    active, phase_idx, age, abort = 0, 0, 0, None
    owner = run.objects[active]['owner']
    phase_start = run.robots[owner].get_current_state()[1][0].copy()
    pick = np.array(run.state(run.objects[active])['position'])
    participants = set()
    for _ in range(run.args.max_steps):
        states = run.observe()
        final_settle = active == len(run.objects)
        phase, duration = ('final_settle', 240) if final_settle else phases[phase_idx]
        commands = []
        if not final_settle:
            obj, state = run.objects[active], states[active]
            owner = obj['owner']
            target = np.array(targets[active]['position'])
            dest = {'hover': [pick[0], pick[1], 1.18], 'descend': pick+[0, 0, .10],
                    'close': pick+[0, 0, .10], 'lift': [pick[0], pick[1], 1.18],
                    'above_target': [target[0], target[1], 1.18],
                    'lower': target+[0, 0, .106], 'release': target+[0, 0, .106],
                    'retract': [target[0], target[1], 1.18], 'park': parks[owner]}[phase]
            t = min(1., age/(duration*.8))
            t = t*t*(3-2*t)
            command = phase_start*(1-t)+np.array(dest)*t
        for i, robot in enumerate(run.robots):
            closed = not final_settle and i == owner and phase in ('close', 'lift', 'above_target', 'lower')
            cmd = command if not final_settle and i == owner else parks[i]
            robot.set_end_effector_pose(cmd, [0., 1., 0., 0.])
            robot.close_gripper() if closed else robot.open_gripper()
            q, ee, _ = robot.get_current_state()
            if closed and min(q[0][-2:]) < .038 and obj['max_lift'] > .08 and np.linalg.norm(ee[0]-state['position']) < .16:
                participants.add(i)
            commands.append({'robot': i, 'hand_target': cmd.tolist(), 'gripper_closed': closed,
                             'active_object': active if not final_settle else None})
        run.step(phase, commands, states)
        age += 1
        if age >= duration:
            if final_settle:
                phase = 'done'
                break
            if phase == 'lift' and obj['max_lift'] < .08:
                abort = 'part_not_lifted'
                break
            phase_idx += 1
            if phase_idx == len(phases):
                active += 1
                phase_idx = 0
                if active < len(run.objects):
                    owner = run.objects[active]['owner']
                    pick = np.array(run.state(run.objects[active])['position'])
            age = 0
            phase_start = run.robots[owner].get_current_state()[1][0].copy()
            run.event('phase', phase='final_settle' if active == len(run.objects) else phases[phase_idx][0], active_object=active)
    else:
        abort = 'step_budget_exhausted'
    final = []
    for obj in run.objects:
        state = run.state(obj)
        state.update(max_lift=obj['max_lift'], released_and_retracted=all(
            min(robot.get_current_state()[0][0][-2:]) > .03 and
            np.linalg.norm(robot.get_current_state()[1][0]-state['position']) > .15 for robot in run.robots))
        final.append(state)
    verification = verify_bridge(final, targets, participants)
    run.finish({'success': phase == 'done' and abort is None and verification['success'],
                'phase': phase, 'abort_reason': abort, 'objects': final,
                'participating_robots': sorted(participants), 'verification': verification})
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type': type(error).__name__, 'message': str(error)})
    run.close(1)
