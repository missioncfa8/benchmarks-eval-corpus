#!/usr/bin/env bash
# ==============================================================================
# run.sh — Universal Linux / Ubuntu / Debian / macOS / VM One-Click Launcher
# ==============================================================================

set -e

echo "========================================================================"
echo "   Starting Nexus Personnel Intelligence Platform (Linux/VM Launcher)"
echo "========================================================================"

# Detect Python
if command -v python3 &>/dev/null; then
    PY_CMD=python3
elif command -v python &>/dev/null; then
    PY_CMD=python
else
    echo "❌ Error: Python 3 is not installed. Run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

# Create virtual environment if absent
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment in ./venv ..."
    $PY_CMD -m venv venv
fi

# Activate virtualenv
source venv/bin/activate

# Install dependencies
echo "📦 Verifying dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Launch
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "🚀 Launching Nexus Portal on http://${HOST}:${PORT} ..."
exec python3 main.py
