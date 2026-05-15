#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ -x ".venv/bin/python" ]; then
  exec ".venv/bin/python" start.py "$@"
fi

exec python3 start.py "$@"
