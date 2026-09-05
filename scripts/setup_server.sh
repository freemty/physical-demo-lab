#!/usr/bin/env bash
# Isolated Isaac Sim runtime. Never installs into an existing training environment.
set -euo pipefail
runtime="${PHYSICAL_DEMO_RUNTIME:-/data0/ybyang/physical-demo-lab-runtime}"
uv_bin="${UV_BIN:-/home/ybyang/.local/bin/uv}"
mkdir -p "$runtime"/{cache/uv,cache/xdg,cache/pip,python,tmp,logs,outputs}
export UV_CACHE_DIR="$runtime/cache/uv"
export UV_PYTHON_INSTALL_DIR="$runtime/python"
export XDG_CACHE_HOME="$runtime/cache/xdg"
export PIP_CACHE_DIR="$runtime/cache/pip"
export TMPDIR="$runtime/tmp"
export UV_HTTP_TIMEOUT=600
export UV_LINK_MODE=copy
"$uv_bin" venv --python 3.12 "$runtime/venv"
"$uv_bin" pip install --python "$runtime/venv/bin/python" \
  'torch==2.11.0' --index-url https://download.pytorch.org/whl/cu128
"$uv_bin" pip install --python "$runtime/venv/bin/python" \
  'isaacsim[all,extscache]==6.0.1.0' \
  --extra-index-url https://pypi.nvidia.com --index-strategy unsafe-best-match
"$uv_bin" pip install --python "$runtime/venv/bin/python" imageio imageio-ffmpeg pytest
"$uv_bin" pip freeze --python "$runtime/venv/bin/python" > "$runtime/packages.freeze.txt"
"$runtime/venv/bin/python" -c 'import sys; from importlib.metadata import version; print(sys.version); print("Isaac Sim", version("isaacsim")); print("PyTorch", version("torch"))'
