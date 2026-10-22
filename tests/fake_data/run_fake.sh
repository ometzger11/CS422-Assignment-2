#!/usr/bin/env bash
# Generate fake data and plot it, to check plots.py works.
set -euo pipefail
cd "$(dirname "$0")"

# Use the repo's venv if it exists, otherwise system python
PY=../../.venv/bin/python
[ -x "$PY" ] || PY=python3

"$PY" gen_fake_data.py
"$PY" ../../plots.py --runs runs.csv --samples samples.csv --out out
echo "Plots written to $(pwd)/out"