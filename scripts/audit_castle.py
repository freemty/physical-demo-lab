"""Replay the independent oracle over recorded PhysX evidence, not the controller."""
import argparse
import gzip
import hashlib
import importlib.util
import math
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'demos'))
class LiftEvidence:
    def __init__(self, names):
        self.names = set(names)
        self.initial_z = {}
        self.stats = {n: {'peak_lift_m': 0., 'bilateral_above_80mm_samples': 0} for n in names}

    def update(self, states, contacts):
        ids = [s['id'] for s in states]
        if len(ids) != len(set(ids)) or set(ids) != self.names:
            raise ValueError('Object identity changed in physical trajectory')
        for s in states:
            values = s['position']+s['orientation']+s['linear_velocity']+s['angular_velocity']
            if not all(math.isfinite(v) for v in values):
                raise ValueError('Non-finite object state')
            name = s['id']
            self.initial_z.setdefault(name, s['position'][2])
            lift = s['position'][2] - self.initial_z[name]
            self.stats[name]['peak_lift_m'] = max(self.stats[name]['peak_lift_m'], lift)
            fingers = {c['other'] for c in contacts if c['body']==name
                       and c['other'].startswith('robot:') and 'finger' in c['other']
                       # Native recorded normal scalars may be negative; load uses magnitude.
                       and math.isfinite(c.get('normal_force',0.))
                       and abs(c.get('normal_force',0.)) > 1e-6}
            if lift >= .08 and len(fingers) >= 2:
                self.stats[name]['bilateral_above_80mm_samples'] += 1

    def verified_names(self):
        return {n for n,s in self.stats.items() if s['bilateral_above_80mm_samples'] > 0}



def audit(output):
    output = Path(output)
    manifest = json.loads((output/'manifest.json').read_text())
    result = json.loads((output/'result.json').read_text())
    status = json.loads(Path(str(output)+'.process.json').read_text())
    errors = []
    for name,expected in manifest['source_files'].items():
        source = output/'source'/name
        if not source.exists() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            errors.append('source_snapshot_mismatch:'+name)
    if hashlib.sha256((output/'source-ir.json').read_bytes()).hexdigest() != manifest['ir_sha256']:
        errors.append('source_ir_mismatch')
    spec = json.loads((output/'source-ir.json').read_text())
    verifier_path = output/'source/demos/castle_verify.py'
    expected_verifier = manifest['source_files'].get('demos/castle_verify.py')
    if hashlib.sha256(verifier_path.read_bytes()).hexdigest() != expected_verifier:
        raise ValueError('Cannot replay an unverified verifier snapshot')
    module_spec = importlib.util.spec_from_file_location('retained_castle_oracle', verifier_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    oracle = module.StableOracle(spec)
    lift_evidence = LiftEvidence([b['name'] for b in spec['objects'] if b.get('free')])
    count,previous,max_penetration,arm_contacts = 0,None,0.,0
    final,final_states = None,None
    with gzip.open(output/'physics-steps.jsonl.gz','rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row['physics_step'] != count:
                errors.append('physics_step_discontinuity')
            if previous is not None and abs(row['sim_time']-previous-manifest['physics_dt']) > 1e-8:
                errors.append('physics_time_discontinuity')
            previous = row['sim_time']
            final_states = row['objects']
            lift_evidence.update(final_states, row['contacts'])
            final = oracle.update(previous,final_states,row['contacts'])
            for c in row['contacts']:
                max_penetration = max(max_penetration,-c['min_distance'])
                if c['other'].startswith('robot:') and 'finger' not in c['other'] and c['min_distance'] <= 0:
                    arm_contacts += 1
            count += 1
    trajectory_count,commanded_parts = 0,set()
    with (output/'trajectory.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['step'] != trajectory_count or row['physics_steps'] != 4*(trajectory_count+1):
                errors.append('control_step_discontinuity')
            phase = row['phase']
            if phase.endswith(':lift'):
                commanded_parts.add(phase.split(':')[0])
            trajectory_count += 1
    if count != 4*trajectory_count or result['physics_steps'] != trajectory_count:
        errors.append('trace_length_mismatch')
    if abs(max_penetration-result['max_penetration_m']) > 1e-9 or arm_contacts != result['arm_contact_samples']:
        errors.append('contact_aggregate_mismatch')
    if final is None or final['success'] != result['verification']['success']:
        errors.append('oracle_result_mismatch')
    expected_code = 0 if result['success'] else 2
    if status['returncode'] != expected_code:
        errors.append('exit_code_mismatch')
    video = None
    if result['video_frames']:
        command = ['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries',
                   'stream=width,height,nb_read_frames,r_frame_rate,duration','-of','json',str(output/'video.mp4')]
        video = json.loads(subprocess.check_output(command,text=True))['streams'][0]
        if int(video['nb_read_frames']) != result['video_frames']:
            errors.append('video_frame_count_mismatch')
        if abs(float(video['duration'])-result['sim_seconds']) > .04:
            errors.append('video_time_mismatch')
    completed = result.get('completed_parts',[])
    verified_lifts = lift_evidence.verified_names()
    if result['mode']=='assemble' and result['success']:
        if len(completed)!=20 or set(completed)!=lift_evidence.names or len(commanded_parts)!=20:
            errors.append('missing_complete_assembly_history')
        if verified_lifts != lift_evidence.names:
            errors.append('missing_native_bilateral_lift_evidence')
        if video is None:
            errors.append('missing_required_video')
    if status.get('resource_monitor',{}).get('termination_reason'):
        errors.append('resource_monitor_failure')
    complete_assembly = (result['mode']=='assemble' and result['success'] and final['success']
                         and len(commanded_parts)==20 and len(completed)==20
                         and verified_lifts==lift_evidence.names and not errors)
    return {'evidence_consistent':not errors,'errors':sorted(set(errors)), 'output':str(output),
            'mode':result['mode'],'task_success':result['success'],'complete_robot_assembly':complete_assembly,
            'native_lift_evidence':lift_evidence.stats, 'verified_lift_count':len(verified_lifts),
            'verifier_snapshot_sha256':expected_verifier,
            'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'physics_samples':count,'control_samples':trajectory_count,'sim_seconds':previous,
            'replayed_stable_seconds':None if final is None else final['stable_seconds'],
            'max_penetration_m':max_penetration,'arm_contact_samples':arm_contacts,
            'process_returncode':status['returncode'],'video':video,
            'replay_scope':'Recomputed oracle from logged physical states and contacts, not action re-execution.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    parser.add_argument('--receipt',type=Path)
    args = parser.parse_args()
    receipt = audit(args.output)
    if args.receipt:
        with args.receipt.open('x') as stream:
            json.dump(receipt,stream,indent=2)
    print(json.dumps(receipt,indent=2))
    raise SystemExit(0 if receipt['evidence_consistent'] else 1)
