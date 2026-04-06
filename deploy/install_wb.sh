#!/bin/bash
set -e

APP_DIR="/opt/wb-meshtastic-control"
VENV_DIR="$APP_DIR/venv"

echo "🔸 WB Meshtastic Control Deployment"
echo "==================================="

# Check current user
if [ "$(whoami)" != "root" ]; then
    echo "⚠️  This script should run as root. Trying with sudo..."
    exec sudo "$0" "$@"
fi

# Clean previous install if exists
if [ -d "$APP_DIR" ]; then
    echo "Removing previous installation: $APP_DIR"
    rm -rf "$APP_DIR"
fi

echo "Creating app directory: $APP_DIR"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "Cloning repository..."
git clone https://github.com/VolkMicro/WB-Meshtastic-control.git . 2>/dev/null || {
    echo "⚠️  Clone failed, trying SSH..."
    git clone git@github.com:VolkMicro/WB-Meshtastic-control.git .
}

echo "Creating Python venv..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -e . -q

# Create data directory
mkdir -p "$APP_DIR/data"

echo "Copying systemd unit..."
cp deploy/systemd_wb-meshtastic.service /etc/systemd/system/wb-meshtastic.service

echo "Updating systemd..."
systemctl daemon-reload

echo "Enabling and starting service..."
systemctl enable wb-meshtastic
systemctl start wb-meshtastic

echo ""
echo "✅ Deployment complete!"
echo "   App directory: $APP_DIR"
echo "   Service: wb-meshtastic"
echo "   API will be available at: http://127.0.0.1:8091"
echo ""
echo "Useful commands:"
echo "   systemctl status wb-meshtastic"
echo "   systemctl restart wb-meshtastic"
echo "   journalctl -u wb-meshtastic -f"
echo ""
