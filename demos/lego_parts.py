"""Enlarged stud/socket bricks, plus an explicitly declared part-to-part latch."""
from gear_verify import multiply_quaternions


def conjugate(q):
    return [q[0], -q[1], -q[2], -q[3]]


def rotate(q, p):
    return multiply_quaternions(multiply_quaternions(q, [0.]+list(p)), conjugate(q))[1:]


def relative_pose(lower, upper):
    delta = [a-b for a, b in zip(upper['position'], lower['position'])]
    return rotate(conjugate(lower['orientation']), delta), multiply_quaternions(
        conjugate(lower['orientation']), upper['orientation'])


def brick(run, name, position, mass, upper=False):
    from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics
    from isaacsim.core.experimental.prims import RigidPrim
    from assembly_parts import cylinder, ring
    path = '/World/'+name
    root = UsdGeom.Xform.Define(run.stage, path)
    root.AddTranslateOp().Set(Gf.Vec3d(*position))
    color = [.29, .56, .65] if upper else [.78, .56, .24]
    if upper:
        run.box(path+'/Roof', [0, 0, .008], [.064, .064, .024], color, friction=1.2)
        for i, x in enumerate([-.029, .029]):
            run.box(path+f'/WallX{i}', [x, 0, -.012], [.006, .064, .016], color, friction=1.2)
        for i, y in enumerate([-.029, .029]):
            run.box(path+f'/WallY{i}', [0, y, -.012], [.052, .006, .016], color, friction=1.2)
        for i, x in enumerate([-.014, .014]):
            for j, y in enumerate([-.014, .014]):
                socket = UsdGeom.Xform.Define(run.stage, path+f'/Socket{i}{j}')
                socket.AddTranslateOp().Set(Gf.Vec3d(x, y, 0))
                ring(run, str(socket.GetPath()), .012, .010, .016, -.012, color, segments=20)
    else:
        run.box(path+'/Core', [0, 0, 0], [.128, .050, .040], color, friction=1.2)
    for i, x in enumerate([-.014, .014] if upper else [-.042, -.014, .014, .042]):
        for j, y in enumerate([-.014, .014]):
            cylinder(run, path+f'/Stud{i}{j}', [x, y, .026], .0075, .012, color)
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(mass)
    api = PhysxSchema.PhysxRigidBodyAPI.Apply(root.GetPrim())
    api.CreateSolverPositionIterationCountAttr(64)
    api.CreateSolverVelocityIterationCountAttr(0)
    api.CreateEnableCCDAttr(True)
    api.CreateSleepThresholdAttr(0.)
    PhysxSchema.PhysxContactReportAPI.Apply(root.GetPrim()).CreateThresholdAttr(0.)
    obj = {'id': name, 'role': 'upper' if upper else 'lower', 'mass': mass,
           'initial_position': position, 'max_lift': 0., 'body': RigidPrim(path)}
    run.objects.append(obj)
    return obj


def latch(run, lower, upper):
    from pxr import Gf, UsdPhysics
    p, q = relative_pose(lower, upper)
    joint = UsdPhysics.FixedJoint.Define(run.stage, '/World/BrickSnap')
    joint.CreateBody0Rel().SetTargets(['/World/LowerBrick'])
    joint.CreateBody1Rel().SetTargets(['/World/UpperBrick'])
    joint.CreateLocalPos0Attr(Gf.Vec3f(*map(float, p)))
    joint.CreateLocalPos1Attr(Gf.Vec3f(0))
    joint.CreateLocalRot0Attr(Gf.Quatf(float(q[0]), Gf.Vec3f(*map(float, q[1:]))))
    joint.CreateLocalRot1Attr(Gf.Quatf(1.))
    joint.CreateBreakForceAttr(6.)
    joint.CreateBreakTorqueAttr(.25)
    joint.CreateExcludeFromArticulationAttr(True)
    joint.CreateCollisionEnabledAttr(True)
    run.stage.GetRootLayer().Export(str(run.output/'scene-with-snap.usda'))
    return {'position': [float(x) for x in p], 'orientation': [float(x) for x in q]}
