---
name: project-skill
description: Use when working on physical-demo-lab demos, Isaac Sim runtime integration, recorded results, or reusable project lessons.
---

# physical-demo-lab — Project Knowledge

> Isaac Sim 物理交互 demo 的逐项复现与可审计经验积累

## Architecture

- The Mac edits and reviews; server 23 executes Isaac Sim. Large runtime data
  lives outside Git under `/data1/ybyang/physical-demo-lab-runtime`.
- Task code in `demos/` drives physics; simulator-independent verification judges
  outcomes. A finished state machine is not a successful physical execution.
- Reports retain attempt history; `docs/knowhow/` holds reusable lessons.
  `docs/demos.json` records scoped completion plus implementation fingerprints.

## Experiment findings

- `demo001` conveyor color sorting: scripted, privileged-state baseline;
  final seeds 0–9 pass for 30 boxes, including one teardown-failure retry and
  two source revisions. Not a fixed-version first-pass 10/10 benchmark.
  Evidence: `reports/bootstrap-validation.md`, `reports/audit-final.json`.
- The other seven reference task categories are planned, not implemented.
  Read `docs/README.md` for source coverage and next-demo selection.

## Durable pitfalls

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

## Active interfaces

- Verified runtime: Python 3.12.13 / Isaac Sim 6.0.1.0 / Torch 2.11.0+cu128.
- `scripts/run.sh`: new output directory required; snapshots source and captures
  console evidence. `scripts/evaluate.py` and `scripts/audit_runs.py` currently
  target the conveyor task, not arbitrary future demos.
- Every completed demo must pass `scripts/check_closeout.py --demo <id>` after
  its report and lessons are updated. Follow
  `docs/knowhow/runbooks/demo-closeout.md`; this is a completion gate, not an
  autonomous writer or a substitute for physical verification.
