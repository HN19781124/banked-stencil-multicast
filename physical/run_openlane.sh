#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python3 tools/prepare_physical.py
python3 -m openlane --docker-no-tty --dockerized --condensed \
  --hide-progress-bar --run-tag sky130-feasibility physical/config.json
