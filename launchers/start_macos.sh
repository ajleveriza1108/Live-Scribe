#!/usr/bin/env sh
set -eu

# ==============================================================
# Live Scribe launcher for macOS
# Works with:
#   - Source project: .venv/bin/python + app.py
#   - Portable app: Live Scribe.app
#   - Portable folder: LiveScribe/LiveScribe
# ==============================================================

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_ROOT="$SCRIPT_DIR"

# In the source project this file is stored inside "launchers".
if [ -f "$SCRIPT_DIR/../app.py" ]; then
    APP_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
fi

cd "$APP_ROOT"
export LIVE_SCRIBE_HOME="$APP_ROOT"

APP_BUNDLE_EXEC="$APP_ROOT/Live Scribe.app/Contents/MacOS/LiveScribe"
PORTABLE_APP="$APP_ROOT/LiveScribe/LiveScribe"
ROOT_APP="$APP_ROOT/LiveScribe"
VENV_PYTHON="$APP_ROOT/.venv/bin/python"
SOURCE_APP="$APP_ROOT/app.py"

make_executable() {
    target="$1"
    if [ -f "$target" ] && [ ! -x "$target" ]; then
        chmod +x "$target" 2>/dev/null || true
    fi
}

make_executable "$APP_BUNDLE_EXEC"
make_executable "$PORTABLE_APP"
make_executable "$ROOT_APP"

printf '\nStarting Live Scribe...\n\n'

if [ -x "$APP_BUNDLE_EXEC" ]; then
    exec "$APP_BUNDLE_EXEC"
fi

if [ -x "$PORTABLE_APP" ]; then
    exec "$PORTABLE_APP"
fi

if [ -f "$ROOT_APP" ] && [ -x "$ROOT_APP" ]; then
    exec "$ROOT_APP"
fi

if [ -x "$VENV_PYTHON" ] && [ -f "$SOURCE_APP" ]; then
    exec "$VENV_PYTHON" "$SOURCE_APP"
fi

printf '%s\n' \
    "Live Scribe could not be started." \
    "" \
    "For source development, run:" \
    "  chmod +x scripts/dev_setup_unix.sh" \
    "  ./scripts/dev_setup_unix.sh" \
    "" \
    "Then run:" \
    "  ./launchers/start_macos.sh"

exit 1
