"""One isolated native castle run; retain process, resource and failure receipts."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["block_castle"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--wall-seconds", type=float, default=3600.)
    args, remaining = parser.parse_known_args()
    root = Path(__file__).resolve().parents[1]
    runtime = Path(os.environ.get("PHYSICAL_DEMO_RUNTIME", "/data1/ybyang/physical-demo-lab-runtime"))
    console = Path(str(args.output)+".console.log")
    status_path = Path(str(args.output)+".process.json")
    gpu_path = Path(str(args.output)+".gpu.jsonl")
    if any(p.exists() for p in [args.output, console, status_path, gpu_path]):
        parser.error("All output paths must be new.")
    uuid = subprocess.check_output(["nvidia-smi","-i",str(args.gpu),"--query-gpu=uuid","--format=csv,noheader"], text=True,timeout=10).strip()
    def contexts():
        rows = subprocess.check_output(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],text=True,timeout=10)
        return [(u.strip(),int(p.strip())) for u,p in (r.split(",") for r in rows.splitlines() if r.strip())]
    if any(u == uuid for u,p in contexts()):
        parser.error("Selected GPU already has compute users; do not stop them.")
    env = dict(os.environ)
    for key,rel in [("XDG_CACHE_HOME","cache/xdg"),("CUDA_CACHE_PATH","cache/cuda"),("__GL_SHADER_DISK_CACHE_PATH","cache/gl"),("TMPDIR","tmp")]:
        env[key] = str(runtime/rel)
    env.update(OMNI_KIT_ACCEPT_EULA="YES",PYTHONUNBUFFERED="1",CUDA_VISIBLE_DEVICES=uuid,CUDA_DEVICE_ORDER="PCI_BUS_ID")
    command = [str(runtime/"venv/bin/python"),str(root/"demos/block_castle.py"),"--output",str(args.output),"--gpu",str(args.gpu),*remaining]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    state = {"termination_reason":None,"samples":0,"owned_pids":[]}
    stop = threading.Event()
    with console.open("x") as stream, gpu_path.open("x") as gpu_stream:
        stream.write(json.dumps({"command":command,"started_at":started,"gpu_uuid":uuid})+"\n")
        stream.flush()
        process = subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,text=True,start_new_session=True)
        def monitor():
            seen = {process.pid}
            term_at = None
            while not stop.is_set():
                try:
                    # Group membership, not process names; no unrelated process may be killed.
                    ps = subprocess.check_output(["ps","-eo","pid=,pgid="],text=True,timeout=10)
                    owned = {int(p) for p,g in (r.split() for r in ps.splitlines()) if int(g)==process.pid}
                    seen.update(owned)
                    active = contexts()
                    own_active = [{"uuid":u,"pid":p} for u,p in active if p in owned]
                    state["samples"] += 1
                    state["owned_pids"] = sorted(seen)
                    gpu_stream.write(json.dumps({"elapsed":time.monotonic()-start,"owned":sorted(owned),"contexts":own_active})+"\n")
                    gpu_stream.flush()
                    reason = "off_target_gpu" if any(x["uuid"] != uuid for x in own_active) else None
                    if time.monotonic()-start > args.wall_seconds:
                        reason = "wall_budget"
                    if reason and state["termination_reason"] is None:
                        state["termination_reason"] = reason
                except Exception as error:
                    state["termination_reason"] = state["termination_reason"] or ("monitor_error:"+repr(error))
                if state["termination_reason"] and process.poll() is None:
                    try:
                        os.killpg(process.pid,signal.SIGTERM if term_at is None else
                                  (signal.SIGKILL if time.monotonic()-term_at > 10 else signal.SIGTERM))
                        term_at = time.monotonic() if term_at is None else term_at
                    except ProcessLookupError:
                        pass
                stop.wait(.5)
        thread = threading.Thread(target=monitor,daemon=True)
        thread.start()
        try:
            for line in process.stdout:
                stream.write(line)
                stream.flush()
                print(line,end="",flush=True)
            code = process.wait()
        except BaseException:
            os.killpg(process.pid,signal.SIGTERM)
            try:
                code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                code = process.wait()
            raise
        finally:
            stop.set()
            thread.join(timeout=25)
            if process.poll() is not None:
                status_path.write_text(json.dumps({"command":command,"returncode":process.returncode,
                    "started_at":started,"ended_at":datetime.now(timezone.utc).isoformat(),
                    "wall_seconds":time.monotonic()-start,"console":str(console),"output":str(args.output),
                    "gpu_uuid":uuid,"resource_monitor":state,
                    "scope":"Sampled own process group CUDA contexts; no universal escaped-descendant coverage."},indent=2))
    return 1 if state["termination_reason"] else (code if code>=0 else 128-code)


if __name__ == "__main__":
    raise SystemExit(main())
