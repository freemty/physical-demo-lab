"""Physical task replay plus independent visual-layer isolation/shot evidence."""
import argparse
import hashlib
import json
from itertools import zip_longest
from pathlib import Path
from audit_task import audit


def audit_showcase(folder, baseline=None):
    physical = audit(folder)
    manifest = json.loads((folder/'manifest.json').read_text())
    guard = json.loads((folder/'visual-physics-guard.json').read_text())
    before = json.loads((folder/'visual-physics-before.json').read_text())
    after = json.loads((folder/'visual-physics-after.json').read_text())
    digests = [hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest() for rows in (before, after)]
    isolation = (before == after and guard['before_sha256'] == digests[0] and guard['after_sha256'] == digests[1]
                 and guard['identical_physical_properties'] and guard['added_geometry_collision_free']
                 and manifest['presentation']['physics_signature'] == digests[0])
    events = [json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
    cuts = [e for e in events if e['kind'] == 'camera_cut']
    shots = [e['shot'] for e in cuts] == ['loading', 'travel', 'arrival']
    for e in cuts:
        shots &= all(e[k] == manifest['presentation']['shots'][e['shot']][k] for k in ('eye', 'target', 'focal_mm'))
    expected_phases = {'loading': 'hover', 'travel': 'navigate', 'arrival': 'final_settle'}
    cut_steps = {e['step']: e['shot'] for e in cuts}
    with (folder/'trajectory.jsonl').open() as stream:
        for line in stream:
            frame = json.loads(line)
            if frame['step'] in cut_steps:
                shots &= frame['phase'] == expected_phases[cut_steps[frame['step']]]
    ledger = json.loads((Path(__file__).resolve().parents[1]/'docs/demos.json').read_text())
    fingerprints = next(d['implementation'] for d in ledger['demos'] if d['id'] == 'demo006')
    implementation_same = all(manifest['source_files'].get(name) == digest for name, digest in fingerprints.items())
    comparison = None
    if baseline:
        fields = ('step', 'phase', 'physics_steps', 'sim_time', 'commands', 'robots', 'objects_before_step', 'objects_after_step')
        matched, total = 0, 0
        with (folder/'trajectory.jsonl').open() as a, (baseline/'trajectory.jsonl').open() as b:
            for left, right in zip_longest(a, b):
                total += 1
                if left and right:
                    x, y = json.loads(left), json.loads(right)
                    matched += all(x[k] == y[k] for k in fields)
        comparison = {'reference': str(baseline), 'exactly_matching_frames': matched, 'total_frames': total,
                      'all_physical_fields_exact': matched == total, 'compared_fields': list(fields)}
    return {'success': bool(physical['success'] and isolation and shots and implementation_same), 'physical_audit': physical,
            'physics_rows_identical': bool(isolation), 'physics_signature': digests[0],
            'baseline_implementation_unchanged': implementation_same, 'baseline_trajectory_comparison': comparison,
            'decorative_primitives': guard['decorative_primitive_count'], 'three_shots_verified': bool(shots), 'cuts': cuts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Audit output must be new')
    rows = [audit_showcase(folder, args.baseline) for folder in args.runs]
    result = {'success': all(r['success'] for r in rows), 'passed': sum(r['success'] for r in rows), 'total': len(rows), 'runs': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('success', 'passed', 'total')}))
    return 0 if result['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
