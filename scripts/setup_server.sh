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
export UV_HTTP_TIMEOUT=90
export UV_LINK_MODE=copy
package_index="${PYTHON_PACKAGE_INDEX:-https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple}"
if [[ ! -x "$runtime/venv/bin/python" ]]; then
  "$uv_bin" venv --python 3.12 "$runtime/venv"
fi
# Pin the official torch wheel directly; resolve CUDA dependencies from a PyPI mirror.
# The PyTorch index redirects CUDA wheel metadata to a server without HTTP Range
# support, forcing a full cuDNN download just to resolve dependencies.
torch_wheel='https://download.pytorch.org/whl/cu128/torch-2.11.0%2Bcu128-cp312-cp312-manylinux_2_28_x86_64.whl#sha256=d252cf975fb18c94a85336323ad425f473df56dab35a44b00399bd70c7a3b997'
"$uv_bin" pip install --python "$runtime/venv/bin/python" \
  "$torch_wheel" --index-url "$package_index"
"$uv_bin" pip install --python "$runtime/venv/bin/python" \
  'isaacsim[all,extscache]==6.0.1.0' \
  --index-url "$package_index" --extra-index-url https://pypi.nvidia.com --index-strategy unsafe-best-match
"$uv_bin" pip install --python "$runtime/venv/bin/python" imageio imageio-ffmpeg pytest --index-url "$package_index"
"$uv_bin" pip freeze --python "$runtime/venv/bin/python" > "$runtime/packages.freeze.txt"
"$runtime/venv/bin/python" -c 'import sys; from importlib.metadata import version; print(sys.version); print("Isaac Sim", version("isaacsim")); print("PyTorch", version("torch"))'
