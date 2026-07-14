#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export LIVE_SCRIBE_HOME="$SCRIPT_DIR"

APP_BUNDLE="$SCRIPT_DIR/Live Scribe.app/Contents/MacOS/LiveScribe"
APP_FOLDER="$SCRIPT_DIR/LiveScribe/LiveScribe"

if [ -x "$APP_BUNDLE" ]; then
  exec "$APP_BUNDLE"
elif [ -x "$APP_FOLDER" ]; then
  exec "$APP_FOLDER"
else
  echo "The portable application files are incomplete or not executable."
  echo "Extract the complete package, then run this script again."
  exit 1
fi
