#!/usr/bin/env sh
set -eu
PLATFORM="linux"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_ROOT="$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/../app.py" ]; then
    APP_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
fi

cd "$APP_ROOT"
export LIVE_SCRIBE_HOME="$APP_ROOT"
LS_CACHE="$APP_ROOT/.cache"

mkdir -p \
    "$LS_CACHE/temp" \
    "$LS_CACHE/huggingface/hub" \
    "$LS_CACHE/huggingface/xet" \
    "$LS_CACHE/huggingface/assets" \
    "$LS_CACHE/xdg/cache" \
    "$LS_CACHE/xdg/config" \
    "$LS_CACHE/xdg/data" \
    "$LS_CACHE/pycache"

export HF_HOME="$LS_CACHE/huggingface"
export HF_HUB_CACHE="$LS_CACHE/huggingface/hub"
export HF_XET_CACHE="$LS_CACHE/huggingface/xet"
export HF_ASSETS_CACHE="$LS_CACHE/huggingface/assets"
export XDG_CACHE_HOME="$LS_CACHE/xdg/cache"
export XDG_CONFIG_HOME="$LS_CACHE/xdg/config"
export XDG_DATA_HOME="$LS_CACHE/xdg/data"
export TMP="$LS_CACHE/temp"
export TEMP="$LS_CACHE/temp"
export TMPDIR="$LS_CACHE/temp"
export PYTHONPYCACHEPREFIX="$LS_CACHE/pycache"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

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

printf '\nStarting Live Scribe in portable mode...\n'
printf 'App folder: %s\n\n' "$APP_ROOT"

if [ "$PLATFORM" = "macos" ] && [ -x "$APP_BUNDLE_EXEC" ]; then
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
    "Keep the complete portable folder together. Do not copy only the executable." \
    "For source development, run scripts/dev_setup_unix.sh first."

exit 1
