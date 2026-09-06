# Castle20 Quickstart Packaging Validation

2026-09-06. Status: implementation and documentation in place; final new-entry
assembly and clean-clone checks still in progress. This report is separate from
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

## Checks Already Completed

- Blender 4.5.0 generated Goal, Loose and Exploded scenes, then reopened the saved
  file and checked twenty independent pieces, raw dimensions, local geometry
  transforms, collision labels and masses. The exported IR SHA-256 is
  `e44fa205d74db0cc9fad91c739100f69dfc4fcb56a8c72b89e2a61c83dfc1910`.
- Preflight passed on the existing project runtime and GPU 1. Installer
  `--check` passed with a new path and created no directory or environment.
- The real accepted seed 0 trajectory exported into 242 segments and 181 events.
  These are sparse measured/commanded endpoints, not replacement trajectories.
- Twelve new unit tests passed, including changed blueprints, missing Blender,
  missing build evidence, discontinuous/truncated logs, failed-run preservation,
  output overwrite refusal and budget checks.
- The new entry started an actual twenty-piece assembly on GPU 1. Its final
  result is pending; no success is claimed by this paragraph.

## Raw Paths and Retained Development Outputs

Root: `/data1/ybyang/physical-demo-lab-runtime/outputs/castle-quickstart`.

- `design-v1`: three rendered layouts, saved Blender file and re-open audit.
- `design-v2`: second build without rendering, with explicit nonzero Blender
  Python-error propagation and required output-receipt checking.
- `seed0-export-v1`: initial export retained; its joint-units label was too broad.
  Native Franka arrays include prismatic finger displacements as well as arm
  angles. `seed0-export-v2` corrects labels and includes native DOF names without
  changing the original recorded measurements.
- `seed0-entry-v1`: full run through the new wrapper using design-v1's identical
  blueprint. Adjacent entrypoint, console, process and GPU records preserve the
  delegated native command.

The bundled examples are byte-identical copies of design-v1 and export-v2;
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

Final run, media, clean-clone and repository checks will be appended before
declaring this packaging milestone complete.
