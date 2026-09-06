"""Portable entry point for the fixed twenty-block Blender-to-Isaac example."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "assets/block_castle/scene_spec.json"
SPEC_SHA256 = "e44fa205d74db0cc9fad91c739100f69dfc4fcb56a8c72b89e2a61c83dfc1910"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_spec(path):
    path = Path(path).resolve()
    if digest(path) != SPEC_SHA256:
        raise ValueError("This quickstart accepts only the verified castle20 blueprint. "
                         "Edited designs need their own controller and physical acceptance.")
    return path


def runtime_path(args):
    return Path(args.runtime).expanduser().resolve()


def runtime_python(args):
    path = runtime_path(args) / "venv/bin/python"
    if not path.is_file():
        raise ValueError(f"No Isaac runtime at {path}. Follow GETTING_STARTED.md.")
    return path


def blender_binary(args):
    name = args.blender
    found = shutil.which(name)
    if not found:
        raise ValueError(f"Blender executable not found: {name}. Set BLENDER_BIN or --blender.")
    return Path(found).resolve()


def doctor(args):
    checks = []
    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
    add("platform", platform.system() == "Linux" and platform.machine() == "x86_64",
        "Full Isaac workflow supports Linux x86_64; Blender-only previews can run elsewhere.")
    py = runtime_path(args) / "venv/bin/python"
    add("runtime_python", py.is_file(), str(py))
    if py.is_file():
        probe = subprocess.run([str(py), "-c",
            "import json,sys; from importlib.metadata import version; "
            "print(json.dumps({'python':list(sys.version_info[:2]),"
            "'isaacsim':version('isaacsim'),'torch':version('torch'),"
            "'imageio':version('imageio'),'imageio-ffmpeg':version('imageio-ffmpeg')}))"],
            capture_output=True, text=True, timeout=30)
        try:
            versions = json.loads(probe.stdout)
            good = (versions["python"] == [3, 12] and versions["isaacsim"] == "6.0.1.0"
                    and versions["torch"] == "2.11.0+cu128")
            add("runtime_versions", good, versions)
        except (ValueError, KeyError):
            add("runtime_versions", False, probe.stderr.strip() or probe.stdout.strip())
    for tool in ["ffmpeg", "ffprobe", "nvidia-smi"]:
        add(tool, shutil.which(tool) is not None, shutil.which(tool) or "not installed")
    try:
        blender = blender_binary(args)
        version = subprocess.check_output([str(blender), "--version"], text=True, timeout=30).splitlines()[0]
        add("blender", version.startswith("Blender 4.5."), version + "; tested family: 4.5 LTS")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        add("blender", False, str(exc))
    if shutil.which("nvidia-smi"):
        gpu = subprocess.run(["nvidia-smi", "-i", str(args.gpu),
            "--query-gpu=index,name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=15)
        add("selected_gpu", gpu.returncode == 0, gpu.stdout.strip() or gpu.stderr.strip())
    report = {"ready": all(x["ok"] for x in checks), "checks": checks,
              "scope": "Preflight only. Does not test asset downloads, RTX startup, free GPU ownership or a completed simulation."}
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


def build(args):
    checked_spec(SPEC)
    blender = blender_binary(args)
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError("Build output must be a new directory.")
    command = [str(blender), "--background", "--factory-startup", "--python-exit-code", "1", "--threads", str(args.threads),
               "--python", str(ROOT / "scripts/castle_blender.py"), "--",
               "--output", str(output), "--spec", str(SPEC)]
    if args.render:
        command += ["--render"]
    subprocess.run(command, check=True)
    subprocess.run([str(blender), "--background", "--python-exit-code", "1", "--threads", str(args.threads),
        str(output / "castle.blend"), "--python", str(ROOT / "scripts/castle_blender.py"),
        "--", "--output", str(output), "--spec", str(output / "scene_spec.json"), "--verify"],
        check=True)
    report = json.loads((output / "blender-audit.json").read_text())
    if report.get("success") is not True or report.get("ir_sha256") != digest(SPEC):
        raise ValueError("Blender audit missing or invalid.")
    print(f"Blender scene and verified physics blueprint: {output}")
    return 0


def run(args):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("This Isaac launcher supports Linux x86_64 only.")
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise ValueError("Read the NVIDIA EULA linked in GETTING_STARTED.md, then set OMNI_KIT_ACCEPT_EULA=YES.")
    design = Path(args.design).resolve()
    ir = checked_spec(design / "scene_spec.json")
    build_audit = json.loads((design / "blender-audit.json").read_text())
    if (build_audit.get("success") is not True or build_audit.get("ir_sha256") != digest(ir)
            or build_audit.get("blend_sha256") != digest(design / "castle.blend")):
        raise ValueError("Blender build audit does not match the design files.")
    py = runtime_python(args)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("ffmpeg and ffprobe must be on PATH.")
    output = Path(args.output).resolve()
    receipt = Path(str(output) + ".entrypoint.json")
    if any(p.exists() for p in [output, receipt, Path(str(output)+".console.log"),
                               Path(str(output)+".process.json"), Path(str(output)+".gpu.jsonl")]):
        raise ValueError("Run and sidecar paths must all be new.")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(py), str(ROOT / "scripts/run_castle_task.py"), "block_castle",
               "--output", str(output), "--gpu", str(args.gpu), "--wall-seconds", str(args.wall_seconds),
               "--mode", args.mode, "--ir", str(ir), "--seed", str(args.seed),
               "--solver", "PGS", "--velocity-iterations", "4", "--parts", "20",
               "--width", "640", "--height", "480", "--max-steps", str(args.max_steps)]
    with receipt.open("x") as stream:
        json.dump({"argv": sys.argv, "command": command, "design": str(design),
                   "ir_sha256": digest(ir), "build_audit_sha256": digest(design/"blender-audit.json"),
                   "entrypoint_sha256": digest(__file__), "scope": "Fixed castle20 quickstart; original physics code unchanged."},
                  stream, indent=2)
    env = dict(os.environ, PHYSICAL_DEMO_RUNTIME=str(runtime_path(args)))
    code = subprocess.run(command, cwd=ROOT, env=env).returncode
    print(f"Run exit: {code}. Evidence retained at {output}; inspect the .process.json sidecar.")
    return code if code >= 0 else 128-code


def audit_run(args):
    output, receipt = Path(args.run).resolve(), Path(args.receipt).resolve()
    physics_receipt = receipt.with_name(receipt.stem + "-physics.json")
    if receipt.exists() or physics_receipt.exists():
        raise ValueError("Both audit receipts must be new paths.")
    py = runtime_python(args)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("ffmpeg and ffprobe must be on PATH.")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    physical = subprocess.run([str(py), str(ROOT/"scripts/audit_castle.py"), str(output),
                               "--receipt", str(physics_receipt)], cwd=ROOT)
    evidence = json.loads(physics_receipt.read_text()) if physics_receipt.exists() else {}
    video = output / "video.mp4"
    decode = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(video),
                             "-map", "0:v:0", "-f", "null", "-"], capture_output=True, text=True)
    success = (physical.returncode == 0 and evidence.get("evidence_consistent") is True
               and evidence.get("complete_robot_assembly") is True and decode.returncode == 0)
    report = {"schema": "castle-quickstart-audit/1", "success": success,
              "run": str(output), "physics_receipt": str(physics_receipt),
              "physics_receipt_sha256": digest(physics_receipt) if physics_receipt.exists() else None,
              "complete_robot_assembly": evidence.get("complete_robot_assembly", False),
              "full_video_decode_returncode": decode.returncode, "decode_stderr": decode.stderr,
              "video_sha256": digest(video) if video.exists() else None,
              "scope": "Physical oracle replay plus full video decode; visual review remains separate."}
    with receipt.open("x") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    return 0 if success else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    default_runtime = os.environ.get("PHYSICAL_DEMO_RUNTIME", str(ROOT/".runtime"))
    def runtime(p):
        p.add_argument("--runtime", default=default_runtime, help="Runtime directory containing venv/bin/python")
    def blender(p):
        p.add_argument("--blender", default=os.environ.get("BLENDER_BIN", "blender"))
    p = sub.add_parser("doctor", help="Read-only environment preflight (no simulation)")
    runtime(p); blender(p); p.add_argument("--gpu", type=int, default=0); p.set_defaults(fn=doctor)
    p = sub.add_parser("build", help="Generate and re-open a Blender scene plus identical physics blueprint")
    blender(p); p.add_argument("--output", required=True)
    p.add_argument("--render", action="store_true", help="Also render goal/loose/exploded design PNGs")
    p.add_argument("--threads", type=int, default=4); p.set_defaults(fn=build)
    p = sub.add_parser("run", help="Import the design blueprint and execute the fixed native controller")
    runtime(p); p.add_argument("--design", required=True); p.add_argument("--output", required=True)
    p.add_argument("--gpu", type=int, default=0); p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mode", choices=["assemble", "goal", "loose"], default="assemble")
    p.add_argument("--max-steps", type=int, default=50000); p.add_argument("--wall-seconds", type=float, default=5400)
    p.set_defaults(fn=run)
    p = sub.add_parser("audit", help="Require complete assembly, oracle consistency and full video decode")
    runtime(p); p.add_argument("--run", required=True); p.add_argument("--receipt", required=True); p.set_defaults(fn=audit_run)
    p = sub.add_parser("export", help="Derive key stages/waypoints from the real control trajectory")
    p.add_argument("--run", required=True); p.add_argument("--output", required=True)
    def export(args):
        from castle_export import export_keyframes
        print(json.dumps(export_keyframes(Path(args.run), Path(args.output)), indent=2))
        return 0
    p.set_defaults(fn=export)
    args = parser.parse_args(argv)
    if getattr(args, "threads", 1) < 1 or getattr(args, "max_steps", 1) < 1 or getattr(args, "wall_seconds", 1) <= 0:
        parser.error("Threads and budgets must be positive.")
    try:
        return args.fn(args)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
