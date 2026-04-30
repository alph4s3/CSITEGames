#!/usr/bin/env bash
# Quick run helper for the CSITEGames project (qr code testing)
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt
python "connect.py"
