"""Derive key stages from recorded controls; never synthesize physical success."""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024*1024), b""):
            h.update(data)
    return h.hexdigest()


def finite(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite value in trajectory")
    elif isinstance(value, dict):
        for v in value.values():
            finite(v)
    elif isinstance(value, list):
        for v in value:
            finite(v)


def selected_state(row):
    name = row["phase"].split(":")[0] if ":" in row["phase"] else None
    return {"step":row["step"], "sim_time":row["sim_time"], "physics_steps":row["physics_steps"],
            "commands":row["commands"], "robots":row["robots"],
            "active_object_after_step":next((o for o in row["objects_after_step"] if o["id"]==name), None)}


def export_keyframes(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Export directory must be new. Existing evidence is never overwritten.")
    manifest = json.loads((run/"manifest.json").read_text())
    result = json.loads((run/"result.json").read_text())
    if file_hash(run/"source-ir.json") != manifest["ir_sha256"]:
        raise ValueError("Source blueprint hash mismatch")
    rows, previous, segments, active, first, last = 0, 0., [], None, None, None
    trajectory_hash = hashlib.sha256()
    with (run/"trajectory.jsonl").open("rb") as stream:
        for raw in stream:
            trajectory_hash.update(raw)
            row = json.loads(raw)
            finite(row)
            if row["step"] != rows or row["physics_steps"] != 4*(rows+1):
                raise ValueError("Control/physics step discontinuity")
            if abs(row["sim_time"]-previous-1/60) > 1e-7:
                raise ValueError("Control time discontinuity")
            phase = row["phase"].removesuffix(":converge")
            if phase != active:
                if last is not None:
                    segments.append({"phase":active, "first":selected_state(first), "last":selected_state(last)})
                active, first = phase, row
            last, previous, rows = row, row["sim_time"], rows+1
    if last is None or rows != result["physics_steps"]:
        raise ValueError("Empty or incomplete control trajectory")
    segments.append({"phase":active, "first":selected_state(first), "last":selected_state(last)})
    if abs(previous-result["sim_seconds"]) > 1e-7:
        raise ValueError("Result time mismatch")
    events = []
    with (run/"events.jsonl").open() as stream:
        for line in stream:
            event = json.loads(line)
            finite(event)
            if not isinstance(event["step"], int) or not 0 <= event["step"] <= rows:
                raise ValueError("Event step outside trajectory")
            events.append(event)
    inspection_path = run / "robot-inspection.json"
    dofs = json.loads(inspection_path.read_text()).get("dofs") if inspection_path.exists() else None
    output.mkdir(parents=True, exist_ok=False)
    (output/"keyframes.json").write_text(json.dumps({
        "schema":"castle-keyframes/1", "source_run":str(run),
        "robot_dof_names":dofs,
        "selection":"First and last state of each control phase; :converge stays in its parent phase.",
        "units":{"position":"meter","orientation":"wxyz quaternion","joint_positions":"arm revolute joints in radians; finger prismatic joints in meters; native DOF order","time":"simulated second"},
        "segments":segments}, indent=2)+"\n")
    (output/"events.json").write_text(json.dumps(events, indent=2)+"\n")
    with (output/"waypoints.csv").open("x", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["phase","step","sim_time_s","commanded_hand_xyz_m","commanded_orientation_wxyz",
                         "gripper_closed","measured_hand_xyz_m","measured_orientation_wxyz","measured_joint_positions"])
        for seg in segments:
            row = seg["last"]
            command, robot = row["commands"][0], row["robots"][0]
            writer.writerow([seg["phase"],row["step"],row["sim_time"],
                json.dumps(command.get("hand_target")),json.dumps(command.get("orientation")),
                command.get("gripper_closed"),json.dumps(robot["hand_position"]),
                json.dumps(robot["hand_orientation"]),json.dumps(robot["joints"])])
    summary = {"schema":"castle-export/1", "source_run":str(run), "control_samples":rows,
               "phase_count":len(segments), "event_count":len(events),
               "completed_parts":result.get("completed_parts",[]),
               "task_reported_success":result["success"],
               "source_hashes":{"trajectory.jsonl":trajectory_hash.hexdigest(),
                   **{name:file_hash(run/name) for name in ["manifest.json","source-ir.json","events.jsonl","result.json"]}},
               "derived_hashes":{name:file_hash(output/name) for name in ["keyframes.json","waypoints.csv","events.json"]},
               "scope":"Sparse measured/commanded stage endpoints from a real run. Not a replay controller, independent physics audit, lossless replacement or training-dataset format."}
    (output/"export-manifest.json").write_text(json.dumps(summary, indent=2)+"\n")
    return summary
