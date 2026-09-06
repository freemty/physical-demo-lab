"""Bounded Jacobian targets; only native position drives move the robot."""
import numpy as np


LOW = np.array([-2.8973, -1.7628, -2.8973, -3.0718, -2.8973, -.0175, -2.8973])
HIGH = np.array([2.8973, 1.7628, 2.8973, -.0698, 2.8973, 3.7525, 2.8973])


def quaternion_error(goal, current):
    goal, current = np.asarray(goal, dtype=float), np.asarray(current, dtype=float)
    goal = goal / np.linalg.norm(goal)
    current = current / np.linalg.norm(current)
    w = goal[0]*current[0] + goal[1:] @ current[1:]
    v = -goal[0]*current[1:] + current[0]*goal[1:] - np.cross(goal[1:], current[1:])
    return v * (1. if w >= 0 else -1.)


def bounded_targets(q, jacobian, position_error, rotation_error, damping=.01, max_delta=.12):
    q = np.asarray(q, dtype=float)
    jacobian = np.asarray(jacobian, dtype=float)
    error = np.r_[position_error, rotation_error]
    if q.shape != (7,) or jacobian.shape != (6, 7) or not np.isfinite(np.r_[q, jacobian.ravel(), error]).all():
        raise ValueError("Invalid finite joint/Jacobian input")
    delta = jacobian.T @ np.linalg.solve(jacobian @ jacobian.T + damping**2*np.eye(6), error)
    delta *= min(1., max_delta / max(float(np.max(np.abs(delta))), 1e-12))
    # This bounds target error, not motor torque or the measured joint velocity.
    return np.clip(q + delta, LOW + .002, HIGH - .002)


class CastleController:
    def __init__(self, robot):
        self.robot = robot
        self.last_record = None

    def target(self, position, orientation):
        q, ee, quat = self.robot.get_current_state()
        jacobian = self.robot.get_jacobian_matrices().numpy()[0, self.robot.end_effector_link_index - 1, :, :7]
        target = bounded_targets(q[0, :7], jacobian, np.asarray(position)-ee[0],
                                 quaternion_error(orientation, quat[0]))
        self.robot.set_dof_position_targets(target, dof_indices=list(range(7)))
        self.last_record = dict(arm_position_target=target.tolist(), actual_arm_q=q[0,:7].tolist(),
                                damping=.01, maximum_target_error_rad=.12)
        return self.last_record
