#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
repo="https://github.com/ajleveriza1108/Live-Scribe.git"
message="Add Call Mode and Australian English"
python_cmd=(python3)
[[ -x .venv/bin/python ]] && python_cmd=(.venv/bin/python)
git fetch origin main
read -r remote_only local_only < <(git rev-list --left-right --count origin/main...HEAD)
[[ "$remote_only" == "0" ]] || { echo "origin/main has newer commits."; exit 1; }
git rm --cached --ignore-unmatch -- data/hardware_profile.json data/.first-run-complete data/unfinished_session.json data/sessions.sqlite3 data/sessions.sqlite3-shm data/sessions.sqlite3-wal data/settings.json data/interview_profiles.json >/dev/null 2>&1 || true
git add --all
"${python_cmd[@]}" scripts/repository_preflight.py
"${python_cmd[@]}" -m pytest -q --ignore=tests/test_ui_handlers.py --ignore=tests/test_media_import.py
git diff --cached --check
if ! git diff --cached --quiet; then git commit -m "$message"; fi
git remote set-url origin "$repo"
git push -u origin main
