"""Independently audit recorded outcomes, source hashes and trajectory continuity."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'demos'))
from verification import verify_object

parser = argparse.ArgumentParser()
parser.add_argument('--runs', type=Path, nargs='+', required=True)
parser.add_argument('--expected-seeds', type=int, nargs='+', default=list(range(10)))
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise SystemExit('Audit output already exists; choose a new path.')
rows = []
for folder in args.runs:
    result = json.loads((folder/'result.json').read_text())
    manifest = json.loads((folder/'manifest.json').read_text())
    source_valid = all(
        hashlib.sha256((folder/'source'/name).read_bytes()).hexdigest() == digest
        for name, digest in manifest['source_files'].items()
    )
    count, continuous = 0, True
    with (folder/'trajectory.jsonl').open() as stream:
        for line in stream:
            frame = json.loads(line)
            continuous &= frame['step'] == count and frame['physics_steps'] == count+1
            continuous &= math.isclose(frame['sim_time'], (count+1)*manifest['physics_dt'], abs_tol=1e-7)
            continuous &= len(frame['objects_before_step']) == 3
            count += 1
    continuous &= count == result['physics_steps']
    continuous &= math.isclose(result['sim_seconds'], count*manifest['physics_dt'], abs_tol=1e-7)
    recomputed = [verify_object(obj['state'], manifest['bins'][obj['state']['color']]) for obj in result['objects']]
    matches = all(old['checks'] == new['checks'] and old['success'] == new['success']
                  for old, new in zip(result['objects'], recomputed))
    passed = (result['success'] and result['phase'] == 'done' and result['abort_reason'] is None
              and len(recomputed) == 3 and all(obj['success'] for obj in recomputed)
              and matches and source_valid and continuous)
    rows.append({'seed': result['seed'], 'success': bool(passed), 'output': str(folder),
                 'source_sha256': manifest['source_sha256'], 'git_commit': manifest['git_commit'],
                 'source_snapshot_verified': source_valid, 'trajectory_continuous': bool(continuous),
                 'verifier_recomputed_and_matched': matches, 'trajectory_frames': count,
                 'sim_seconds': result['sim_seconds'], 'loop_wall_seconds': result['wall_seconds'],
                 'renderer_gpu': manifest['renderer_gpu_requested'], 'result': result})
rows.sort(key=lambda row: row['seed'])
seeds = [row['seed'] for row in rows]
complete = sorted(seeds) == sorted(args.expected_seeds) and len(set(seeds)) == len(seeds)
report = {'task': 'conveyor_color_sort', 'expected_seeds': args.expected_seeds,
          'complete_seed_set': complete, 'runs': rows, 'passed': sum(row['success'] for row in rows),
          'total': len(rows), 'single_controller_hash': len({row['source_sha256'] for row in rows}) == 1,
          'success': complete and all(row['success'] for row in rows),
          'scope': 'Three boxes, privileged poses and labels, scripted differential IK, frictional grasp, stopped belt.'}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2))
print(json.dumps({key: report[key] for key in ['success', 'passed', 'total', 'complete_seed_set', 'single_controller_hash']}))
raise SystemExit(0 if report['success'] else 2)
