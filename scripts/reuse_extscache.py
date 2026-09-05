"""Copy only verified Isaac Sim 6.0.1 extension-cache distributions locally.

Optional acceleration for servers with the identical SDK already installed.
Source files are read-only. No environment, torch, or credentials are copied.
Distribution metadata is exposed only after all payload hashes pass.
"""
import argparse
import base64
import csv
import hashlib
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True, help='Existing site-packages')
parser.add_argument('--target', type=Path, required=True, help='New site-packages')
parser.add_argument('--report', type=Path, required=True)
args = parser.parse_args()
source, target = args.source.resolve(), args.target.resolve()
assert source != target and source.is_dir() and target.is_dir()
names = ['isaacsim_extscache_kit', 'isaacsim_extscache_kit_sdk', 'isaacsim_extscache_physics']
payload, metadata = {}, {}
for name in names:
    dist = f'{name}-6.0.1.0.dist-info'
    if (target/dist).exists():
        raise RuntimeError(f'Refusing to overwrite installed distribution: {dist}')
    with (source/dist/'RECORD').open(newline='') as stream:
        for relative, digest, size in csv.reader(stream):
            path = Path(relative)
            if relative == '../../../bin/isaacsim' or path.suffix == '.pyc':
                continue  # Entry point belongs to the new environment's main package.
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Unsafe distribution path: {relative}')
            if not (relative.startswith('isaacsim/') or relative.startswith(dist+'/')):
                raise ValueError(f'Unexpected distribution payload: {relative}')
            if not (source/path).resolve().is_relative_to(source):
                raise ValueError(f'Source path escapes site-packages: {relative}')
            bucket = metadata if relative.startswith(dist+'/') else payload
            item = (digest, size)
            if relative in bucket and bucket[relative] != item:
                raise ValueError(f'Conflicting shared payload: {relative}')
            bucket[relative] = item


def copy_verified(entry):
    relative, (digest, size) = entry
    src, dst = source/relative, target/relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256()
    length = 0
    with src.open('rb') as inp, dst.open('wb') as out:
        while data := inp.read(4*1024*1024):
            sha.update(data)
            length += len(data)
            out.write(data)
    if size and length != int(size):
        raise ValueError(f'Incorrect size: {relative}')
    actual = 'sha256='+base64.urlsafe_b64encode(sha.digest()).rstrip(b'=').decode()
    if digest and actual != digest:
        raise ValueError(f'RECORD hash mismatch: {relative}')
    shutil.copystat(src, dst)
    return length


started, total = time.monotonic(), 0
print(f'Verifying and copying {len(payload)} SDK files', flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:
    for i, size in enumerate(pool.map(copy_verified, payload.items()), 1):
        total += size
        if i % 2000 == 0:
            print(f'{i}/{len(payload)} files; {total/1024**3:.2f} GiB', flush=True)
for item in metadata.items():
    copy_verified(item)
report = {'source': str(source), 'target': str(target), 'packages': names, 'version': '6.0.1.0',
          'payload_files': len(payload), 'payload_bytes': total, 'seconds': time.monotonic()-started,
          'verification': 'Every payload with a RECORD digest verified as SHA-256 during copy.',
          'omitted': ['Source-environment bin/isaacsim entry point', 'Generated pyc files']}
args.report.write_text(json.dumps(report, indent=2))
print(json.dumps(report), flush=True)
