"""Rigid service cart: two driven wheels and two freely rolling ball casters."""
import math


class ServiceCart:
    RADIUS, TRACK = .07, .28

    def __init__(self, run, position):
        import numpy as np
        from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics, UsdShade
        from isaacsim.core.experimental.prims import RigidPrim
        self.np, self.drives, self.wheels = np, [], []
        self.path = '/World/ServiceCart'
        root = UsdGeom.Xform.Define(run.stage, self.path)
        root.AddTranslateOp().Set(Gf.Vec3d(*position))
        run.box(self.path+'/Chassis', [0, 0, 0], [.32, .22, .08], [.30]*3)
        run.box(self.path+'/Column', [0, 0, .32], [.055, .055, .58], [.55]*3)
        run.box(self.path+'/Tray', [0, 0, .628], [.34, .25, .024], [.77]*3, friction=1.2)
        for i, y in enumerate([-.12, .12]):
            run.box(self.path+f'/RimY{i}', [0, y, .66], [.34, .01, .04], [.58]*3)
        for i, x in enumerate([-.165, .165]):
            run.box(self.path+f'/RimX{i}', [x, 0, .66], [.01, .23, .04], [.58]*3)

        def dynamic(prim, mass):
            UsdPhysics.RigidBodyAPI.Apply(prim)
            UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
            api = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
            api.CreateSolverPositionIterationCountAttr(32)
            api.CreateSolverVelocityIterationCountAttr(4)
            api.CreateEnableCCDAttr(True)
            api.CreateSleepThresholdAttr(0.)
        dynamic(root.GetPrim(), 8.)
        mass = UsdPhysics.MassAPI(root.GetPrim())
        mass.CreateCenterOfMassAttr(Gf.Vec3f(0, 0, .015))
        mass.CreateDiagonalInertiaAttr(Gf.Vec3f(.16, .18, .15))
        self.body = RigidPrim(self.path)
        self.object = {'id': 'service_cart', 'role': 'carrier', 'body': self.body,
                       'initial_position': position, 'mass': 8., 'max_lift': 0.,
                       'tray_floor_local_z': .640, 'tray_inner_half_size': [.16, .115]}
        run.objects.append(self.object)

        def material(prim, path, friction):
            m = UsdShade.Material.Define(run.stage, path+'/Material')
            api = UsdPhysics.MaterialAPI.Apply(m.GetPrim())
            api.CreateStaticFrictionAttr(friction)
            api.CreateDynamicFrictionAttr(friction)
            api.CreateRestitutionAttr(0.)
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(m, materialPurpose='physics')

        for i, y in enumerate([self.TRACK/2, -self.TRACK/2]):
            path = '/World/CartWheel'+str(i)
            wheel = UsdGeom.Cylinder.Define(run.stage, path)
            wheel.CreateAxisAttr('Y')
            wheel.CreateRadiusAttr(self.RADIUS)
            wheel.CreateHeightAttr(.035)
            wheel.AddTranslateOp().Set(Gf.Vec3d(position[0], position[1]+y, position[2]-.06))
            wheel.CreateDisplayColorAttr([Gf.Vec3f(.12, .12, .12)])
            UsdPhysics.CollisionAPI.Apply(wheel.GetPrim())
            dynamic(wheel.GetPrim(), .25)
            material(wheel.GetPrim(), path, 1.0)
            joint = UsdPhysics.RevoluteJoint.Define(run.stage, '/World/WheelJoint'+str(i))
            joint.CreateBody0Rel().SetTargets([self.path])
            joint.CreateBody1Rel().SetTargets([path])
            joint.CreateLocalPos0Attr(Gf.Vec3f(0, y, -.06))
            joint.CreateLocalPos1Attr(Gf.Vec3f(0))
            joint.CreateAxisAttr('Y')
            drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), 'angular')
            drive.CreateTypeAttr('force')
            drive.CreateStiffnessAttr(0.)
            drive.CreateDampingAttr(5.)
            drive.CreateMaxForceAttr(4.)
            drive.CreateTargetVelocityAttr(0.)
            self.drives.append(drive)
            self.wheels.append(RigidPrim(path))
        for i, x in enumerate([-.13, .13]):
            path = '/World/CartCaster'+str(i)
            caster = UsdGeom.Sphere.Define(run.stage, path)
            caster.CreateRadiusAttr(.025)
            caster.AddTranslateOp().Set(Gf.Vec3d(position[0]+x, position[1], position[2]-.105))
            caster.CreateDisplayColorAttr([Gf.Vec3f(.2, .2, .2)])
            UsdPhysics.CollisionAPI.Apply(caster.GetPrim())
            dynamic(caster.GetPrim(), .05)
            material(caster.GetPrim(), path, .4)
            joint = UsdPhysics.SphericalJoint.Define(run.stage, '/World/CasterJoint'+str(i))
            joint.CreateBody0Rel().SetTargets([self.path])
            joint.CreateBody1Rel().SetTargets([path])
            joint.CreateLocalPos0Attr(Gf.Vec3f(x, 0, -.105))
            joint.CreateLocalPos1Attr(Gf.Vec3f(0))
        run.robots.append(self)

    def reset_to_default_pose(self):
        pass  # The dynamic chassis has an authored initial state, never teleported.

    def get_current_state(self):
        from gear_verify import multiply_quaternions
        position, orientation = self.body.get_world_poses()
        q = orientation.numpy()[0].tolist()
        inv = [q[0], -q[1], -q[2], -q[3]]
        angles = []
        for wheel in self.wheels:
            relative = multiply_quaternions(inv, wheel.get_world_poses()[1].numpy()[0].tolist())
            angles.append(2*math.atan2(relative[2], relative[0]))
        return self.np.array([angles]), position.numpy(), orientation.numpy()

    def drive(self, linear, angular):
        speeds = [(linear-angular*self.TRACK/2)/self.RADIUS,
                  (linear+angular*self.TRACK/2)/self.RADIUS]
        for drive, speed in zip(self.drives, speeds):
            drive.GetTargetVelocityAttr().Set(math.degrees(speed))
        return speeds
