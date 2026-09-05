"""Small shared recorder for new demos; no task-success logic lives here."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path


class Run:
    def __init__(self, task, max_steps=8000, dt=1/60):
        parser = argparse.ArgumentParser()
        parser.add_argument('--seed', type=int, default=0)
        parser.add_argument('--gpu', type=int, default=7)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--no-video', action='store_true')
        parser.add_argument('--width', type=int, default=960)
        parser.add_argument('--height', type=int, default=720)
        parser.add_argument('--max-steps', type=int, default=max_steps)
        self.invocation = sys.argv[:]
        self.args, kit_args = parser.parse_known_args()
        sys.argv = [sys.argv[0]] + kit_args
        self.output, self.task, self.dt = self.args.output, task, dt
        self.output.mkdir(parents=True, exist_ok=False)
        root = Path(__file__).resolve().parents[1]
        self.sources = {}
        paths = sorted((root/'demos').glob('*.py')) + sorted((root/'scripts').glob('*task*.py'))
        for source in paths:
            name = str(source.relative_to(root))
            target = self.output/'source'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            self.sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        self.write('invocation.json', {'argv': self.invocation, 'source_files': self.sources})
        os.environ.setdefault('OMNI_KIT_ACCEPT_EULA', 'YES')
        from isaacsim import SimulationApp
        self.app = SimulationApp({
            'headless': True, 'active_gpu': self.args.gpu, 'physics_gpu': self.args.gpu,
            'multi_gpu': False, 'renderer': 'RaytracedLighting',
            'width': self.args.width, 'height': self.args.height, 'sync_loads': True,
            'shutdown_watchdog_timeout': 15.0,
            'extra_args': ['--/app/settings/persistent=false', '--/app/asyncRendering=false',
                           '--/rtx-transient/resourcemanager/texturestreaming/enabled=false'],
        })
        import numpy as np
        import warp as wp
        import isaacsim.core.experimental.utils.stage as stage_utils
        from pxr import UsdGeom
        wp.set_device('cpu')
        self.np, self.rng = np, np.random.default_rng(self.args.seed)
        self.stage = stage_utils.get_current_stage()
        UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(self.stage, 1.)
        self.stage.SetDefaultPrim(UsdGeom.Xform.Define(self.stage, '/World').GetPrim())
        self.robots, self.objects, self.step_count, self.video_frames = [], [], 0, 0
        self.writer, self.trajectory, self.events = None, None, None
        self.start_wall = time.monotonic()
        self.manifest = {'schema_version': 2, 'task': task, 'seed': self.args.seed,
            'physics_dt': dt, 'renderer_gpu_requested': self.args.gpu,
            'source_files': self.sources,
            'git_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True).stdout.strip(),
            'versions': {'python': platform.python_version(), 'isaacsim': version('isaacsim'), 'torch': version('torch')}}

    def write(self, filename, value):
        (self.output/filename).write_text(json.dumps(value, indent=2, ensure_ascii=False))

    def box(self, path, position, scale, color, dynamic=False, mass=.05, friction=.8):
        from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics, UsdShade
        shape = UsdGeom.Cube.Define(self.stage, path)
        shape.CreateSizeAttr(1.)
        shape.AddTranslateOp().Set(Gf.Vec3d(*map(float, position)))
        shape.AddScaleOp().Set(Gf.Vec3f(*map(float, scale)))
        shape.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        prim = shape.GetPrim()
        UsdPhysics.CollisionAPI.Apply(prim)
        material = UsdShade.Material.Define(self.stage, path+'/PhysicsMaterial')
        mat = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
        mat.CreateStaticFrictionAttr(friction)
        mat.CreateDynamicFrictionAttr(friction)
        mat.CreateRestitutionAttr(0.)
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material, materialPurpose='physics')
        if dynamic:
            UsdPhysics.RigidBodyAPI.Apply(prim)
            UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
            api = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
            api.CreateSolverPositionIterationCountAttr(16)
            api.CreateSolverVelocityIterationCountAttr(4)
            api.CreateEnableCCDAttr(True)
            api.CreateSleepThresholdAttr(0.)
        return prim

    def add_box(self, name, position, size, visual_color, mass=.05, **metadata):
        from isaacsim.core.experimental.prims import RigidPrim
        path = '/World/'+name
        self.box(path, position, [size]*3, visual_color, True, mass, 1.2)
        obj = {'id': name, 'size': size, 'mass': mass, 'initial_position': list(position),
               'body': RigidPrim(path), 'max_lift': 0., **metadata}
        self.objects.append(obj)
        return obj

    def franka(self, path='/World/Franka', position=(0, 0, .7), orientation=(1, 0, 0, 0)):
        import isaacsim.core.experimental.utils.app as app_utils
        app_utils.enable_extension('isaacsim.robot.experimental.manipulators.examples')
        from isaacsim.robot.experimental.manipulators.examples.franka import Franka
        robot = Franka(robot_path=path, create_robot=True)
        robot.set_world_poses(positions=list(position), orientations=list(orientation))
        self.robots.append(robot)
        return robot

    def camera(self, eye=(1.95, -2.10, 2.25), target=(.12, -.02, .82)):
        from pxr import Gf, UsdGeom, UsdLux
        import omni.replicator.core as rep
        UsdLux.DomeLight.Define(self.stage, '/World/Light').CreateIntensityAttr(1500)
        sun = UsdLux.DistantLight.Define(self.stage, '/World/Sun')
        sun.CreateIntensityAttr(1800)
        sun.AddRotateXYZOp().Set(Gf.Vec3f(-30, -25, -20))
        camera = UsdGeom.Camera.Define(self.stage, '/World/Camera')
        camera.CreateFocalLengthAttr(24)
        camera.CreateClippingRangeAttr(Gf.Vec2f(.01, 100))
        look = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1))
        camera.AddTransformOp().Set(look.GetInverse())
        self.product = rep.create.render_product('/World/Camera', (self.args.width, self.args.height))
        self.rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        self.rgb.attach([self.product])

    def start(self, metadata):
        import carb
        import isaacsim.core.experimental.utils.app as app_utils
        from isaacsim.core.simulation_manager import SimulationManager
        self.manager = SimulationManager
        SimulationManager.setup_simulation(dt=self.dt, device='cpu')
        SimulationManager.get_physics_scenes()[0].set_enabled_gpu_dynamics(False)
        carb.settings.get_settings().set('/app/player/useFixedTimeStepping', True)
        carb.settings.get_settings().set('/app/player/fixedTimeStep', self.dt)
        app_utils.play()
        app_utils.update_app(steps=30)
        for robot in self.robots:
            robot.reset_to_default_pose()
        app_utils.update_app(steps=30)
        self.sim_start = SimulationManager.get_simulation_time()
        self.physics_start = SimulationManager.get_num_physics_steps()
        self.start_wall = time.monotonic()
        self.manifest.update(metadata)
        self.manifest['objects'] = [{k: v for k, v in o.items() if k != 'body'} for o in self.objects]
        self.write('manifest.json', self.manifest)
        self.stage.GetRootLayer().Export(str(self.output/'scene.usda'))
        self.trajectory = (self.output/'trajectory.jsonl').open('w')
        self.events = (self.output/'events.jsonl').open('w')
        if not self.args.no_video:
            import imageio.v2 as imageio
            self.writer = imageio.get_writer(str(self.output/'video.mp4'), fps=30, codec='libx264', quality=8, macro_block_size=2)

    def state(self, obj):
        pos, quat = obj['body'].get_world_poses()
        linear, angular = obj['body'].get_velocities()
        state = {'id': obj['id'], 'position': pos.numpy()[0].tolist(), 'orientation': quat.numpy()[0].tolist(),
                 'linear_velocity': linear.numpy()[0].tolist(), 'angular_velocity': angular.numpy()[0].tolist()}
        obj['max_lift'] = max(obj['max_lift'], state['position'][2]-obj['initial_position'][2])
        return state

    def observe(self):
        return [self.state(obj) for obj in self.objects]

    def event(self, kind, **fields):
        event = {'step': self.step_count, 'kind': kind, **fields}
        self.events.write(json.dumps(event)+'\n')
        self.events.flush()
        print('EVENT '+json.dumps(event), flush=True)

    def step(self, phase, commands, states_before):
        self.app.update()
        robot_states = []
        for robot in self.robots:
            q, ee, orientation = robot.get_current_state()
            robot_states.append({'joints': q.tolist(), 'hand_position': ee.tolist(), 'hand_orientation': orientation.tolist()})
        record = {'step': self.step_count, 'phase': phase,
            'physics_steps': self.manager.get_num_physics_steps()-self.physics_start,
            'sim_time': self.manager.get_simulation_time()-self.sim_start,
            'commands': commands, 'robots': robot_states,
            'objects_before_step': states_before, 'objects_after_step': self.observe()}
        self.trajectory.write(json.dumps(record)+'\n')
        if self.step_count % 2 == 0:
            frame = self.np.asarray(self.rgb.get_data())
            if frame.ndim == 3:
                if self.writer:
                    self.writer.append_data(frame[..., :3])
                    self.video_frames += 1
                if self.step_count == 120:
                    import imageio.v2 as imageio
                    imageio.imwrite(self.output/'preview.png', frame[..., :3])
        self.step_count += 1

    def finish(self, result):
        result.update({'task': self.task, 'seed': self.args.seed, 'physics_steps': self.step_count,
                       'sim_seconds': self.manager.get_simulation_time()-self.sim_start,
                       'wall_seconds': time.monotonic()-self.start_wall, 'video_frames': self.video_frames})
        self.write('result.json', result)
        frame = self.np.asarray(self.rgb.get_data())
        if frame.ndim == 3:
            import imageio.v2 as imageio
            imageio.imwrite(self.output/'final.png', frame[..., :3])
        print('RESULT '+json.dumps(result), flush=True)
        self.close(0 if result['success'] else 2)

    def close(self, code=1):
        for handle in (self.trajectory, self.events, self.writer):
            if handle:
                handle.close()
        self.app.close(wait_for_replicator=False, skip_cleanup=True, exit_code=code)
        raise SystemExit(code)
