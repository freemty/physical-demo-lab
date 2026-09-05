"""Independent-process multi-seed runs, preserving failed attempts and exit codes."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('task')
parser.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2])
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--gpu', type=int, default=7)
parser.add_argument('--video-seed', type=int, default=0)
args = parser.parse_args()
args.root.mkdir(parents=True, exist_ok=False)
rows = []
for seed in args.seeds:
    output = args.root/f'seed-{seed}'
    command = [sys.executable, str(Path(__file__).with_name('run_task.py')), args.task,
               '--seed', str(seed), '--gpu', str(args.gpu), '--output', str(output)]
    if seed != args.video_seed:
        command += ['--no-video', '--width', '480', '--height', '360']
    print(f'Running {args.task} seed {seed}', flush=True)
    with (args.root/f'seed-{seed}.launcher.log').open('x') as stream:
        proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    result_path = output/'result.json'
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    rows.append({'seed': seed, 'returncode': proc.returncode, 'output': str(output),
                 'success': proc.returncode == 0 and result is not None and result['success'], 'result': result})
    summary = {'task': args.task, 'runs': rows, 'passed': sum(bool(r['success']) for r in rows), 'total': len(rows)}
    (args.root/'summary.json').write_text(json.dumps(summary, indent=2))
    print(f"Seed {seed}: {'PASS' if rows[-1]['success'] else 'FAIL'}", flush=True)
raise SystemExit(0 if summary['passed'] == summary['total'] else 2)
