#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
  sh scripts/dev_setup_unix.sh
fi

.venv/bin/python scripts/build_portable.py
