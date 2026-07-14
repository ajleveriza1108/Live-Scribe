#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

repository_url="https://github.com/ajleveriza1108/Live-Scribe.git"
commit_message="Add stoppable model downloads and vocabulary editing"

if ! command -v git >/dev/null 2>&1; then
  echo "Git is not installed. Install Git, then run this script again."
  exit 1
fi

if [ ! -d ".git" ]; then
  git init
fi

git branch -M main

if git remote | grep -qx "origin"; then
  current_remote=$(git remote get-url origin)
  if [ "$current_remote" != "$repository_url" ]; then
    git remote set-url origin "$repository_url"
  fi
else
  git remote add origin "$repository_url"
fi

git add .

if ! git diff --cached --quiet; then
  git commit -m "$commit_message"
else
  echo "No uncommitted changes were found."
fi

git push -u origin main

echo
echo "Live Scribe was uploaded successfully:"
echo "$repository_url"
