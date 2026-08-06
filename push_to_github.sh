#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
repo="https://github.com/ajleveriza1108/Live-Scribe.git"
py="python3"; [[ -x .venv/bin/python ]] && py=".venv/bin/python"
"$py" scripts/repository_preflight.py
"$py" -m pytest -q --ignore=tests/test_ui_handlers.py --ignore=tests/test_media_import.py
[[ -d .git ]] || git init
git branch -M main
if git remote get-url origin >/dev/null 2>&1; then git remote set-url origin "$repo"; else git remote add origin "$repo"; fi
git rm --cached --ignore-unmatch -- data/hardware_profile.json data/.first-run-complete data/unfinished_session.json data/sessions.sqlite3 data/sessions.sqlite3-shm data/sessions.sqlite3-wal >/dev/null 2>&1 || true
git add .
[[ -z "$(git status --porcelain)" ]] || git commit -m "Upgrade Live Scribe to v0.9.1"
git push -u origin main
