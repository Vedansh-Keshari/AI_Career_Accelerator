#!/bin/bash
# Double-click this file on a Mac (or run it in a Linux terminal).
cd "$(dirname "$0")" || exit 1
echo "============================================================"
echo "  FeatureBot: Feature Engineering with AI Guidance"
echo "============================================================"
if command -v python3 >/dev/null 2>&1; then PY=python3; else
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."
  read -p "Press Enter to close..." _; exit 1
fi
if [ ! -x ".venv/bin/python" ]; then echo "[1/4] First run: setting up the environment (1-2 minutes)..."; $PY -m venv .venv || exit 1; fi
echo "[1/4] Installing / checking libraries..."
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt || { read -p "Failed. Press Enter..." _; exit 1; }
if [ ! -f adult.csv ]; then echo "[2/4] Building adult.csv from Resources_Dataset.xlsx..."; .venv/bin/python prepare_data.py || exit 1; else echo "[2/4] adult.csv found."; fi
echo "[3/4] Running the FeatureBot pipeline..."
.venv/bin/python featurebot_adult_income.py || { read -p "Failed. Press Enter..." _; exit 1; }
echo "[4/4] Running the extended experiments (1-2 minutes)..."
.venv/bin/python analysis/extended_experiments.py || { read -p "Failed. Press Enter..." _; exit 1; }
echo
echo "DONE. Results: featurebot_outputs/experiments_log.csv and results/extended_experiments.csv"
command -v open >/dev/null 2>&1 && open featurebot_outputs
read -p "Press Enter to close..." _
