# Castle Output Contract

[Getting Started](../../GETTING_STARTED.md)

## Design Bundle

`castle.blend` has Goal, Loose and Exploded scenes. Each contains twenty
independent parent objects with named mesh children. Parent custom properties
retain source identity, target/loose positions and support dependencies.
These scenes are design views, not physics rollouts.

`scene_spec.json` is the simulator input. It is copied byte-for-byte from the
accepted blueprint. `blender-audit.json` records the saved Blender file hash,
blueprint hash and reopened geometry checks. Changing the saved Blender file
invalidates that build receipt. The quickstart rejects edited blueprints;
lower-level experiments need a separate specification and acceptance run.

## Full Run

| File | Meaning |
| --- | --- |
| `initial-authored.usda`, `scene.usda` | Native Isaac scene; external NVIDIA robot references are not bundled |
| `source-ir.json`, `manifest.json`, `source/`, `invocation.json` | Inputs, versions, source snapshots and hashes |
| `trajectory.jsonl` | Every 60 Hz control step: command, robot state, object states before/after |
| `physics-steps.jsonl.gz` | Every 240 Hz physical step: object states and filtered contacts |
| `contacts.jsonl` | Control-rate contact snapshots; not a replacement for the native-rate stream |
| `events.jsonl` | Part start/end and motion-end receipts, including convergence residuals |
| `robot-inspection.json` | Native link names and degree-of-freedom order |
| `initial-verification.json`, `result.json` | Initial and final task checks; result may report failure |
| `video.mp4`, `preview.png`, `final.png` | Actual simulator renders at the recorded camera |
| Adjacent `.entrypoint.json` | Quickstart arguments, generated design hashes and delegated native command |
| Adjacent `.console.log`, `.process.json`, `.gpu.jsonl` | Console, exit status, time limit and sampled process-group GPU ownership |

A row's `step` is zero-based. `physics_steps` is the number of elapsed native
steps, so control row 0 ends at physics step 4. `sim_time` is seconds since the
episode clock began. Commands precede the corresponding physical steps;
`robots` and `objects_after_step` are measured afterward.

Positions are world-frame meters. Quaternions use **wxyz**.
The native nine-position robot array contains seven revolute arm positions in
radians followed by two prismatic finger positions in meters. Check
`robot-inspection.json` rather than treating all nine numbers as angles.
The native API retains a leading batch dimension for robot measurements.

The full action contract is recorded under `commands`: Cartesian hand target,
orientation, gripper state and the finite native joint-drive target. A target
is not a measurement; keep commanded and measured values distinct.

## Key-Stage Export

`export` streams the actual control log and keeps the first and last row of
each contiguous phase. A `:converge` suffix remains in its parent phase.
The accepted seed 0 sample produces 242 segments from 26,411 control rows.

`keyframes.json` preserves each selected row's command and robot measurement,
plus the active block state. It records the native DOF names when available.
`waypoints.csv` exposes the last row of each phase; vector columns are JSON
arrays, including the native batch dimension for measured values.
`events.json` retains the complete event stream.
`export-manifest.json` records input and derived-file SHA-256 values.

Export checks step/time continuity and input blueprint integrity. Its
`task_reported_success` field copies the run's claim; it is **not** an
independent acceptance verdict. A failed run can be exported for diagnosis
without becoming successful. Run the strict audit separately.

These files are sparse inspection data. They are not a direct real-robot
replay program, an IK solver, a motion planner, a lossless episode archive,
or a LIBERO/LeRobot dataset conversion.

## Strict Acceptance

`castle.py audit` calls the original independent native-state auditor, then
fully decodes the video with ffmpeg. Success requires a complete assembly,
consistent evidence and a clean decode. It preserves the detailed physics
receipt and writes a separate aggregate receipt.

The physical replay recomputes predicates on logged states. It does not
re-execute the robot actions or prove cross-simulator equivalence.
Video decoding does not replace visual inspection. Source snapshots are
trusted local code; do not run the auditor on an untrusted third-party archive
without reviewing its bundled verifier.
