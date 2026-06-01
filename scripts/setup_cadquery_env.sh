#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${1:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

"${PYTHON_BIN}" -m venv "${ENV_DIR}"
# shellcheck disable=SC1091
source "${ENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install "cadquery==2.7.0"
python "$(dirname "$0")/verify_cadquery.py"
