#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export LIVE_SCRIBE_HOME="$SCRIPT_DIR"

APP="$SCRIPT_DIR/LiveScribe/LiveScribe"
if [ ! -x "$APP" ]; then
  echo "The portable application files are incomplete or not executable."
  echo "Extract the complete package, then run: chmod +x start_linux.sh LiveScribe/LiveScribe"
  exit 1
fi

exec "$APP"
