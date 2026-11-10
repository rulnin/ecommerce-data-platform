#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python_path="$(command -v python3.14)"
"$python_path" -c 'import sys; assert sys.version_info[:3] == (3, 14, 4), sys.version'
# --allow-existing repairs the previous partial venv without deleting its files.
uv venv --python "$python_path" --no-python-downloads --seed --allow-existing .venv
source .venv/bin/activate
python --version
python -m pip --version
python -c 'import sys; assert sys.prefix != sys.base_prefix; print(sys.prefix, sys.base_prefix)'
