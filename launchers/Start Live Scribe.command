#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -f "$SCRIPT_DIR/start_macos.sh" ]; then
    chmod +x "$SCRIPT_DIR/start_macos.sh" 2>/dev/null || true
    exec "$SCRIPT_DIR/start_macos.sh"
fi

if [ -f "$SCRIPT_DIR/launchers/start_macos.sh" ]; then
    chmod +x "$SCRIPT_DIR/launchers/start_macos.sh" 2>/dev/null || true
    exec "$SCRIPT_DIR/launchers/start_macos.sh"
fi

echo "start_macos.sh was not found."
echo "Keep this file beside start_macos.sh or in the Live Scribe project root."
printf "Press Return to close..."
read answer
