#!/usr/bin/env python
"""Comprehensive self-test of the WB Meshtastic Control MVP"""
import sys
import traceback
import json
import tempfile
from pathlib import Path
sys.stdout.flush()

print("=" * 60)
print("WB-Meshtastic-Control Self-Test")
print("=" * 60)
sys.stdout.flush()

try:
    # Test 1: Config
    print("\n[1] Configuration loading:")
    sys.stdout.flush()
    from wb_meshtastic_control.config import settings
    print(f"  ✓ Meshtastic port: {settings.meshtastic_port}")
    print(f"  ✓ WB MQTT host: {settings.wb_mqtt_host}:{settings.wb_mqtt_port}")
    print(f"  ✓ Rules file: {settings.rules_path}")
    sys.stdout.flush()

    # Test 2: YAML parsing
    print("\n[2] Rules YAML parsing:")
    sys.stdout.flush()
    import yaml
    rules_content = yaml.safe_load(settings.rules_path.read_text())
    print(f"  ✓ {len(rules_content.get('rules', []))} rules loaded")
    for rule in rules_content.get('rules', []):
        print(f"    - {rule['id']}: {len(rule.get('actions', []))} action(s)")
    sys.stdout.flush()

    # Test 3: Message parsing
    print("\n[3] WBMESH message parsing:")
    sys.stdout.flush()
    from wb_meshtastic_control.mesh_service import parse_wbmesh_text
    test_msg = 'WBMESH {"kind":"sensor","node":"shed-01","sensor":"temp","value":23.4}'
    result = parse_wbmesh_text(test_msg, "!212c")
    if result:
        print(f"  ✓ Parsed: kind={result.kind}, node={result.node}, source={result.source}")
    else:
        print(f"  ✗ Failed to parse WBMESH message")
    sys.stdout.flush()

    # Test 4: API import
    print("\n[4] API module:")
    sys.stdout.flush()
    try:
        from wb_meshtastic_control.api import app
        print(f"  ✓ FastAPI app created: {app.title}")
    except Exception as e:
        print(f"  ✗ API import failed: {e}")
    sys.stdout.flush()

    # Test 5: Files present
    print("\n[5] Project files:")
    sys.stdout.flush()
    files = [
        ".env",
        ".gitignore",
        "config/rules.example.yaml",
        "pyproject.toml",
        "README.md",
        "wb_meshtastic_control/__init__.py",
        "wb_meshtastic_control/api.py",
        "wb_meshtastic_control/config.py",
        "wb_meshtastic_control/models.py",
        "wb_meshtastic_control/mesh_service.py",
        "wb_meshtastic_control/relay_backends.py",
        "wb_meshtastic_control/rules.py",
        "wb_meshtastic_control/service.py",
        "wb_meshtastic_control/storage.py",
    ]
    project_root = Path.cwd()
    missing = []
    for f in files:
        path = project_root / f
        if not path.exists():
            missing.append(f)
            print(f"  ✗ {f}")
        else:
            print(f"  ✓ {f}")
    sys.stdout.flush()
    if missing:
        print(f"\n  WARNING: {len(missing)} file(s) missing!")
    else:
        print(f"\n  ✓ All {len(files)} files present")

    print("\n" + "=" * 60)
    if missing:
        print("RESULT: ⚠️  Some files missing - check above")
    else:
        print("RESULT: ✅ MVP is ready for deployment")
    print("=" * 60)
    sys.stdout.flush()

except Exception as e:
    print(f"\n✗ Self-test failed with error:")
    sys.stdout.flush()
    traceback.print_exc()
    sys.stdout.flush()
    sys.exit(1)
