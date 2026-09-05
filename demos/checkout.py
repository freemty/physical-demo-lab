"""Contact-driven pick, simulated scan and bagging; privileged SKU IDs, not vision."""
import traceback
from sim_runtime import Run

run = Run('supermarket_checkout')
try:
    import numpy as np
    from pxr import Gf, PhysxSchema, UsdPhysics, UsdGeom
    from checkout_verify import verify_checkout

    run.box('/World/Floor', [0, 0, -.03], [6, 6, .06], [.42]*3)
    run.box('/World/RobotPedestal', [0, 0, .35], [.22, .22, .70], [.24]*3)
    run.box('/World/Counter', [.05, -.4, .65], [1.90, .38, .10], [.38]*3)
    belt = run.box('/World/Belt', [.05, -.4, .705], [1.85, .29, .03], [.08]*3)
    UsdPhysics.RigidBodyAPI.Apply(belt).CreateKinematicEnabledAttr(True)
    surface = PhysxSchema.PhysxSurfaceVelocityAPI.Apply(belt)
    surface.CreateSurfaceVelocityEnabledAttr(True)
    surface.CreateSurfaceVelocityLocalSpaceAttr(False)
    surface.CreateSurfaceVelocityAttr(Gf.Vec3f(0, 0, 0))
    for suffix, y in [('Front', -.57), ('Back', -.23)]:
        run.box('/World/Rail'+suffix, [.05, y, .75], [1.92, .025, .07], [.55]*3)
    for i, x in enumerate([-.65, .75]):
        for j, y in enumerate([-.53, -.27]):
            run.box(f'/World/Leg{i}{j}', [x, y, .30], [.045, .045, .60], [.24]*3)

    # A fixed scanner fixture; only observed item occupancy creates scan events.
    run.box('/World/ScannerStand', [.49, .0, .38], [.28, .29, .76], [.32]*3)
    run.box('/World/ScannerGlass', [.49, .0, .775], [.23, .25, .025], [.14, .22, .25])
    run.box('/World/ScanLine', [.49, .0, .791], [.21, .009, .004], [.82, .10, .08])
    run.box('/World/MonitorPole', [.79, .13, .94], [.045, .05, .30], [.18]*3)
    run.box('/World/Monitor', [.79, .13, 1.14], [.32, .045, .23], [.14]*3)
    run.box('/World/Screen', [.79, .103, 1.14], [.285, .008, .195], [.07, .15, .18])
    indicators = []
    for i in range(3):
        indicators.append(run.box(f'/World/ReceiptLine{i}', [.79, .097, 1.19-i*.05], [.22, .008, .025], [.3]*3))
    floor, outer, rim, wall = .70, .42, .14, .015
    x, y = .38, .42
    run.box('/World/Bag/Base', [x, y, floor-.012], [outer, .30, .024], [.62, .57, .45])
    for suffix, dx, dy, sx, sy in [('L', -outer/2, 0, wall, .30), ('R', outer/2, 0, wall, .30),
                                  ('F', 0, -.15, outer, wall), ('B', 0, .15, outer, wall)]:
        run.box('/World/Bag/'+suffix, [x+dx, y+dy, floor+rim/2], [sx, sy, rim], [.62, .57, .45])
    run.box('/World/BagStand', [x, y, .33], [.12, .12, .66], [.24]*3)
    bag = {'color': 'bag', 'inner_lower': [x-outer/2+wall/2, y-.15+wall/2, floor],
           'inner_upper': [x+outer/2-wall/2, y+.15-wall/2, floor+rim]}
    robot = run.franka()
    colors = [[.72, .14, .11], [.10, .32, .69], [.79, .58, .12]]
    for i in range(3):
        size = float(run.rng.uniform(.044, .050))
        pos = [float(-i*.30+run.rng.uniform(-.02, .02)), float(-.4+run.rng.uniform(-.015, .015)), .724+size/2]
        run.add_box(f'product_{i}', pos, size, colors[i], mass=float(run.rng.uniform(.035, .065)),
                    color='bag', price_cents=[450, 720, 390][i], belt_displacement=0.,
                    placement=[.27+i*.11, .42, .70])
    scan_lower, scan_upper = [.36, -.12, .83], [.60, .13, .98]
    run.camera(eye=(2.1, -2.05, 2.05), target=(.15, -.03, .84))
    run.start({'control': 'privileged-state scripted differential IK', 'grasp': 'friction only',
               'bag': bag, 'scanner': {'lower': scan_lower, 'upper': scan_upper, 'dwell_frames': 12},
               'limitations': ['Known SKU IDs and poses; no barcode image recognition.',
                               'Stopped belt, procedural packages, no real payment transaction.']})
    durations = {'settle': 45, 'hover': 120, 'descend': 100, 'close': 75, 'lift': 100,
                 'above_scan': 120, 'scan_lower': 100, 'scan_sweep': 100, 'scan_lift': 100,
                 'above_bag': 120, 'lower': 100, 'release': 60, 'retract': 90}
    order = list(durations)
    phase, age, active, abort = 'feed', 0, 0, None
    pick, command = np.array([.35, -.4, .745]), np.array([.36, -.4, 1.1])
    phase_start = command.copy()
    scans, dwell = [], {o['id']: 0 for o in run.objects}
    for _ in range(run.args.max_steps):
        states = run.observe()
        for obj, state in zip(run.objects, states):
            inside = all(scan_lower[j] <= state['position'][j] <= scan_upper[j] for j in range(3))
            dwell[obj['id']] = dwell[obj['id']]+1 if inside else 0
            if dwell[obj['id']] >= 12 and obj['id'] not in [s['id'] for s in scans]:
                scan = {'id': obj['id'], 'price_cents': obj['price_cents'], 'step': run.step_count,
                        'position': state['position'], 'dwell_frames': dwell[obj['id']], 'inside_volume': inside}
                scans.append(scan)
                run.event('scan', **scan)
                UsdGeom.Cube(indicators[len(scans)-1]).GetDisplayColorAttr().Set([Gf.Vec3f(.12, .67, .29)])
        if phase != 'final_settle':
            obj, state = run.objects[active], states[active]
            dest = obj['placement']
        new_phase, closed = None, False
        if phase == 'feed':
            command = np.array([.36, -.4, 1.10])
            surface.GetSurfaceVelocityAttr().Set(Gf.Vec3f(.12, 0, 0))
            if state['position'][0] >= .35:
                surface.GetSurfaceVelocityAttr().Set(Gf.Vec3f(0, 0, 0))
                new_phase = 'settle'
            elif age > 900:
                abort = 'conveyor_failed_to_deliver'
                break
        elif phase in order:
            if phase == 'settle':
                pick = np.array(state['position'])
                obj['belt_displacement'] = float(pick[0]-obj['initial_position'][0])
            targets = {'settle': [pick[0], pick[1], 1.10], 'hover': [pick[0], pick[1], pick[2]+.28],
                'descend': [pick[0], pick[1], pick[2]+.10], 'close': [pick[0], pick[1], pick[2]+.10],
                'lift': [pick[0], pick[1], 1.16], 'above_scan': [.48, -.09, 1.16],
                'scan_lower': [.48, -.09, 1.00], 'scan_sweep': [.48, .10, 1.00],
                'scan_lift': [.48, .10, 1.16], 'above_bag': [dest[0], dest[1], 1.16],
                'lower': [dest[0], dest[1], dest[2]+.10+obj['size']/2+.025],
                'release': [dest[0], dest[1], dest[2]+.10+obj['size']/2+.025],
                'retract': [dest[0], dest[1], 1.16]}
            closed = phase in order[3:11]
            t = min(1., age/(durations[phase]*.8))
            t = t*t*(3-2*t)
            command = phase_start*(1-t)+np.array(targets[phase])*t
            if age >= durations[phase]:
                if phase == 'lift' and obj['max_lift'] < .08:
                    abort = 'grasp_did_not_lift_object'
                    break
                if phase == 'scan_lift' and obj['id'] not in [s['id'] for s in scans]:
                    abort = 'item_not_scanned'
                    break
                if phase == 'retract':
                    active += 1
                    new_phase = 'feed' if active < len(run.objects) else 'final_settle'
                else:
                    new_phase = order[order.index(phase)+1]
        else:
            command = np.array([.38, 0, 1.18])
            if age >= 180:
                phase = 'done'
                break
        robot.set_end_effector_pose(command, [0., 1., 0., 0.])
        robot.close_gripper() if closed else robot.open_gripper()
        run.step(phase, [{'hand_target': command.tolist(), 'gripper_closed': closed}], states)
        age += 1
        if new_phase:
            phase, age = new_phase, 0
            phase_start = robot.get_current_state()[1][0].copy()
            run.event('phase', phase=phase, active_object=active)
    else:
        abort = 'step_budget_exhausted'
    final = []
    q, ee, _ = robot.get_current_state()
    for obj in run.objects:
        state = run.state(obj)
        state.update({k: obj[k] for k in ('color', 'size', 'max_lift', 'belt_displacement')})
        state['released_and_retracted'] = bool(min(q[0][-2:]) > .03 and np.linalg.norm(np.array(state['position'])-ee[0]) > .15)
        final.append(state)
    receipt = {'currency': 'simulated cents', 'lines': scans, 'total_cents': sum(s['price_cents'] for s in scans)}
    run.write('receipt.json', receipt)
    verification = verify_checkout(final, bag, run.manifest['objects'], scans)
    run.finish({'success': phase == 'done' and abort is None and verification['success'],
                'phase': phase, 'abort_reason': abort, 'verification': verification,
                'objects': final, 'receipt': receipt})
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type': type(error).__name__, 'message': str(error)})
    run.close(1)
