#!/usr/bin/env bash
# ===================================================================
# Fetch Remote - Steam Deck & Handheld Gaming Mode Runner
# Publisher: TAB inc.
# ===================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required."
    exit 1
fi

# Ensure pywebview is installed
python3 -c "import webview" 2>/dev/null || {
    echo "Installing pywebview..."
    pip3 install --user pywebview || pip install --user pywebview
}

# Run in fullscreen / 1280x800 handheld mode
exec python3 "$SCRIPT_DIR/fetch_remote.py"
