"""Run independent seeded Isaac Sim processes and retain every attempt."""
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--seeds', type=int, nargs='+', default=list(range(10)))
parser.add_argument('--gpu', type=int, default=1)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--objects', type=int, default=3, choices=(1, 2, 3))
parser.add_argument('--video-seed', type=int, default=0)
args = parser.parse_args()
args.root.mkdir(parents=True, exist_ok=False)
runner = Path(__file__).with_name('run.sh')
rows = []
for seed in args.seeds:
    output = args.root/f'seed-{seed}'
    command = ['bash', str(runner), '--seed', str(seed), '--gpu', str(args.gpu),
               '--objects', str(args.objects), '--output', str(output)]
    if seed != args.video_seed:
        command += ['--no-video', '--width', '480', '--height', '360']
    print(f'Running seed {seed}', flush=True)
    # run.sh independently writes its complete console log next to the output.
    with (args.root/f'seed-{seed}.launcher.log').open('x') as stream:
        proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    result_path = output/'result.json'
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    row = {'seed': seed, 'command': command, 'returncode': proc.returncode,
           'success': proc.returncode == 0 and result is not None and result['success'],
           'result': result, 'output': str(output)}
    rows.append(row)
    summary = {'runs': rows, 'passed': sum(bool(r['success']) for r in rows), 'total': len(rows)}
    (args.root/'summary.json').write_text(json.dumps(summary, indent=2))
    print(f"Seed {seed}: {'PASS' if row['success'] else 'FAIL'}", flush=True)
print(json.dumps({'passed': summary['passed'], 'total': summary['total']}), flush=True)
raise SystemExit(0 if summary['passed'] == summary['total'] else 2)
