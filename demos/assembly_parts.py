"""Procedural compound colliders with explicit holes; units are meters."""
import math


def rotated_box(run, path, position, scale, color, yaw, friction=.8):
    from pxr import UsdGeom
    prim = run.box(path, position, scale, color, friction=friction)
    xform = UsdGeom.Xformable(prim)
    translate, scaling = xform.GetOrderedXformOps()
    rotation = xform.AddRotateZOp()
    rotation.Set(math.degrees(yaw))
    # Rotate the sized box in its parent frame, not the unit cube before scaling.
    xform.SetXformOpOrder([translate, rotation, scaling])
    return prim


def ring(run, path, outer, inner, height, z, color, segments=32):
    radius = (outer+inner)/2
    tangential = 2*radius*math.tan(math.pi/segments)*1.02
    for i in range(segments):
        angle = 2*math.pi*i/segments
        rotated_box(run, f'{path}/Section_{i}', [radius*math.cos(angle), radius*math.sin(angle), z],
                    [outer-inner, tangential, height], color, angle, friction=1.0)


def gear(run, name, position, dynamic=True, mass=.06, yaw=0., color=(.55, .60, .63)):
    from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics
    path = '/World/'+name
    root = UsdGeom.Xform.Define(run.stage, path)
    root.AddTranslateOp().Set(Gf.Vec3d(*position))
    root.AddOrientOp().Set(Gf.Quatf(math.cos(yaw/2), Gf.Vec3f(0, 0, math.sin(yaw/2))))
    ring(run, path+'/Web', .037, .009, .020, 0., color)
    ring(run, path+'/Hub', .019, .009, .040, .030, color)
    for i in range(20):
        angle = i*2*math.pi/20
        rotated_box(run, f'{path}/Tooth_{i}', [.040*math.cos(angle), .040*math.sin(angle), 0.],
                    [.007, .005, .020], color, angle)
    if dynamic:
        UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
        UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(mass)
        api = PhysxSchema.PhysxRigidBodyAPI.Apply(root.GetPrim())
        api.CreateSolverPositionIterationCountAttr(32)
        api.CreateSolverVelocityIterationCountAttr(8)
        api.CreateEnableCCDAttr(True)
        api.CreateSleepThresholdAttr(0.)
    return root.GetPrim()


def cylinder(run, path, position, radius, height, color):
    from pxr import Gf, UsdGeom, UsdPhysics
    shape = UsdGeom.Cylinder.Define(run.stage, path)
    shape.CreateRadiusAttr(radius)
    shape.CreateHeightAttr(height)
    shape.CreateAxisAttr('Z')
    shape.AddTranslateOp().Set(Gf.Vec3d(*position))
    shape.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
    return shape.GetPrim()
