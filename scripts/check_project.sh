#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
bash scripts/check_agent_parity.sh
python3 scripts/check_closeout.py
python3 scripts/check_quickstart.py
python3 -m unittest discover -s tests -v
git diff --check
