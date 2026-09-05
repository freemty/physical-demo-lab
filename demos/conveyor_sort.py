"""Headless conveyor sorting with a contact-driven Franka parallel gripper.

Privileged simulation poses/color labels feed a scripted state machine. No object
teleportation, grasp joints, hidden attachment, or learned-policy claim.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from importlib.metadata import distributions, version
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--objects', type=int, choices=(1, 2, 3), default=3)
parser.add_argument('--gpu', type=int, default=1, help='Physical renderer GPU index, matched against nvidia-smi at startup')
parser.add_argument('--output', type=Path, required=True, help='New output directory (existing paths are refused)')
parser.add_argument('--no-video', action='store_true')
parser.add_argument('--width', type=int, default=960)
parser.add_argument('--height', type=int, default=720)
parser.add_argument('--max-steps', type=int, default=7000)
invocation = sys.argv[:]
args, kit_args = parser.parse_known_args()
sys.argv = [sys.argv[0]] + kit_args
args.output.mkdir(parents=True, exist_ok=False)
source_root = Path(__file__).resolve().parents[1]
source_files = {}
for relative in ['README.md', 'demos/conveyor_sort.py', 'demos/verification.py',
                 'scripts/run.sh', 'scripts/setup_server.sh', 'scripts/evaluate.py', 'scripts/reuse_extscache.py']:
    source_path = source_root / relative
    target_path = args.output / 'source' / relative
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    source_files[relative] = hashlib.sha256(source_path.read_bytes()).hexdigest()
(args.output/'invocation.json').write_text(json.dumps({'argv': invocation, 'source_files': source_files}, indent=2))
os.environ.setdefault('OMNI_KIT_ACCEPT_EULA', 'YES')

from isaacsim import SimulationApp

app = SimulationApp({
    'headless': True, 'active_gpu': args.gpu, 'physics_gpu': args.gpu,
    'multi_gpu': False, 'renderer': 'RaytracedLighting',
    'width': args.width, 'height': args.height, 'sync_loads': True,
    'extra_args': ['--/app/settings/persistent=false', '--/app/asyncRendering=false',
                   '--/rtx-transient/resourcemanager/texturestreaming/enabled=false'],
})

import numpy as np
import carb
import omni.replicator.core as rep
import isaacsim.core.experimental.utils.app as app_utils
import isaacsim.core.experimental.utils.stage as stage_utils
from isaacsim.core.experimental.prims import RigidPrim
from isaacsim.core.simulation_manager import SimulationManager
from pxr import Gf, PhysxSchema, UsdGeom, UsdLux, UsdPhysics, UsdShade
from verification import verify_object

app_utils.enable_extension('isaacsim.robot.experimental.manipulators.examples')
from isaacsim.robot.experimental.manipulators.examples.franka import Franka

DT = 1/60
COLORS = {'red': [0.72, 0.12, 0.09], 'blue': [0.10, 0.30, 0.68]}
rng = np.random.default_rng(args.seed)
stage = stage_utils.get_current_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)
default = UsdGeom.Xform.Define(stage, '/World').GetPrim()
stage.SetDefaultPrim(default)


def box(path, position, scale, color, *, dynamic=False, mass=0.05, friction=0.8):
    shape = UsdGeom.Cube.Define(stage, path)
    shape.CreateSizeAttr(1.0)
    shape.AddTranslateOp().Set(Gf.Vec3d(*map(float, position)))
    shape.AddScaleOp().Set(Gf.Vec3f(*map(float, scale)))
    shape.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    prim = shape.GetPrim()
    UsdPhysics.CollisionAPI.Apply(prim)
    material = UsdShade.Material.Define(stage, path + '/PhysicsMaterial')
    physics_mat = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    physics_mat.CreateStaticFrictionAttr(friction)
    physics_mat.CreateDynamicFrictionAttr(friction)
    physics_mat.CreateRestitutionAttr(0.0)
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material, materialPurpose='physics')
    if dynamic:
        UsdPhysics.RigidBodyAPI.Apply(prim)
        UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
        api = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
        api.CreateSolverPositionIterationCountAttr(16)
        api.CreateSolverVelocityIterationCountAttr(4)
        api.CreateEnableCCDAttr(True)
    return prim


box('/World/Floor', [0, 0, -0.03], [6, 6, 0.06], [0.31, 0.32, 0.33])
box('/World/RobotPedestal', [0, 0, 0.35], [0.22, 0.22, 0.70], [0.22, 0.23, 0.24])
box('/World/ConveyorFrame', [0.05, -0.40, 0.65], [1.90, 0.38, 0.10], [0.38, 0.39, 0.40])
belt = box('/World/ConveyorBelt', [0.05, -0.40, 0.705], [1.85, 0.29, 0.03], [0.075, 0.080, 0.085])
# Surface velocity modifies contact friction; it does not edit the boxes' state.
UsdPhysics.RigidBodyAPI.Apply(belt).CreateKinematicEnabledAttr(True)
surface = PhysxSchema.PhysxSurfaceVelocityAPI.Apply(belt)
surface.CreateSurfaceVelocityEnabledAttr(True)
surface.CreateSurfaceVelocityLocalSpaceAttr(False)
surface.CreateSurfaceVelocityAttr(Gf.Vec3f(0, 0, 0))
for side, y in [('Front', -0.57), ('Back', -0.23)]:
    box('/World/Rail'+side, [0.05, y, 0.75], [1.92, 0.025, 0.07], [0.88, 0.63, 0.08])
for i, x in enumerate([-0.65, 0.75]):
    for j, y in enumerate([-0.53, -0.27]):
        box(f'/World/ConveyorLeg{i}{j}', [x, y, 0.30], [0.045, 0.045, 0.60], [0.24, 0.25, 0.26])

bins = {}
for color, x in [('red', 0.19), ('blue', 0.54)]:
    y, floor, outer, wall, rim = 0.39, 0.70, 0.28, 0.015, 0.14
    p = '/World/Bin_' + color
    box(p+'/Base', [x, y, floor-0.012], [outer, outer, 0.024], COLORS[color])
    for suffix, dx, dy, sx, sy in [('L', -outer/2, 0, wall, outer), ('R', outer/2, 0, wall, outer),
                                    ('F', 0, -outer/2, outer, wall), ('B', 0, outer/2, outer, wall)]:
        box(p+'/'+suffix, [x+dx, y+dy, floor+rim/2], [sx, sy, rim], COLORS[color])
    box(p+'/Stand', [x, y, 0.33], [0.08, 0.08, 0.66], [0.22, 0.23, 0.24])
    interior = outer/2-wall/2
    bins[color] = {'color': color, 'center': [x, y, floor],
                   'inner_lower': [x-interior, y-interior, floor],
                   'inner_upper': [x+interior, y+interior, floor+rim]}

robot = Franka(robot_path='/World/Franka', create_robot=True)
robot.set_world_poses(positions=[0, 0, 0.70], orientations=[1, 0, 0, 0])
objects = []
for i in range(args.objects):
    color = ['red', 'blue', 'red'][i]
    size = float(rng.uniform(0.044, 0.050))
    position = [float(0.00-i*0.30+rng.uniform(-0.02, 0.02)), float(-0.40+rng.uniform(-0.015, 0.015)), 0.72+size/2+0.004]
    path = f'/World/Parcel_{i}'
    box(path, position, [size]*3, COLORS[color], dynamic=True, mass=float(rng.uniform(0.035, 0.065)), friction=1.2)
    body = RigidPrim(path)
    objects.append({'id': f'parcel_{i}', 'color': color, 'size': size, 'body': body,
                    'initial_position': position, 'max_lift': 0., 'belt_displacement': 0.})

# Distinct landing slots prevent deliberately commanding two boxes to overlap.
for color in COLORS:
    same_color = [obj for obj in objects if obj['color'] == color]
    for slot, obj in enumerate(same_color):
        obj['placement'] = list(bins[color]['center'])
        if len(same_color) > 1:
            obj['placement'][0] += -0.06 if slot == 0 else 0.06

light = UsdLux.DomeLight.Define(stage, '/World/Light')
light.CreateIntensityAttr(1500)
sun = UsdLux.DistantLight.Define(stage, '/World/Sun')
sun.CreateIntensityAttr(1800)
sun.AddRotateXYZOp().Set(Gf.Vec3f(-30, -25, -20))
cam = UsdGeom.Camera.Define(stage, '/World/Camera')
cam.CreateFocalLengthAttr(32)
cam.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100))
look = Gf.Matrix4d().SetLookAt(Gf.Vec3d(1.75, -1.95, 2.15), Gf.Vec3d(0.12, -0.02, 0.64), Gf.Vec3d(0, 0, 1))
cam.AddTransformOp().Set(look.GetInverse())
product = rep.create.render_product('/World/Camera', (args.width, args.height))
rgb = rep.AnnotatorRegistry.get_annotator('rgb')
rgb.attach([product])

SimulationManager.setup_simulation(dt=DT, device='cpu')
SimulationManager.get_physics_scenes()[0].set_enabled_gpu_dynamics(False)
carb.settings.get_settings().set('/app/player/useFixedTimeStepping', True)
carb.settings.get_settings().set('/app/player/fixedTimeStep', DT)
app_utils.play()
app_utils.update_app(steps=30)
robot.reset_to_default_pose()
app_utils.update_app(steps=30)


def state_of(obj):
    pos, quat = obj['body'].get_world_poses()
    linear_values, angular_values = obj['body'].get_velocities()
    linear = linear_values.numpy()[0].tolist()
    angular = angular_values.numpy()[0].tolist()
    return {'position': pos.numpy()[0].tolist(), 'orientation': quat.numpy()[0].tolist(),
            'linear_velocity': linear, 'angular_velocity': angular}


manifest = {
    'schema_version': 1, 'task': 'conveyor_color_sort', 'seed': args.seed,
    'control': 'privileged-state scripted differential IK', 'grasp': 'parallel-jaw frictional contact only',
    'physics_dt': DT, 'renderer_gpu_requested': args.gpu,
    'versions': {'python': platform.python_version(), 'isaacsim': version('isaacsim'), 'torch': version('torch')},
    'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'git_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).parent, capture_output=True, text=True).stdout.strip(),
    'objects': [{k:v for k,v in obj.items() if k != 'body'} for obj in objects], 'bins': bins,
    'limitations': ['No visual perception or learned policy.', 'Conveyor pauses for picking.',
                    'No collision-aware global planning.', 'Procedural boxes, not a replica of the reference video.'],
}
manifest['source_files'] = source_files
manifest['installed_packages'] = sorted(
    [{'name': d.metadata['Name'], 'version': d.version} for d in distributions()],
    key=lambda item: item['name'].lower(),
)
(args.output/'manifest.json').write_text(json.dumps(manifest, indent=2))
stage.GetRootLayer().Export(str(args.output/'scene.usda'))
trajectory = (args.output/'trajectory.jsonl').open('w')
events = (args.output/'events.jsonl').open('w')
writer = None
if not args.no_video:
    import imageio.v2 as imageio
    writer = imageio.get_writer(str(args.output/'video.mp4'), fps=30, codec='libx264', quality=8, macro_block_size=2)

active, phase, phase_step = 0, 'feed', 0
pick = np.array([0.36, -0.40, 0.745])
command = np.array([0.36, -0.40, 1.10])
phase_start = command.copy()
closed = False
abort_reason = None
video_frames = 0
start = time.monotonic()
simulation_start = SimulationManager.get_simulation_time()
physics_step_start = SimulationManager.get_num_physics_steps()
DURATIONS = {'settle_belt': 45, 'hover': 120, 'descend': 100, 'close': 75,
             'lift': 100, 'transit': 120, 'above_bin': 120, 'lower': 100,
             'release': 60, 'retract': 90, 'final_settle': 180}
ORDER = ['settle_belt', 'hover', 'descend', 'close', 'lift', 'transit', 'above_bin', 'lower', 'release', 'retract']


def transition(new_phase, step, states):
    global phase, phase_step, phase_start
    phase, phase_step = new_phase, 0
    phase_start = robot.get_current_state()[1][0].copy()
    record = {'step': step, 'phase': phase, 'active_object': active, 'states': states}
    events.write(json.dumps(record)+'\n')
    events.flush()
    print(f'PHASE step={step} object={active} phase={phase}', flush=True)


try:
    for step in range(args.max_steps):
        states = [state_of(obj) for obj in objects]
        for obj, state in zip(objects, states):
            obj['max_lift'] = max(obj['max_lift'], state['position'][2]-obj['initial_position'][2])
        if phase not in ('final_settle', 'done'):
            obj, state = objects[active], states[active]
            dest = obj['placement']
        if phase == 'feed':
            closed = False
            command = np.array([0.36, -0.40, 1.10])
            surface.GetSurfaceVelocityAttr().Set(Gf.Vec3f(0.12, 0, 0))
            if state['position'][0] >= 0.35:
                surface.GetSurfaceVelocityAttr().Set(Gf.Vec3f(0, 0, 0))
                transition('settle_belt', step, states)
            elif phase_step > 900:
                abort_reason = 'conveyor_failed_to_deliver'
                break
        elif phase in ORDER:
            if phase == 'settle_belt':
                pick = np.array(state['position'])
                obj['belt_displacement'] = float(pick[0]-obj['initial_position'][0])
            targets = {
                'settle_belt': [pick[0], pick[1], 1.10],
                'hover': [pick[0], pick[1], pick[2]+0.28],
                'descend': [pick[0], pick[1], pick[2]+0.10],
                'close': [pick[0], pick[1], pick[2]+0.10],
                'lift': [pick[0], pick[1], 1.16],
                'transit': [0.48, 0.00, 1.16],
                'above_bin': [dest[0], dest[1], 1.16],
                'lower': [dest[0], dest[1], dest[2]+0.10+obj['size']/2+0.025],
                'release': [dest[0], dest[1], dest[2]+0.10+obj['size']/2+0.025],
                'retract': [dest[0], dest[1], 1.16],
            }
            closed = phase in ('close', 'lift', 'transit', 'above_bin', 'lower')
            t = min(1., phase_step/(DURATIONS[phase]*0.8))
            smooth = t*t*(3-2*t)
            command = phase_start*(1-smooth)+np.array(targets[phase])*smooth
            if phase_step >= DURATIONS[phase]:
                if phase == 'lift' and obj['max_lift'] < 0.08:
                    abort_reason = 'grasp_did_not_lift_object'
                    break
                if phase == 'retract':
                    active += 1
                    transition('feed' if active < len(objects) else 'final_settle', step, states)
                else:
                    transition(ORDER[ORDER.index(phase)+1], step, states)
        elif phase == 'final_settle':
            closed = False
            command = np.array([0.38, 0, 1.18])
            if phase_step >= DURATIONS[phase]:
                phase = 'done'
                break
        robot.set_end_effector_pose(command, [0., 1., 0., 0.])
        robot.close_gripper() if closed else robot.open_gripper()
        app.update()
        q, ee, orientation = robot.get_current_state()
        trajectory.write(json.dumps({'step': step, 'sim_time': SimulationManager.get_simulation_time()-simulation_start,
            'physics_steps': SimulationManager.get_num_physics_steps()-physics_step_start, 'phase': phase,
            'active_object': active, 'command': {'hand_target': command.tolist(), 'gripper_closed': closed},
            'joint_positions': q.tolist(), 'hand_position': ee.tolist(), 'hand_orientation': orientation.tolist(),
            'objects_before_step': states})+'\n')
        if step % 2 == 0:
            frame = np.asarray(rgb.get_data())
            if frame.ndim == 3 and frame.shape[0] == args.height:
                if writer:
                    writer.append_data(frame[..., :3])
                    video_frames += 1
                if step == 120:
                    import imageio.v2 as imageio
                    imageio.imwrite(args.output/'preview.png', frame[..., :3])
        phase_step += 1
    else:
        abort_reason = 'step_budget_exhausted'

    q, ee, _ = robot.get_current_state()
    results = []
    for obj in objects:
        state = state_of(obj)
        state.update({k:obj[k] for k in ('id', 'color', 'size', 'max_lift', 'belt_displacement')})
        state['released_and_retracted'] = bool(min(q[0][-2:]) > 0.03 and np.linalg.norm(np.array(state['position'])-ee[0]) > 0.15)
        results.append({'state': state, **verify_object(state, bins[obj['color']])})
    result = {'success': abort_reason is None and phase == 'done' and all(r['success'] for r in results),
              'seed': args.seed, 'phase': phase, 'abort_reason': abort_reason, 'steps': step+1,
              'wall_seconds': time.monotonic()-start, 'sim_seconds': SimulationManager.get_simulation_time()-simulation_start,
              'physics_steps': SimulationManager.get_num_physics_steps()-physics_step_start,
              'video_frames': video_frames, 'objects': results}
    (args.output/'result.json').write_text(json.dumps(result, indent=2))
    print('RESULT '+json.dumps(result), flush=True)
    frame = np.asarray(rgb.get_data())
    if frame.ndim == 3:
        import imageio.v2 as imageio
        imageio.imwrite(args.output/'final.png', frame[..., :3])
finally:
    trajectory.close()
    events.close()
    if writer:
        writer.close()
    app_utils.stop()
    app.close()

sys.exit(0 if result['success'] else 2)
