---
name: project-skill
description: Use when working on physical-demo-lab demos, Isaac Sim runtime integration, recorded results, or reusable project lessons.
---

# physical-demo-lab — Project Knowledge

> Isaac Sim 物理交互 demo 的逐项复现与可审计经验积累

## Architecture

- Develop, test, commit and push from server 23's
  `/data1/ybyang/physical-demo-lab`; the Mac connects and reviews.
  Large runtime data stays under `/data1/ybyang/physical-demo-lab-runtime`.
- Task code in `demos/` drives physics; simulator-independent verification judges
  outcomes. A finished state machine is not a successful physical execution.
- Reports retain attempt history; `docs/knowhow/` holds reusable lessons.
  `docs/demos.json` records scoped completion plus implementation fingerprints;
  `docs/TODO.md` holds actionable work, dependencies and acceptance criteria.
- README's completed-demo gallery uses unchanged simulation frames. Images and provenance
  live in `docs/previews/`; add previews only for explicitly verified scopes.

## Experiment findings

- `demo001` conveyor color sorting: scripted, privileged-state baseline;
  final seeds 0–9 pass for 30 boxes, including one teardown-failure retry and
  two source revisions. Not a fixed-version first-pass 10/10 benchmark.
  Evidence: `reports/bootstrap-validation.md`, `reports/audit-final.json`.
- `demo002` checkout: seeds 0, 1, 2 pass physical bagging and trajectory-replayed
  simulated scan/receipt checks; forced one-step failure returns 2. Known SKU IDs,
  not barcode perception. See `reports/demo002-checkout.md` and its audit.
- `demo003` gear insertion: three fixed-version seeds pass strict seating,
  alignment, release and process/trajectory checks after two retained failures.
  Approximate compound teeth, not precision transmission. See `reports/demo003-gears.md`.
- `demo004` two-arm bridge: three seeds pass both-arm participation and three
  seconds of released structure stability, with no control revision. Sequential
  workspace sharing, not joint grasping. See `reports/demo004-dual-blocks.md`.
- `demo005` Allegro cap: three final mass seeds pass contact-driven rotation,
  explicit passive-helix disengagement and continuous free-cap holding. Earlier
  stability failures are retained. See `reports/demo005-bottle-cap.md`.
- `demo006` service cart: three identical-version seeds pass fixed-arm loading,
  in-tray wheel-driven transport and three-second parked delivery. One earlier
  settling failure and zero-drive/one-step negatives are retained. See
  `reports/demo006-restaurant.md`; this is not a mobile dual-arm reproduction.
- Restaurant has a separate colorful cafe presentation layer. Final seed 0 matches
  all 2974 baseline physical frames exactly; visual assets are not new interaction
  capabilities. See `reports/demo006-restaurant-showcase.md`.
- `demo009` castle20: fixed-version seeds 0–5 pass 6/6 first attempts, each with
  20 native bilateral-force lifts, released stability, independent oracle replay,
  process checks and full video decode. Fixed blueprint / privileged-state baseline;
  not task generation or learned generalization. 200/1000 remain paused.
  See `reports/demo009-castle20.md` and
  `docs/knowhow/debug-solutions/castle-bounded-control-and-lift-evidence.md`.
- Lego geometry/spec drafts are paused before execution; humanoid is planned.
  Read `docs/README.md` for source coverage and next-demo selection.

## Durable pitfalls

- Keep visual polish separate from verified controllers. Inspect real lighting,
  material depth and camera-readback latency, and compare physical trajectories.
  The current showcase audit's overall success does not include its baseline
  comparison field; check that field explicitly until the recorded TODO is fixed.
  See `docs/knowhow/toolchain/simulation-presentation-layer.md`.
- Moving-carrier containment belongs in the carrier's local coordinates; verify
  the whole transport interval and net displacement, not only a final image or
  cumulative jitter path. See `docs/knowhow/toolchain/mobile-carrier-evidence.md`.
- Allegro fixed/floating roots can reorder link indices; bind the mounting link
  by verified name. Contact filters also need contact-report APIs. At non-60-Hz
  physics, explicitly align the app timeline and audit actual step counts.
  See `docs/knowhow/debug-solutions/allegro-mount-contact-clock.md`.
- For carried-part insertion, a downward gripper does not guarantee a level part;
  inspect part pose and collision clearance. Joint geometry/control revisions
  solved this gear fixture, without establishing separate causal effects. See
  `docs/knowhow/debug-solutions/gear-seating-and-pose.md`.
- Moving a kinematic belt surface may leave sleeping parcels stationary;
  the observed fix disables parcel sleep. It is not proof that changing sleep
  settings solves every contact problem. See
  `docs/knowhow/debug-solutions/conveyor-and-teardown.md`.
- Isaac Sim fast shutdown can hide failure exit codes; a physical result alone
  cannot establish a successful run. Flush evidence and preserve process status.
  The same debug note records the failed run and negative exit-code check.
- Do not copy another environment wholesale. SDK cache reuse was content-hash
  verified; setup/storage boundaries are in
  `docs/knowhow/infrastructure/server23-isaac-sim.md`.
- If server GitHub transport fails, a verified incremental Git bundle supports
  fast-forward-only sync without replacing `.git`. The same infrastructure
  note records the successful procedure and its conflict boundary.

## Active interfaces

- Verified runtime: Python 3.12.13 / Isaac Sim 6.0.1.0 / Torch 2.11.0+cu128.
- `scripts/run_task.py` isolates new demo processes and captures their exit status;
  `sim_runtime.py` records their physics, but task-specific auditors must be added.
  See `docs/knowhow/toolchain/checkout-and-process-evidence.md`.
- `scripts/run.sh`: new output directory required; snapshots source and captures
  console evidence. `scripts/evaluate.py` and `scripts/audit_runs.py` currently
  target the conveyor task, not arbitrary future demos.
- Every completed demo must pass `scripts/check_closeout.py --demo <id>` after
  its report and lessons are updated. Follow
  `docs/knowhow/runbooks/demo-closeout.md`; this is a completion gate, not an
  autonomous writer or a substitute for physical verification.
