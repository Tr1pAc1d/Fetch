#!/usr/bin/env bash
# ===================================================================
# Fetch Remote - 1-Click Steam Deck Installer (TAB inc.)
# ===================================================================

set -e

INSTALL_DIR="$HOME/.local/share/fetch-remote"
DESKTOP_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

echo "========================================================"
echo "    FETCH REMOTE - STEAM DECK INSTALLER (TAB inc.)"
echo "========================================================"

mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICONS_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/3] Copying files to $INSTALL_DIR..."
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/start_deck.sh"

echo "[2/3] Installing application icon..."
if [ -f "$INSTALL_DIR/icon.png" ]; then
    cp "$INSTALL_DIR/icon.png" "$ICONS_DIR/fetch-remote.png"
fi

echo "[3/3] Registering SteamOS Application..."
cat <<EOF > "$DESKTOP_DIR/fetch-remote.desktop"
[Desktop Entry]
Name=Fetch Remote
Comment=Use your Steam Deck as a wireless touchpad & PC controller
Exec=bash "$INSTALL_DIR/start_deck.sh"
Icon=$ICONS_DIR/fetch-remote.png
Terminal=false
Type=Application
Categories=Utility;Game;
Path=$INSTALL_DIR
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR/fetch-remote.desktop"

# Also copy to Desktop if exists
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_DIR/fetch-remote.desktop" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/fetch-remote.desktop"
fi

echo ""
echo "========================================================"
echo "Installation Complete!"
echo ""
echo "TO PLAY FROM STEAM GAMING MODE:"
echo "1. Open the Steam desktop client."
echo "2. Click 'Games' menu -> 'Add a Non-Steam Game to My Library'."
echo "3. Select 'Fetch Remote' from the list and click 'Add Selected Programs'."
echo "4. Return to Gaming Mode — Fetch Remote will be in your Library!"
echo "========================================================"
