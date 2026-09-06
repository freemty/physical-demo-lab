"""IR-to-USD adapter. Dynamic objects are authored only before play."""
import hashlib
import gzip
import json
import math
import re
import shutil
from pathlib import Path

from castle_runtime import Run


class CastleRun(Run):
    def __init__(self, mode, ir, solver='TGS', velocity_iterations=4, **kwargs):
        super().__init__('block_castle', dt=1/240, **kwargs)
        self.mode, self.ir_path = mode, ir
        self.solver, self.velocity_iterations = solver, velocity_iterations
        self.spec = json.loads(ir.read_text())
        shutil.copy2(ir, self.output/'source-ir.json')
        self.spec_hash = hashlib.sha256(ir.read_bytes()).hexdigest()
        self.contact_records, self.contact_handle = [], None
        self.physics_handle, self.physics_ticks = None, 0
        self.physics_oracle = None
        self.max_penetration, self.arm_contact_samples = 0., 0

    def build(self):
        from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics
        from isaacsim.core.experimental.prims import RigidPrim
        from isaacsim.core.rendering_manager import RenderingManager
        scene = UsdPhysics.Scene.Define(self.stage, '/World/CastlePhysics')
        api = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
        api.CreateSolverTypeAttr(self.solver)
        api.CreateMinPositionIterationCountAttr(32)
        api.CreateMinVelocityIterationCountAttr(self.velocity_iterations)
        api.CreateMaxVelocityIterationCountAttr(self.velocity_iterations)
        self.box('/World/Floor', [0, 0, -.03], [4, 4, .06], [.36]*3)
        self.box('/World/Table', [0, 0, .775], self.spec['table']['size'], [.42, .38, .32])
        robot = self.franka(position=(-.44, 0, .8))
        self.robot = robot
        for i, (x, y) in enumerate([(-.6,-.48),(-.6,.48),(.6,-.48),(.6,.48)]):
            self.box(f'/World/Leg{i}', [x,y,.375], [.045,.045,.75], [.28]*3)
        for src in self.spec['objects']:
            name, dynamic = src['name'], src.get('free', False)
            position = list(src['target_pos'] if dynamic and self.mode == 'goal' else src['pos'])
            yaw = 0.
            if dynamic and self.mode != 'goal':
                position[:2] = (self.np.array(position[:2])+self.rng.uniform(-.003,.003,2)).tolist()
                yaw = float(self.rng.uniform(-.025,.025))
            path = '/World/'+name
            root = UsdGeom.Xform.Define(self.stage, path)
            root.AddTranslateOp().Set(Gf.Vec3d(*position))
            root.AddOrientOp().Set(Gf.Quatf(math.cos(yaw/2), 0, 0, math.sin(yaw/2)))
            mass = 0.
            for index, geom in enumerate(src['geoms']):
                child_path = path+'/'+re.sub('[^a-zA-Z0-9_]', '_', geom.get('name',str(index)))
                size = geom['size']
                if geom['shape'] == 'box':
                    shape = UsdGeom.Cube.Define(self.stage, child_path)
                    shape.CreateSizeAttr(1.)
                    shape.AddScaleOp().Set(Gf.Vec3f(*(2*v for v in size)))
                elif geom['shape'] == 'cylinder':
                    shape = UsdGeom.Cylinder.Define(self.stage, child_path)
                    shape.CreateRadiusAttr(size[0])
                    shape.CreateHeightAttr(2*size[1])
                else:
                    raise ValueError('Unsupported castle geometry: '+geom['shape'])
                shape.AddTranslateOp().Set(Gf.Vec3d(*geom.get('pos',[0,0,0])))
                if 'quat' in geom:
                    shape.AddOrientOp().Set(Gf.Quatf(*geom['quat']))
                shape.CreateDisplayColorAttr([Gf.Vec3f(*geom['rgba'][:3])])
                # Translate before local scale; translation must remain in meters.
                ops = shape.GetOrderedXformOps()
                shape.SetXformOpOrder(sorted(ops, key=lambda op: 2 if op.GetOpType()==UsdGeom.XformOp.TypeScale else 0))
                if geom.get('collision', True):
                    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
                    mass += geom.get('mass',0.)
            if dynamic:
                prim = root.GetPrim()
                UsdPhysics.RigidBodyAPI.Apply(prim)
                UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
                rb = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
                rb.CreateSolverPositionIterationCountAttr(32)
                rb.CreateSolverVelocityIterationCountAttr(self.velocity_iterations)
                rb.CreateEnableCCDAttr(True)
                rb.CreateSleepThresholdAttr(0.)
                self.objects.append({'id': name, 'initial_position': position, 'dimensions': src['full_size'],
                    'mass': mass, 'max_lift': 0., 'body': RigidPrim(path), 'target': src['target_pos'],
                    'supports': src['supports'], 'grasp_offset_z': src['grasp_offset_z']})
        from pxr import UsdShade
        mat = UsdShade.Material.Define(self.stage, '/World/CastleMaterial')
        material = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
        material.CreateStaticFrictionAttr(.9)
        material.CreateDynamicFrictionAttr(.9)
        material.CreateRestitutionAttr(0.)
        for prim in self.stage.Traverse():
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                collision = PhysxSchema.PhysxCollisionAPI.Apply(prim)
                collision.CreateContactOffsetAttr(.001)
                collision.CreateRestOffsetAttr(0.)
                UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, materialPurpose='physics')
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                PhysxSchema.PhysxContactReportAPI.Apply(prim).CreateThresholdAttr(0.)
        self.sensor_names = [o['id'] for o in self.objects]
        # A static Xform is not a PhysX actor; its collider child is the actor.
        self.filter_paths = ['/World/foundation/foundation_solid','/World/Table']+['/World/'+n for n in self.sensor_names]+robot.link_paths[0]
        self.filter_names = ['foundation','Table']+self.sensor_names+['robot:'+p.rsplit('/',1)[-1] for p in robot.link_paths[0]]
        self.contacts = RigidPrim(['/World/'+n for n in self.sensor_names],
                                  contact_filter_paths=self.filter_paths, max_contact_count=8192)
        RenderingManager.set_dt(1/60)
        self.camera(eye=(-1.30,-1.50,1.85), target=(.05,0,.86))
        from pxr import UsdLux
        UsdLux.DomeLight(self.stage.GetPrimAtPath('/World/Light')).GetIntensityAttr().Set(350.)
        UsdLux.DistantLight(self.stage.GetPrimAtPath('/World/Sun')).GetIntensityAttr().Set(700.)
        self.stage.GetRootLayer().Export(str(self.output/'initial-authored.usda'))

    def start_castle(self):
        self.start({'mode': self.mode, 'ir_sha256': self.spec_hash,
                    'spec': self.spec, 'control_dt': 1/60, 'video_fps': 30,
                    'physics_solver':self.solver, 'velocity_iterations':self.velocity_iterations,
                    'contact_sensor_names': self.sensor_names, 'contact_filter_names': self.filter_names,
                    'scope': 'Isaac Sim native contact-driven assembly; privileged-state scripted controller',
                    'initialization_only_state_edits': True,
                    'limitations': ['No learned or visual policy', 'No cross-engine state-equivalence claim']})
        self.contact_handle = (self.output/'contacts.jsonl').open('w')
        self.physics_handle = gzip.open(self.output/'physics-steps.jsonl.gz','wt',compresslevel=3)
        from castle_verify import StableOracle
        self.physics_oracle = StableOracle(self.spec)
        self.read_contacts()
        self.write('robot-inspection.json', {'links':self.robot.link_paths, 'dofs':self.robot.dof_names,
                                            'state':[v.tolist() for v in self.robot.get_current_state()]})

    def read_contacts(self):
        forces, points, normals, distances, counts, starts = [v.numpy().copy() for v in self.contacts.get_contact_force_data(dt=self.dt)]
        records = []
        for i,j in self.np.argwhere(counts > 0):
            a, count = int(starts[i,j]), int(counts[i,j])
            subset = distances[a:a+count].reshape(-1)
            minimum = float(subset.min())
            records.append({'body':self.sensor_names[i], 'other':self.filter_names[j], 'min_distance':minimum,
                            'normal_force':float(forces[a:a+count].sum()), 'count':count,
                            'points':points[a:a+count].tolist(), 'normals':normals[a:a+count].tolist(),
                            'distances':subset.tolist()})
            self.max_penetration = max(self.max_penetration, -minimum)
            if self.filter_names[j].startswith('robot:') and 'finger' not in self.filter_names[j] and minimum <= 0:
                self.arm_contact_samples += 1
        self.contact_records = records
        return records

    def observe(self):
        positions, quaternions = [v.numpy() for v in self.contacts.get_world_poses()]
        linear, angular = [v.numpy() for v in self.contacts.get_velocities()]
        states = []
        for i,obj in enumerate(self.objects):
            obj['max_lift'] = max(obj['max_lift'],float(positions[i,2])-obj['initial_position'][2])
            states.append({'id':obj['id'],'position':positions[i].tolist(),'orientation':quaternions[i].tolist(),
                           'linear_velocity':linear[i].tolist(),'angular_velocity':angular[i].tolist()})
        return states

    def physics_tick(self, *_):
        contacts = self.read_contacts()
        states = self.observe()
        now = self.manager.get_simulation_time()-self.sim_start
        self.physics_verification = self.physics_oracle.update(now,states,contacts)
        self.physics_handle.write(json.dumps({'physics_step':self.physics_ticks,'sim_time':now,
            'objects':states,'contacts':contacts},separators=(',',':'))+'\n')
        self.physics_ticks += 1

    def step(self, phase, commands, states_before):
        # Fail serialization before advancing physics, so malformed commands
        # cannot produce an unrecorded physical action.
        json.dumps(commands)
        # Four native physics steps per control tick. Rendering does not advance physics.
        from isaacsim.core.rendering_manager import RenderingManager
        self.manager.step(steps=4, callback=self.physics_tick)
        if self.step_count % 2 == 0 and (self.writer or self.step_count % 120 == 0):
            RenderingManager.render()
            frame = self.np.asarray(self.rgb.get_data())
            if frame.ndim == 3:
                if self.writer:
                    self.writer.append_data(frame[...,:3])
                    self.video_frames += 1
                if self.step_count % 120 == 0:
                    import imageio.v2 as imageio
                    imageio.imwrite(self.output/'preview.png',frame[...,:3])
        robot_states = []
        for robot in self.robots:
            q,ee,orientation = robot.get_current_state()
            robot_states.append({'joints':q.tolist(),'hand_position':ee.tolist(),'hand_orientation':orientation.tolist()})
        record = {'step':self.step_count,'phase':phase,
            'physics_steps':self.manager.get_num_physics_steps()-self.physics_start,
            'sim_time':self.manager.get_simulation_time()-self.sim_start,
            'commands':commands,'robots':robot_states,'objects_before_step':states_before,'objects_after_step':self.observe()}
        self.trajectory.write(json.dumps(record)+'\n')
        contacts = self.contact_records
        self.contact_handle.write(json.dumps({'step':self.step_count,
            'sim_time':self.manager.get_simulation_time()-self.sim_start, 'contacts':contacts})+'\n')
        self.step_count += 1
        if self.step_count % 120 == 0:
            self.contact_handle.flush()
            self.trajectory.flush()

    def close(self, code=1):
        if self.physics_handle:
            self.physics_handle.close()
        if self.contact_handle:
            self.contact_handle.close()
        super().close(code)
