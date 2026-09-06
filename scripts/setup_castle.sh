#!/usr/bin/env bash
# Portable, opt-in setup for a new dedicated castle runtime.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
castle_runtime="${PHYSICAL_DEMO_RUNTIME:-$repo_dir/.runtime}"
castle_uv="${UV_BIN:-$(command -v uv || true)}"
if [[ "${OMNI_KIT_ACCEPT_EULA:-}" != YES ]]; then
  echo "Read https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html"
  echo "Then set OMNI_KIT_ACCEPT_EULA=YES to opt in."
  exit 1
fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "This installer supports Linux x86_64 only. See GETTING_STARTED.md for Blender-only use."
  exit 1
fi
if [[ -z "$castle_uv" || ! -x "$castle_uv" ]]; then
  echo "Install uv, or set UV_BIN to its executable path. See GETTING_STARTED.md."
  exit 1
fi
if [[ -e "$castle_runtime/venv" ]]; then
  echo "Runtime already exists; no packages were changed. Run scripts/castle.py doctor."
  exit 0
fi
if [[ "${1:-}" == --check ]]; then
  echo "Setup preconditions passed; no environment created or dependencies downloaded."
  exit 0
fi
if [[ $# -gt 0 ]]; then
  echo "Usage: bash scripts/setup_castle.sh [--check]"
  exit 1
fi
# Reuse the pinned installation recipe with portable paths and the normal PyPI index.
# The script only writes into the explicit dedicated runtime directory.
export PHYSICAL_DEMO_RUNTIME="$castle_runtime"
export UV_BIN="$castle_uv"
export PYTHON_PACKAGE_INDEX="${PYTHON_PACKAGE_INDEX:-https://pypi.org/simple}"
bash "$repo_dir/scripts/setup_server.sh"
echo "Runtime installed. Install Blender 4.5 and ffmpeg separately, then run scripts/castle.py doctor."
