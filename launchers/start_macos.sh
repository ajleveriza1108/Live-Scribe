#!/usr/bin/env sh
set -eu

# ==============================================================
# Live Scribe launcher for macOS
# Supports:
#   1. Portable app:   Live Scribe.app
#   2. Portable build: LiveScribe/LiveScribe
#   3. Portable build: LiveScribe
#   4. Source build:   .venv/bin/python app.py
# ==============================================================

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_ROOT="$SCRIPT_DIR"

# Also support this launcher inside a launchers subfolder.
if [ ! -f "$APP_ROOT/app.py" ] && [ -f "$SCRIPT_DIR/../app.py" ]; then
    APP_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
fi

cd "$APP_ROOT"
export LIVE_SCRIBE_HOME="$APP_ROOT"

APP_BUNDLE_EXECUTABLE="$APP_ROOT/Live Scribe.app/Contents/MacOS/LiveScribe"
PORTABLE_APP="$APP_ROOT/LiveScribe/LiveScribe"
ROOT_APP="$APP_ROOT/LiveScribe"
VENV_PYTHON="$APP_ROOT/.venv/bin/python"
SOURCE_APP="$APP_ROOT/app.py"

make_executable_if_possible() {
    target="$1"
    if [ -f "$target" ] && [ ! -x "$target" ]; then
        chmod +x "$target" 2>/dev/null || true
    fi
}

make_executable_if_possible "$APP_BUNDLE_EXECUTABLE"
make_executable_if_possible "$PORTABLE_APP"
make_executable_if_possible "$ROOT_APP"

printf '\nStarting Live Scribe...\n\n'

if [ -x "$APP_BUNDLE_EXECUTABLE" ]; then
    exec "$APP_BUNDLE_EXECUTABLE"
fi

if [ -x "$PORTABLE_APP" ]; then
    exec "$PORTABLE_APP"
fi

if [ -x "$ROOT_APP" ] && [ ! -d "$ROOT_APP" ]; then
    exec "$ROOT_APP"
fi

if [ -x "$VENV_PYTHON" ] && [ -f "$SOURCE_APP" ]; then
    exec "$VENV_PYTHON" "$SOURCE_APP"
fi

printf '%s\n' \
    "Live Scribe could not be started." \
    "" \
    "No portable application or prepared Python environment was found." \
    "" \
    "For the source version, first run:" \
    "  chmod +x scripts/dev_setup_unix.sh" \
    "  ./scripts/dev_setup_unix.sh" \
    "" \
    "Then run this launcher again."

exit 1
