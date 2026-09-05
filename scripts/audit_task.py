"""Independent source/trajectory/process audit with per-task semantic replay."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'demos'))
from checkout_verify import verify_checkout
from gear_verify import verify_gear


def audit(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    result = json.loads((folder/'result.json').read_text())
    process = json.loads(Path(str(folder)+'.process.json').read_text())
    source_valid = all(hashlib.sha256((folder/'source'/name).read_bytes()).hexdigest() == digest
                       for name, digest in manifest['source_files'].items())
    continuous, count, final_frame = True, 0, None
    observed_scans, dwell = [], {o['id']: 0 for o in manifest['objects']}
    inventory = {o['id']: o for o in manifest['objects']}
    max_lift = {o['id']: 0. for o in manifest['objects']}
    transported = {o['id']: 0. for o in manifest['objects']}
    events = [json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
    active, event_idx = 0, 0
    with (folder/'trajectory.jsonl').open() as stream:
        for line in stream:
            frame = json.loads(line)
            while event_idx < len(events) and events[event_idx]['step'] <= count:
                if events[event_idx]['kind'] == 'phase':
                    active = events[event_idx]['active_object']
                event_idx += 1
            continuous &= frame['step'] == count and frame['physics_steps'] == count+1
            continuous &= math.isclose(frame['sim_time'], (count+1)*manifest['physics_dt'], abs_tol=1e-7)
            for obj in frame['objects_before_step'] + frame['objects_after_step']:
                max_lift[obj['id']] = max(max_lift[obj['id']], obj['position'][2]-inventory[obj['id']]['initial_position'][2])
            if manifest['task'] == 'supermarket_checkout':
                scanner = manifest['scanner']
                for idx, obj in enumerate(frame['objects_before_step']):
                    inside = all(scanner['lower'][i] <= obj['position'][i] <= scanner['upper'][i] for i in range(3))
                    dwell[obj['id']] = dwell[obj['id']]+1 if inside else 0
                    if dwell[obj['id']] == scanner['dwell_frames'] and obj['id'] not in [s['id'] for s in observed_scans]:
                        observed_scans.append({'id': obj['id'], 'price_cents': inventory[obj['id']]['price_cents'],
                            'step': count, 'position': obj['position'], 'dwell_frames': dwell[obj['id']], 'inside_volume': True})
                    if idx == active and frame['phase'] in ('feed', 'settle'):
                        transported[obj['id']] = max(transported[obj['id']], obj['position'][0]-inventory[obj['id']]['initial_position'][0])
            count += 1
            final_frame = frame
    continuous &= count == result['physics_steps']
    semantic = False
    if manifest['task'] == 'supermarket_checkout' and final_frame:
        states = []
        last_robot = final_frame['robots'][0]
        for obj in final_frame['objects_after_step']:
            state = dict(obj)
            source = inventory[obj['id']]
            distance = sum((a-b)**2 for a, b in zip(state['position'], last_robot['hand_position'][0]))**.5
            state.update(color='bag', size=source['size'], max_lift=max_lift[obj['id']],
                         belt_displacement=transported[obj['id']],
                         released_and_retracted=min(last_robot['joints'][0][-2:]) > .03 and distance > .15)
            states.append(state)
        verification = verify_checkout(states, manifest['bag'], manifest['objects'], observed_scans)
        semantic = verification['success'] and observed_scans == result['receipt']['lines']
        semantic &= result['receipt']['total_cents'] == sum(o['price_cents'] for o in manifest['objects'])
    elif manifest['task'] == 'gear_assembly' and final_frame:
        state = dict(final_frame['objects_after_step'][0])
        robot = final_frame['robots'][0]
        distance = sum((a-b)**2 for a, b in zip(state['position'], robot['hand_position'][0]))**.5
        state.update(max_lift=max_lift[state['id']],
                     released_and_retracted=min(robot['joints'][0][-2:]) > .03 and distance > .15)
        verification = verify_gear(state, manifest['target'])
        semantic = verification['success'] and verification['checks'] == result['verification']['checks']
    else:
        verification = {'success': False, 'reason': 'No independent semantic auditor for this task yet'}
    success = (source_valid and continuous and semantic and result['success']
               and result['phase'] == 'done' and result['abort_reason'] is None and process['returncode'] == 0)
    return {'success': bool(success), 'task': manifest['task'], 'seed': manifest['seed'], 'output': str(folder),
            'source_snapshot_verified': source_valid, 'trajectory_continuous': bool(continuous),
            'semantic_replay_verified': bool(semantic), 'process_returncode': process['returncode'],
            'frames': count, 'sim_seconds': result['sim_seconds'], 'verification': verification,
            'source_files': manifest['source_files']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Audit output must be new')
    rows = [audit(folder) for folder in args.runs]
    result = {'success': all(r['success'] for r in rows), 'passed': sum(r['success'] for r in rows),
              'total': len(rows), 'runs': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('success', 'passed', 'total')}))
    return 0 if result['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
