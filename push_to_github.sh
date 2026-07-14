#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

repository_url="https://github.com/ajleveriza1108/Live-Scribe.git"

if ! command -v git >/dev/null 2>&1; then
  echo "Git is not installed. Install Git, then run this script again."
  exit 1
fi

if [ ! -d ".git" ]; then
  git init
fi

git branch -M main

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$repository_url"
else
  git remote add origin "$repository_url"
fi

git add .
if ! git diff --cached --quiet; then
  git commit -m "Release Live Scribe v0.3.2"
fi

git push -u origin main

echo
echo "Live Scribe was uploaded to:"
echo "$repository_url"
