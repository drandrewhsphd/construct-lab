#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  echo "Complete INSTALL-FIRST.txt before starting."
  read
  exit 1
fi
.venv/bin/python scripts/restore_app.py
