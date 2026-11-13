#!/usr/bin/env bash
# LinkedIn Influence Lab - macOS / Linux launcher.
cd "$(dirname "$0")" || exit 1
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install -q -r requirements.txt
python -m streamlit run app.py
