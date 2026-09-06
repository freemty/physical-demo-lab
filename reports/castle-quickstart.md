# Castle20 Quickstart Packaging Validation

2026-09-06. The fixed castle20 quickstart is verified: Blender generation and
re-open checks, a new complete twenty-piece assembly, strict physical/video audit,
key-stage export, and clean-clone scene/smoke checks passed. This is separate from
the completed [six-seed native acceptance](demo009-castle20.md).

## Scope

The user requested a repository that another person can open and use, beginning
with Blender-generated blocks, simulator import and trajectory generation.
This milestone adds portable wrappers and documentation around the fixed
twenty-piece example. It does not merge other repositories or resume 200/1000
piece experiments.

The accepted eight-file native implementation and blueprint remain unchanged.
New files provide Blender design generation, build integrity checks, a runtime
preflight, explicit EULA opt-in, strict native/video audit, and measured
key-stage export. New runtime setup uses the existing pinned install recipe with
a portable runtime path and a PATH-discovered uv executable.

## Verified Packaging Checks

- Blender 4.5.0 generated Goal, Loose and Exploded scenes, then reopened the saved
  file and checked twenty independent pieces, raw dimensions, local geometry
  transforms, collision labels and masses. The exported IR SHA-256 is
  `e44fa205d74db0cc9fad91c739100f69dfc4fcb56a8c72b89e2a61c83dfc1910`.
- Preflight passed on the existing project runtime and GPU 1. Installer
  `--check` passed with a new path and created no directory or environment.
- The real accepted seed 0 trajectory exported into 242 segments and 181 events.
  These are sparse measured/commanded endpoints, not replacement trajectories.
- Fourteen new unit tests passed, including changed blueprints, missing Blender,
  missing build evidence, discontinuous/truncated logs, failed-run preservation,
  output overwrite refusal and budget checks.
- All three Blender design renders were inspected. The sample-file hashes and
  local guide links passed; all 65 project unit tests passed.
- A clean clone of `5abe0e4` built and re-opened the Blender scene, then ran the
  documented loose-state smoke on GPU 7: 1,440 native steps, 360 control steps,
  180 video frames / six simulated seconds, process exit 0 and no GPU-monitor
  termination. Its strict complete-assembly audit intentionally returned 1.
  See [clean-clone physical receipt](castle-quickstart-clean-clone-physics.json)
  and [strict negative receipt](castle-quickstart-clean-clone-audit.json).
  These checks used the existing runtime, not a fresh dependency installation.
- The strict entry also rejected the earlier stable loose run, with a successful
  video decode but no assembly: [negative receipt](castle-quickstart-loose-negative.json).
- The new entry completed and independently audited the full assembly below.


## New-Entry Full Assembly

The documented entry completed `seed0-entry-v1` on GPU 1 from
2026-09-06 11:08:37 to 11:37:18 UTC. Process wall time was 1,721.10 seconds
(28.68 minutes), return code 0, with no resource-monitor termination.

| Check | Observed Result |
| --- | --- |
| Complete assembly / native bilateral lifts | 20 / 20 |
| Native physics / control samples | 105,644 at 240 Hz / 26,411 at 60 Hz |
| Replayed continuous released stability | 11.2333 seconds |
| Video | 13,206 frames, 640 × 480, 30 Hz, 440.20 seconds |
| Full video decode / strict audit exit | 0 / 0 |
| Export | 242 phase segments and 181 events |

Receipts are byte-identical copies of the raw records:
[strict aggregate](castle-quickstart-entry-audit.json),
[native physics](castle-quickstart-entry-physics.json),
[process](castle-quickstart-entry-process.json),
[entry point](castle-quickstart-entrypoint.json), and
[new-run export](castle-quickstart-entry-export.json).

The manifest records native commit `2d1c984`. The wrapper was uncommitted at
launch; its separately recorded SHA-256 is
`9b305c1256e675fd4783ee3787ac9576e63535902eec06dd68d5e36ddef446bc`,
identical to the subsequently committed `5abe0e4` and `87ad641` version.
All eight native acceptance files still match `2d1c984`; packaging did not
change the controller, blueprint, physical budgets, or success predicates.

The full video decoded without errors. Visual review covered the native final
PNG and unaltered video frames at 0, 20, 70, 150, 250, 340 and 430 seconds.
They show the scattered start, grasp/transport stages, intermediate layers and
assembled castle. This was sampled visual inspection, not continuous viewing of
every frame or a separate motion-quality acceptance.

The new export is in `seed0-entry-v1-keyframes`. The repository's bundled sample
still refers to the earlier accepted `final-v6-seed0`; its provenance was not
silently replaced with this new run.

## Clean-Clone and Contributor Checks

The clean clone at
`/data1/ybyang/physical-demo-lab-runtime/quickstart-clean-clone-20260906`
built and re-opened the scene and ran the six-second loose smoke at `5abe0e4`.
After fast-forwarding it to `87ad641`, all 65 tests passed using the existing
project runtime. No full assembly was repeated from this clone; the full run
above used the canonical checkout with the same committed wrapper.

An initial contributor-check invocation used system Python 3.10 and failed
because NumPy was absent. Selecting the dedicated runtime's Python resolved
that import error; no global package was installed. Both Getting Started guides
now show environment activation before repository checks. Sample hashes, local
guide links, shell-example syntax, closeout records and host-map parity passed.

## Raw Paths and Retained Development Outputs

Root: `/data1/ybyang/physical-demo-lab-runtime/outputs/castle-quickstart`.

- `design-v1`: three rendered layouts, saved Blender file and re-open audit.
- `design-v2`: second build without rendering, with explicit nonzero Blender
  Python-error propagation and required output-receipt checking.
- `seed0-export-v1`: initial export retained; its joint-units label was too broad.
  Native Franka arrays include prismatic finger displacements as well as arm
  angles. `seed0-export-v2` corrects labels and includes native DOF names without
  changing the original recorded measurements. Export-v3 uses LF CSV line endings
  after the staged whitespace check caught CSV's default CRLF. Export-v4 also
  binds the native DOF metadata hash and records the run mode. All versions remain
  under the raw root.
- `seed0-entry-v1`: full run through the new wrapper using design-v1's identical
  blueprint. Adjacent entrypoint, console, process and GPU records preserve the
  delegated native command. `seed0-entry-v1-review` retains the seven sampled
  video frames, selected by frame indices 0, 600, 2100, 4500, 7500, 10200 and 12900.

The bundled examples are byte-identical copies of design-v1 and export-v4;
their paths and hashes are recorded in
[provenance.json](../examples/castle20/provenance.json).

## Limits

This is not a fresh OS installation or a second-host GPU verification.
The dependency recipe was previously exercised for the project environment;
this round checks portable setup preconditions and uses that existing runtime.
Blender-only portability is documented separately from actual Linux tests.

The repository remains private unless the user explicitly requests a visibility
change. A root source-code license has not been selected. NVIDIA software and
robot assets retain their own terms and are not redistributed in the example.
