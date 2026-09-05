"""Run one new demo with full console capture and independent process status."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task', choices=['checkout', 'gear_assembly', 'dual_blocks', 'bottle_cap', 'restaurant', 'dual_lego', 'humanoid_walk'])
    parser.add_argument('--output', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    root = Path(__file__).resolve().parents[1]
    runtime = Path(os.environ.get('PHYSICAL_DEMO_RUNTIME', '/data1/ybyang/physical-demo-lab-runtime'))
    console = Path(str(args.output)+'.console.log')
    status_path = Path(str(args.output)+'.process.json')
    if any(p.exists() for p in (args.output, console, status_path)):
        parser.error('Output, console and process-status paths must all be new.')
    entry = root/'demos'/f'{args.task}.py'
    if not entry.exists():
        parser.error(f'Task is not implemented: {args.task}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for key, relative in [('XDG_CACHE_HOME', 'cache/xdg'), ('CUDA_CACHE_PATH', 'cache/cuda'),
                          ('__GL_SHADER_DISK_CACHE_PATH', 'cache/gl'), ('TMPDIR', 'tmp')]:
        env[key] = str(runtime/relative)
        (runtime/relative).mkdir(parents=True, exist_ok=True)
    env.update(OMNI_KIT_ACCEPT_EULA='YES', PYTHONUNBUFFERED='1')
    command = [str(runtime/'venv/bin/python'), str(entry), '--output', str(args.output), *remaining]
    started = datetime.now(timezone.utc).isoformat()
    with console.open('x') as stream:
        stream.write(json.dumps({'command': command, 'started_at': started})+'\n')
        subprocess.run(['nvidia-smi', '--query-gpu=index,uuid,name,memory.used,utilization.gpu,driver_version', '--format=csv'], stdout=stream, stderr=subprocess.STDOUT)
        stream.flush()
        process = subprocess.Popen(command, env=env, cwd=root, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for line in process.stdout:
                stream.write(line)
                stream.flush()
                print(line, end='', flush=True)
            code = process.wait()
        except BaseException:
            process.terminate()
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
            raise
        finally:
            if process.poll() is not None:
                status_path.write_text(json.dumps({'command': command, 'returncode': process.returncode,
                    'started_at': started, 'ended_at': datetime.now(timezone.utc).isoformat(),
                    'console': str(console), 'output': str(args.output)}, indent=2))
    return code if code >= 0 else 128-code


if __name__ == '__main__':
    raise SystemExit(main())
