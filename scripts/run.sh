#!/usr/bin/env bash
set -euo pipefail
runtime="${PHYSICAL_DEMO_RUNTIME:-/data0/ybyang/physical-demo-lab-runtime}"
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CACHE_HOME="$runtime/cache/xdg"
export TMPDIR="$runtime/tmp"
export OMNI_KIT_ACCEPT_EULA=YES
export OMNI_KIT_ALLOW_ROOT=0
export PYTHONUNBUFFERED=1
exec "$runtime/venv/bin/python" "$repo_dir/demos/conveyor_sort.py" "$@"
