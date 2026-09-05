"""Read-only development diagnostics; this is not a success verifier."""
import argparse
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('folder', type=Path)
args = parser.parse_args()
manifest = json.loads((args.folder/'manifest.json').read_text())
links = manifest.get('contact_links', [])
samples = []
with (args.folder/'trajectory.jsonl').open() as stream:
    for line in stream:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row['step'] % 120:
            continue
        command = row['commands'][0]
        contacts = {name.split('/')[-1]: math.sqrt(sum(v*v for v in force[0]))
                    for name, force in zip(links, command.get('finger_contact_forces', []))
                    if sum(v*v for v in force[0]) > .0001}
        samples.append({'step': row['step'], 'phase': row['phase'], 'angle': command['cap_angle'],
                        'z': row['objects_before_step'][0]['position'][2],
                        'wrist': row['robots'][0]['hand_position'], 'contacts_N': contacts})
print(json.dumps(samples, indent=2))
