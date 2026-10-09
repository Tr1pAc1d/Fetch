#!/usr/bin/env bash
# ===================================================================
# Fetch Remote - Touchpad Client for Linux (TAB inc.)
# ===================================================================

echo "========================================================"
echo "    FETCH REMOTE - TOUCHPAD CLIENT FOR LINUX"
echo "                   TAB inc."
echo "========================================================"

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Please install python3."
    exit 1
fi

# Ensure pywebview is installed
python3 -c "import webview" 2>/dev/null || {
    echo "Installing pywebview..."
    pip3 install pywebview || pip install pywebview
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/fetch_remote.py"
