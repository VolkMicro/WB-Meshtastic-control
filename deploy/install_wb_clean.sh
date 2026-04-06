#!/bin/bash
set -e

cd /opt/wb-meshtastic-control
rm -rf venv wb_meshtastic_control.egg-info __pycache__ build dist

echo "Creating venv..."
python3 -m venv venv

echo "Activating venv..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install paho-mqtt fastapi uvicorn pydantic-settings PyYAML -q

echo ""
echo "Testing imports..."
python3 -c "
from wb_meshtastic_control.config import settings
print('✓ Config:', settings.meshtastic_port)
from wb_meshtastic_control.api import app
print('✓ API:', app.title)
from wb_meshtastic_control.mesh_service import parse_wbmesh_text
print('✓ Parser ready')
"

echo ""
echo "✅ Installation complete!"
echo "App at: /opt/wb-meshtastic-control"
echo "Venv at: /opt/wb-meshtastic-control/venv"
ls -lh wb_meshtastic_control config deploy .env 2>/dev/null | awk '{print "  " $9}'
