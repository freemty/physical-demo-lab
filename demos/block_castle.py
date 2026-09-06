"""Native Isaac Sim castle assembly. Goal mode is a stability test, not a demo."""
import argparse
import math
from pathlib import Path
import sys
import traceback
import faulthandler
import signal

faulthandler.register(signal.SIGUSR1, all_threads=True)

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--mode', choices=['goal','loose','assemble'], default='assemble')
parser.add_argument('--parts', type=int, default=20)
parser.add_argument('--velocity-iterations', type=int, default=4)
parser.add_argument('--solver', choices=['TGS','PGS'], default='TGS')
parser.add_argument('--ir', type=Path, default=Path(__file__).resolve().parents[1]/'assets/block_castle/scene_spec.json')
options, remaining = parser.parse_known_args()
sys.argv = [sys.argv[0]]+remaining
from castle_backend import CastleRun
from castle_verify import StableOracle, check_castle
from castle_control import CastleController

run = CastleRun(options.mode, options.ir, solver=options.solver,
                velocity_iterations=options.velocity_iterations, max_steps=50000)
try:
    import numpy as np
    run.build()
    run.start_castle()
    oracle = StableOracle(run.spec)
    robot = run.robot
    controller = CastleController(robot)
    down = np.array([0., math.sqrt(.5), math.sqrt(.5), 0.])
    verification = oracle.update(0., run.observe(), run.contact_records)
    run.write('initial-verification.json', verification)
    abort, completed = None, []

    def tick(phase, target=None, closed=False, orientation=None):
        if run.step_count >= run.args.max_steps:
            raise RuntimeError('step_budget_exhausted')
        states = run.observe()
        if target is not None:
            controller.target(target, down if orientation is None else orientation)
            robot.close_gripper() if closed else robot.open_gripper()
        run.step(phase, [{'hand_target':None if target is None else np.asarray(target,dtype=float).tolist(), 'gripper_closed':closed,
                         'orientation':(down if orientation is None else orientation).tolist(),
                         'native_drive_command': controller.last_record}], states)
        return run.physics_verification

    if options.mode != 'assemble':
        initial = run.observe()
        for _ in range(min(360,run.args.max_steps)):
            verification = tick(options.mode)
        final = run.observe()
        drift = max(float(np.linalg.norm(np.array(a['position'])-b['position'])) for a,b in zip(initial,final))
        success = verification['success'] if options.mode == 'goal' else not verification['all_valid'] and drift < .005
        run.finish({'success':success, 'mode':options.mode, 'assembly_demonstration':False,
                    'max_drift_m':drift, 'verification':verification,
                    'max_penetration_m':run.max_penetration, 'arm_contact_samples':run.arm_contact_samples})
    else:
        if verification['all_valid']:
            raise RuntimeError('initial_state_already_solved')
        cruise = 1.18

        def move(phase, destination, seconds, closed=False, orientation=None):
            start = robot.get_current_state()[1][0].copy()
            dest = np.array(destination, dtype=float)
            count = max(30, int(seconds*60))
            result = None
            for i in range(count):
                t = min(1., (i+1)/(count*.8))
                s = t*t*(3-2*t)
                result = tick(phase, start+(dest-start)*s, closed, orientation)
            extra_steps = 0
            # Bounded convergence dwell; preserve the 15 mm motion abort and task oracle.
            while extra_steps < 180:
                ee = robot.get_current_state()[1][0]
                if float(np.linalg.norm(ee-dest)) <= .004:
                    break
                result = tick(phase+':converge', dest, closed, orientation)
                extra_steps += 1
            ee = robot.get_current_state()[1][0]
            residual = float(np.linalg.norm(ee-dest))
            run.event('motion_end', phase=phase, residual_m=residual, convergence_steps=extra_steps, hand=ee.tolist(), target=dest.tolist())
            if residual > .015:
                raise RuntimeError(f'hand_target_unreached:{phase}:{residual:.6f}')
            return result

        def hold(phase, seconds, closed=False, orientation=None):
            target = robot.get_current_state()[1][0].copy()
            for _ in range(int(seconds*60)):
                result = tick(phase,target,closed,orientation)
            return result

        for name in run.spec['task']['assembly_order'][:options.parts]:
            obj = next(o for o in run.objects if o['id']==name)
            checks = check_castle(run.spec,run.observe(),run.contact_records)
            for support in obj['supports']:
                if support != 'foundation' and not checks['blocks'][support]['valid']:
                    raise RuntimeError(f'support_not_valid:{name}:{support}')
            state = run.state(obj)
            pick = np.array(state['position'])
            w,x,y,z = state['orientation']
            yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
            pick_down = np.array([0.,math.cos((math.pi/2+yaw)/2),math.sin((math.pi/2+yaw)/2),0.])
            current = robot.get_current_state()[1][0]
            run.event('part_start', name=name, ordinal=len(completed), pick=pick.tolist())
            move(name+':clear',[current[0],current[1],cruise],1.5,orientation=pick_down)
            move(name+':hover',[pick[0],pick[1],cruise],3.,orientation=pick_down)
            grasp = pick+np.array([0,0,.102+obj['grasp_offset_z']])
            move(name+':descend',grasp,2.5,orientation=pick_down)
            hold(name+':open_settle',.4,orientation=pick_down)
            hold(name+':close',1.,True,pick_down)
            move(name+':lift',[pick[0],pick[1],cruise],2.5,True,pick_down)
            if run.state(obj)['position'][2] < 1.02:
                raise RuntimeError('not_lifted:'+name)
            target = np.array(obj['target'])
            move(name+':traverse',[target[0],target[1],cruise],3.,True,down)
            held = np.array(run.state(obj)['position'])
            offset = robot.get_current_state()[1][0]-held
            place = target+offset+np.array([0,0,.002])
            move(name+':lower',place,2.5,True,down)
            hold(name+':pre_release',.3,True,down)
            hold(name+':release',.6,False,down)
            move(name+':retreat',[place[0],place[1],cruise],2.,False,down)
            verification = hold(name+':settle',.6,False,down)
            check = verification['blocks'][name]
            run.event('part_end',name=name,verification=check)
            if not check['valid']:
                raise RuntimeError('placed_part_invalid:'+name)
            completed.append(name)
        move('park',[-.10,-.30,1.20],2.)
        verification = hold('final_settle',4.)
        run.finish({'success':len(completed)==20 and verification['success'], 'mode':options.mode,
                    'completed_parts':completed, 'verification':verification,
                    'max_penetration_m':run.max_penetration, 'arm_contact_samples':run.arm_contact_samples})
except BaseException as error:
    if isinstance(error,SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type':type(error).__name__, 'message':str(error)})
    if run.trajectory is not None:
        run.finish({'success':False,'mode':options.mode,'abort_reason':str(error),
                    'completed_parts':locals().get('completed',[]),
                    'verification':locals().get('verification'), 'objects':run.observe(),
                    'max_penetration_m':run.max_penetration,'arm_contact_samples':run.arm_contact_samples})
    else:
        run.close(1)
