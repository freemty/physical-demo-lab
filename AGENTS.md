# physical-demo-lab

> Isaac Sim 物理交互 demo 的逐项复现与可审计经验积累

## Project knowledge

- Durable project map: `.agents/skills/project-skill/SKILL.md`
- Verified operational knowledge: `docs/knowhow/`

Read the project map when history or architecture matters. Read a specific
knowhow entry only when its topic is relevant.

## Gotchas

- Preserve unrelated dirty worktree changes.
- Keep `.agents/` and `.claude/` project-skill mirrors identical when both
  hosts are used.
- Record verified causes and commands; do not archive unresolved guesses.

## Demo completion contract

- Before a demo, read `docs/README.md`, its relevant knowhow, and its task spec.
  Work through `docs/demos.json` one demo at a time; distinguish a scripted
  baseline from a full reference reproduction or learned policy.
- After every implemented or investigated milestone, use LabMate update-docs
  to record the result, failed attempts, reproducible fix, evidence paths and
  limits in this repository's `docs/` and `reports/`. If that skill is unavailable
  on the executing host, follow `docs/knowhow/runbooks/demo-closeout.md` directly.
  Do this before declaring completion or moving to the next demo. Read-only
  questions alone do not require new records.
- Material stable findings also update the compact project-skill map and both
  mirrors; transient logs stay in Data1. Do not turn an unverified diagnosis into
  a confirmed lesson. Do not overwrite prior runs or failed-attempt evidence.
- Mark `complete` only after physical checks, process exit and required media
  checks pass within an explicitly recorded scope. Refresh the implementation
  fingerprints only after verification and documentation, never to silence a
  stale-record error. Run `python3 scripts/check_closeout.py --demo <id>` and
  `bash scripts/check_project.sh` before handoff. Missing docs mean not complete.

## Compute boundary

- Develop, test and commit in `/data1/ybyang/physical-demo-lab` on
  server 23, then push this repository from server 23. The Mac is for access and
  viewing results, not an independent development/commit source.
- Keep actionable work and acceptance criteria in `docs/TODO.md`; maintain it
  alongside the scoped completion ledger. A listed TODO is not a completed run.
- Put bulky environments, caches, temporary data and outputs under
  `/data1/ybyang/physical-demo-lab-runtime`. Check GPU availability live;
  never stop unrelated jobs or modify other projects' environments.
- Setup is project-local. Do not install global hooks, enable scheduled work,
  or publish additional material merely because LabMate is initialized.
