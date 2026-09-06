"""Read-only checks for the portable guides and bundled castle example."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check():
    errors = []
    example = ROOT / "examples/castle20"
    provenance = json.loads((example/"provenance.json").read_text())
    for item in provenance["files"]:
        path = (ROOT/item["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != item["sha256"]:
            errors.append("example hash mismatch: "+item["path"])
    if sha(example/"scene_spec.json") != sha(ROOT/"assets/block_castle/scene_spec.json"):
        errors.append("bundled blueprint differs from accepted blueprint")
    audit = json.loads((example/"blender-audit.json").read_text())
    if (audit.get("success") is not True or audit["blend_sha256"] != sha(example/"castle.blend")
            or audit["ir_sha256"] != sha(example/"scene_spec.json")):
        errors.append("bundled Blender audit does not bind the files")
    export = json.loads((example/"trajectory/export-manifest.json").read_text())
    keyframes = json.loads((example/"trajectory/keyframes.json").read_text())
    for name, expected in export["derived_hashes"].items():
        if sha(example/"trajectory"/name) != expected:
            errors.append("derived export hash mismatch: "+name)
    if len(keyframes["segments"]) != export["phase_count"]:
        errors.append("export phase count mismatch")
    if len(keyframes.get("robot_dof_names") or []) != 9:
        errors.append("missing native nine-DOF order")
    with (example/"trajectory/waypoints.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != export["phase_count"] or "measured_joint_positions" not in rows[0]:
        errors.append("CSV count or mixed-unit field mismatch")
    native = json.loads((ROOT/"reports/demo009-seed0-audit.json").read_text())
    if (native["complete_robot_assembly"] is not True or
            native["control_samples"] != export["control_samples"] or len(export["completed_parts"]) != 20):
        errors.append("sample differs from referenced native acceptance")
    documents = ["README.md", "GETTING_STARTED.md", "docs/README.md", "docs/TODO.md",
        "docs/guides/getting-started.zh-CN.md", "docs/guides/castle-outputs.md",
        "examples/castle20/README.md", "examples/castle20/trajectory/README.md",
        "reports/castle-quickstart.md", "docs/knowhow/toolchain/castle-quickstart-boundaries.md"]
    links = 0
    for name in documents:
        path = ROOT/name
        text = path.read_text()
        targets = re.findall(r"\]\(([^)]+)\)", text) + re.findall(r'(?:href|src)="([^"]+)"', text)
        for target in targets:
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#")[0]
            if not (path.parent/target).exists():
                errors.append("broken local link: "+name+" -> "+target)
            links += 1
        for block in re.findall(r"```bash\n(.*?)```", text, re.S):
            result = subprocess.run(["bash","-n"],input=block,text=True,capture_output=True)
            if result.returncode:
                errors.append("invalid shell example in "+name+": "+result.stderr)
    return {"success":not errors,"errors":errors,"bundled_files":len(provenance["files"]),
            "checked_documents":len(documents),"checked_local_links":links,
            "scope":"File hashes, sparse sample consistency, local links and shell syntax; no simulation or external URL check."}


if __name__ == "__main__":
    report = check()
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["success"] else 1)
