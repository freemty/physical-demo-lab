#!/usr/bin/env bash
set -euo pipefail
runtime="${PHYSICAL_DEMO_RUNTIME:-/data1/ybyang/physical-demo-lab-runtime}"
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export XDG_CACHE_HOME="$runtime/cache/xdg"
export TMPDIR="$runtime/tmp"
export OMNI_KIT_ACCEPT_EULA=YES
export OMNI_KIT_ALLOW_ROOT=0
export PYTHONUNBUFFERED=1
run_args=("$@")
output_dir=''
while (($#)); do
  case "$1" in
    --output) output_dir="${2:?--output needs a path}"; shift 2 ;;
    --output=*) output_dir="${1#--output=}"; shift ;;
    *) shift ;;
  esac
done
if [[ -z "$output_dir" || -e "$output_dir" || -e "$output_dir.console.log" ]]; then
  echo 'Provide --output pointing to a new directory; existing outputs/logs are never overwritten.' >&2
  exit 1
fi
mkdir -p "$(dirname -- "$output_dir")"
{
  printf 'Command:'
  printf ' %q' "$runtime/venv/bin/python" "$repo_dir/demos/conveyor_sort.py" "${run_args[@]}"
  printf '\n'
  date --iso-8601=seconds
  nvidia-smi --query-gpu=index,uuid,name,memory.used,utilization.gpu,driver_version --format=csv
  "$runtime/venv/bin/python" "$repo_dir/demos/conveyor_sort.py" "${run_args[@]}"
} 2>&1 | tee "$output_dir.console.log"
