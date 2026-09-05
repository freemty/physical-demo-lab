"""Allegro contact-driven cap with a declared reduced-order helical fixture.

Development implementation: not complete until independent auditing passes.
"""
import math
import json
import os
import traceback
from sim_runtime import Run

run = Run('bottle_cap', max_steps=3600, dt=1/120)
try:
    import numpy as np
    from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics
    from isaacsim.core.experimental.prims import Articulation, RigidPrim
    from isaacsim.core.experimental.utils.stage import add_reference_to_stage
    from isaacsim.storage.native import get_assets_root_path
    from assembly_parts import ring, cylinder

    cx, cy, z0 = -.064, .068, 1.010
    pitch, release_angle, mass = .012, math.pi, float(run.rng.uniform(.038, .042))
    stiffness, damping, rotary_drag = 1000., 2., .002
    negative = os.environ.get('BOTTLE_NO_CLOSE') == '1'
    run.box('/World/Floor', [0, 0, -.03], [3, 3, .06], [.3]*3)
    run.box('/World/Table', [0, 0, .76], [.8, .8, .08], [.4]*3)
    cylinder(run, '/World/Bottle', [cx, cy, .89], .04, .18, [.32, .48, .48])
    cylinder(run, '/World/Neck', [cx, cy, .998], .021, .056, [.40, .58, .57])
    run.box('/World/Fixture', [cx, cy, .813], [.105, .105, .026], [.2]*3)
    root = UsdGeom.Xform.Define(run.stage, '/World/Cap')
    root.AddTranslateOp().Set(Gf.Vec3d(cx, cy, z0))
    ring(run, '/World/Cap/Wall', .036, .025, .05, 0., [.73, .39, .15])
    cylinder(run, '/World/Cap/Top', [0, 0, .027], .036, .004, [.8, .45, .19])
    run.box('/World/Cap/Marker', [.02, 0, .03], [.02, .006, .003], [.05]*3)
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(mass)
    rb = PhysxSchema.PhysxRigidBodyAPI.Apply(root.GetPrim())
    rb.CreateSolverPositionIterationCountAttr(32)
    rb.CreateSolverVelocityIterationCountAttr(8)
    rb.CreateSleepThresholdAttr(0.)
    cap = RigidPrim('/World/Cap')
    obj = {'id': 'Cap', 'body': cap, 'initial_position': [cx, cy, z0], 'mass': mass, 'max_lift': 0.}
    run.objects.append(obj)

    def axial_joint(path, body, world_position, local_position, local_rotation):
        joint = UsdPhysics.Joint.Define(run.stage, path)
        joint.CreateBody1Rel().SetTargets([body])
        joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*world_position))
        joint.CreateLocalPos1Attr().Set(Gf.Vec3f(*local_position))
        joint.CreateLocalRot0Attr().Set(Gf.Quatf(math.sqrt(.5), 0, -math.sqrt(.5), 0))
        joint.CreateLocalRot1Attr().Set(Gf.Quatf(*local_rotation))
        joint.CreateExcludeFromArticulationAttr().Set(True)
        # D6's twist X is aligned with world Z; swing axes cannot represent
        # an unrestricted full turn. Local frame X is also the lift axis.
        for axis in ('transY', 'transZ', 'rotY', 'rotZ'):
            limit = UsdPhysics.LimitAPI.Apply(joint.GetPrim(), axis)
            limit.CreateLowAttr(1.)
            limit.CreateHighAttr(-1.)
        return joint

    thread = axial_joint('/World/ThreadGuide', '/World/Cap', [cx, cy, z0], [0, 0, 0], [math.sqrt(.5), 0, -math.sqrt(.5), 0])
    # Limits only prevent tightening beyond the initial seat; the free Z and
    # yaw coordinates are passively coupled by equal/opposite spring work.
    lim = UsdPhysics.LimitAPI.Apply(thread.GetPrim(), 'rotX')
    lim.CreateLowAttr(-2.)
    lim.CreateHighAttr(360.)

    path = '/World/Allegro'
    asset = get_assets_root_path()+'/Isaac/Robots/WonikRobotics/AllegroHand/allegro_hand.usd'
    add_reference_to_stage(usd_path=asset, path=path)
    placement = UsdGeom.Xformable(run.stage.GetPrimAtPath(path))
    placement.ClearXformOpOrder()
    placement.AddTranslateOp(opSuffix='fixture').Set(Gf.Vec3d(0, 0, 1.15))
    placement.AddOrientOp(opSuffix='fixture').Set(Gf.Quatf(0, 1, 0, 0))
    run.stage.GetPrimAtPath(path+'/root_joint').SetActive(False)
    hand = Articulation(path)
    # Removing the fixed root makes palm_link the articulation root. The named
    # mounting link remains valid, but link_paths[0][0] no longer names it.
    mount_path = path+'/allegro_mount'
    mount = axial_joint('/World/WristFixture', mount_path, [cx, cy, 1.15], [cx, -cy, 0], [0, -math.sqrt(.5), 0, math.sqrt(.5)])
    spin = UsdPhysics.DriveAPI.Apply(mount.GetPrim(), 'rotX')
    spin.CreateTypeAttr('force')
    spin.CreateStiffnessAttr(0.)
    spin.CreateDampingAttr(6.)
    spin.CreateMaxForceAttr(2.)
    height = UsdPhysics.DriveAPI.Apply(mount.GetPrim(), 'transX')
    height.CreateTypeAttr('force')
    height.CreateStiffnessAttr(800.)
    height.CreateDampingAttr(60.)
    height.CreateMaxForceAttr(80.)
    for prim in run.stage.Traverse():
        if str(prim.GetPath()).startswith(path) and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateDisableGravityAttr(True)
    q_open = np.zeros(hand.num_dofs, dtype=np.float32)
    q_closed = np.zeros(hand.num_dofs, dtype=np.float32)
    for i, name in enumerate(hand.dof_names):
        q_closed[i] = .9 if not name.endswith('_0') else 0.
        if name == 'thumb_joint_0':
            q_open[i], q_closed[i] = .28, 1.1
    hand.set_default_state(dof_positions=q_open)
    hand.set_dof_gains(stiffnesses=3., dampings=.1)
    hand.set_dof_max_efforts(.5)
    palm = RigidPrim(mount_path)
    contact_links = [p for p in hand.link_paths[0] if any(f+'_' in p for f in ('index', 'middle', 'ring', 'thumb'))]
    for link in contact_links+['/World/Cap']:
        PhysxSchema.PhysxContactReportAPI.Apply(run.stage.GetPrimAtPath(link)).CreateThresholdAttr(0.)
    contact = RigidPrim(contact_links, contact_filter_paths=['/World/Cap'])
    run.write('hand-mount.json', {'link_paths': hand.link_paths, 'mount_path': mount_path,
                                'initial_mount': [v.numpy().tolist() for v in palm.get_world_poses()]})

    class Adapter:
        def reset_to_default_pose(self):
            hand.reset_to_default_state()

        def get_current_state(self):
            p, q = palm.get_world_poses()
            return hand.get_dof_positions().numpy(), p.numpy(), q.numpy()

    run.robots.append(Adapter())
    run.camera(eye=(-.65, .8, 1.5), target=(cx, cy, 1.10))
    run.start({'asset': asset, 'scope': 'contact-driven Allegro cap; equivalent passive spring helix, fixed bottle',
               'thread': {'pitch': pitch, 'release_angle': release_angle, 'spring': stiffness,
                          'damping': damping, 'rotary_drag': rotary_drag, 'z0': z0},
               'negative_no_close': negative, 'dof_names': hand.dof_names, 'contact_links': contact_links,
               'video_fps': 60})
    if run.writer:
        # No frame has yet been written. Keep real-time playback at 120 Hz
        # physics / one image per two steps, without changing the shared Run.
        import imageio.v2 as imageio
        run.writer.close()
        run.writer = imageio.get_writer(str(run.output/'video.mp4'), fps=60, codec='libx264', quality=8, macro_block_size=2)
    angle, last_yaw, released_step, max_error = 0., 0., None, 0.
    for step in range(run.args.max_steps):
        tick = step/2
        states = run.observe()
        s = states[0]
        w, x, y, z = s['orientation']
        yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        angle += math.atan2(math.sin(yaw-last_yaw), math.cos(yaw-last_yaw))
        last_yaw = yaw
        coefficient = pitch/(2*math.pi)
        error = s['position'][2]-z0-coefficient*angle
        force, torque = 0., 0.
        if released_step is None:
            max_error = max(max_error, abs(error))
            if angle >= release_angle:
                thread.CreateJointEnabledAttr().Set(False)
                released_step = step
                run.event('thread_disengaged', cap_angle=angle, position=s['position'], helix_error=error)
            else:
                rate = s['linear_velocity'][2]-coefficient*s['angular_velocity'][2]
                force = -stiffness*error-damping*rate
                torque = -coefficient*force-rotary_drag*s['angular_velocity'][2]
                cap.apply_forces_and_torques_at_pos(forces=[0, 0, force], torques=[0, 0, torque])
        if tick < 120:
            phase, fraction = 'open', 0.
        elif tick < 360:
            phase, fraction = 'grasp', min(1., (tick-120)/180)
        elif released_step is None:
            phase, fraction = 'unscrew', 1.
        else:
            phase, fraction = 'lift', 1.
        target_angle = min(240., max(0., (tick-360)/60*35.))
        target_velocity = 35. if 360 <= tick < 772 and released_step is None else 0.
        target_height = max(0., angle)*coefficient
        if released_step is not None:
            target_height = release_angle*coefficient+min(.16, (step-released_step)*run.dt*.04)
        if negative:
            fraction = 0.
        fingers = q_open+(q_closed-q_open)*fraction
        hand.set_dof_position_targets(fingers)
        spin.GetTargetVelocityAttr().Set(target_velocity)
        height.GetTargetPositionAttr().Set(target_height)
        contact_forces = contact.get_contact_force_matrix(dt=run.dt).numpy().tolist()
        run.step(phase, [{'joints': fingers.tolist(), 'wrist_angle_deg': target_angle, 'wrist_height': target_height,
                         'wrist_velocity_deg_s': target_velocity, 'finger_contact_forces': contact_forces,
                         'thread_force_z': force, 'thread_torque_z': torque, 'cap_angle': angle,
                         'helix_error': error, 'thread_engaged': released_step is None}], states)
        if step % 240 == 0:
            run.event('progress', cap_angle=angle, cap_position=s['position'], helix_error=error, phase=phase)
        if released_step is not None and (step-released_step)*run.dt > 10.:
            break
    final = run.observe()[0]
    from cap_verify import verify_cap_trace
    run.trajectory.flush()
    with (run.output/'trajectory.jsonl').open() as trace:
        verification = verify_cap_trace(run.manifest, map(json.loads, trace))
    run.finish({'success': verification['success'], 'phase': 'done' if verification['success'] else 'failed',
                'abort_reason': None if verification['success'] else 'physical verification failed or step budget exhausted',
                'verification': verification,
                'cap_angle': angle, 'released_step': released_step, 'final_cap': final,
                'max_helix_error': max_error, 'negative_no_close': negative})
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type': type(error).__name__, 'message': str(error)})
    run.close(1)
