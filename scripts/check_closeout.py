"""Read-only completion gate: evidence, lessons, limitations and source freshness.

This checks record completeness, not the truth of prose or physical success.
Those still require the demo's verifier and an evidence-grounded review.
"""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path


def validate(root, ledger, required_demo=None):
    root = Path(root).resolve()
    errors, seen = [], set()
    if not isinstance(ledger, dict) or ledger.get('schema_version') != 1:
        return ['Unsupported or missing schema_version']
    demos = ledger.get('demos')
    if not isinstance(demos, list) or not demos:
        return ['demos must be a nonempty list']

    def local_file(value, label):
        if not isinstance(value, str) or not value:
            errors.append(f'{label}: missing relative file path')
            return None
        path = (root/value).resolve()
        if Path(value).is_absolute() or not path.is_relative_to(root):
            errors.append(f'{label}: path must stay inside the repository')
            return None
        if not path.is_file() or not path.stat().st_size:
            errors.append(f'{label}: missing or empty file: {value}')
            return None
        return path

    for demo in demos:
        if not isinstance(demo, dict):
            errors.append('Each demo must be an object')
            continue
        key = demo.get('id')
        if not isinstance(key, str) or not key:
            errors.append('Each demo needs a nonempty id')
            continue
        if key in seen:
            errors.append(f'{key}: duplicate id')
        seen.add(key)
        if not isinstance(demo.get('title'), str) or not demo['title'].strip():
            errors.append(f'{key}: missing title')
        status = demo.get('status')
        if status not in ('planned', 'in_progress', 'blocked', 'complete'):
            errors.append(f'{key}: invalid status')
        if status != 'complete':
            if key == required_demo:
                errors.append(f'{key}: not complete ({status})')
            continue
        if not isinstance(demo.get('scope'), str) or not demo['scope'].strip():
            errors.append(f'{key}: missing verified scope')
        try:
            date.fromisoformat(demo.get('verified_at', ''))
        except (ValueError, TypeError):
            errors.append(f'{key}: verified_at must be an ISO date')
        limits = demo.get('limitations')
        if not isinstance(limits, list) or not limits or not all(isinstance(x, str) and x.strip() for x in limits):
            errors.append(f'{key}: explicit limitations required')
        local_file(demo.get('report'), f'{key}.report')
        for field in ('lessons', 'evidence'):
            values = demo.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f'{key}: {field} required before completion')
                continue
            for value in values:
                local_file(value, f'{key}.{field}')
        implementation = demo.get('implementation')
        if not isinstance(implementation, dict) or not implementation:
            errors.append(f'{key}: implementation fingerprints required')
            continue
        for name, expected in implementation.items():
            path = local_file(name, f'{key}.implementation')
            if path and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f'{key}: stale closeout for {name}; reverify and update the docs before closing')
    if required_demo and required_demo not in seen:
        errors.append(f'Unknown demo: {required_demo}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--demo', help='Require this specific demo to be complete')
    args = parser.parse_args()
    try:
        ledger = json.loads((args.root/'docs/demos.json').read_text())
        errors = validate(args.root, ledger, args.demo)
    except (OSError, ValueError) as error:
        ledger, errors = {}, [str(error)]
    entries = ledger.get('demos', []) if isinstance(ledger, dict) else []
    entries = entries if isinstance(entries, list) else []
    print(json.dumps({'success': not errors,
                      'completed': [d['id'] for d in entries
                                    if isinstance(d, dict) and d.get('status') == 'complete' and 'id' in d],
                      'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
