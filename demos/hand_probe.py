"""Asset integration probe only; this is not a bottle-opening task result."""
import traceback
from sim_runtime import Run

run = Run('hand_asset_probe', max_steps=360)
try:
    import numpy as np
    from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics
    from isaacsim.core.experimental.prims import Articulation, RigidPrim
    from isaacsim.core.experimental.utils.stage import add_reference_to_stage
    from isaacsim.storage.native import get_assets_root_path

    path = '/World/Allegro'
    asset = get_assets_root_path()+'/Isaac/Robots/WonikRobotics/AllegroHand/allegro_hand.usd'
    add_reference_to_stage(usd_path=asset, path=path)
    hand = Articulation(path)
    hand.set_world_poses(positions=[0., 0., 1.15], orientations=[0., 1., 0., 0.])
    run.write('asset-structure.json', {'asset': asset, 'dof_names': hand.dof_names,
        'link_paths': hand.link_paths, 'limits': [value.numpy().tolist() for value in hand.get_dof_limits()],
        'joints': [{'path': str(p.GetPath()), 'type': p.GetTypeName(),
                    'body0': [str(t) for t in UsdPhysics.Joint(p).GetBody0Rel().GetTargets()],
                    'body1': [str(t) for t in UsdPhysics.Joint(p).GetBody1Rel().GetTargets()]}
                   for p in run.stage.Traverse() if p.IsA(UsdPhysics.Joint)]})
    palm_path = hand.link_paths[0][0]
    fixed = UsdPhysics.FixedJoint.Define(run.stage, '/World/ProbeMount')
    fixed.CreateBody1Rel().SetTargets([palm_path])
    fixed.CreateLocalPos0Attr().Set(Gf.Vec3f(0, 0, 1.15))
    fixed.CreateLocalRot0Attr().Set(Gf.Quatf(0, 1, 0, 0))
    for prim in run.stage.Traverse():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateDisableGravityAttr(True)
    q_open = np.zeros(hand.num_dofs, dtype=np.float32)
    q_closed = np.zeros(hand.num_dofs, dtype=np.float32)
    for i, name in enumerate(hand.dof_names):
        q_closed[i] = .9 if not name.endswith('_0') else .0
        if name == 'thumb_joint_0':
            q_open[i], q_closed[i] = .28, 1.1
    hand.set_default_state(dof_positions=q_open)
    hand.set_dof_gains(stiffnesses=3., dampings=.1)
    hand.set_dof_max_efforts(.5)
    palm = RigidPrim(palm_path)

    class Adapter:
        def reset_to_default_pose(self):
            hand.reset_to_default_state()

        def get_current_state(self):
            p, q = palm.get_world_poses()
            return hand.get_dof_positions().numpy(), p.numpy(), q.numpy()

    run.robots.append(Adapter())
    run.box('/World/Floor', [0, 0, -.03], [3, 3, .06], [.3]*3)
    run.box('/World/Table', [0, 0, .76], [.75, .75, .08], [.4]*3)
    run.camera(eye=(.7, -.9, 1.4), target=(.03, 0, 1.06))
    run.start({'asset': asset, 'scope': 'open/close and link-coordinate integration probe; not bottle opening'})
    probes = []
    for step in range(360):
        closed = 120 <= step < 280
        hand.set_dof_position_targets(q_closed if closed else q_open)
        run.step('close' if closed else 'open', [{'joints': (q_closed if closed else q_open).tolist()}], [])
        if step in (100, 260, 350):
            links = []
            for link_path in hand.link_paths[0]:
                p, q = RigidPrim(link_path).get_world_poses()
                links.append({'path': link_path, 'position': p.numpy().tolist(), 'orientation': q.numpy().tolist()})
            probes.append({'step': step, 'links': links, 'joints': hand.get_dof_positions().numpy().tolist()})
            run.write('link-probes.json', probes)
    run.finish({'success': True, 'phase': 'asset_probe_done', 'abort_reason': None,
                'not_a_bottle_task': True, 'dof_names': hand.dof_names})
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    traceback.print_exc()
    run.write('exception.json', {'type': type(error).__name__, 'message': str(error)})
    run.close(1)
