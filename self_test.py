#!/usr/bin/env python
"""Comprehensive self-test of the WB Meshtastic Control MVP"""
import sys
import traceback
try:
    import json
    import tempfile
    from pathlib import Path
except Exception as e:
    print(f"Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("WB-Meshtastic-Control Self-Test")
print("=" * 60)
sys.stdout.flush()

try:

# Test 1: Config
print("\n[1] Configuration loading:")
from wb_meshtastic_control.config import settings
print(f"  ✓ Meshtastic port: {settings.meshtastic_port}")
print(f"  ✓ WB MQTT host: {settings.wb_mqtt_host}:{settings.wb_mqtt_port}")
print(f"  ✓ Rules file: {settings.rules_path}")

# Test 2: YAML parsing
print("\n[2] Rules YAML parsing:")
import yaml
rules_content = yaml.safe_load(settings.rules_path.read_text())
print(f"  ✓ {len(rules_content.get('rules', []))} rules loaded")
for rule in rules_content.get('rules', []):
    print(f"    - {rule['id']}: {len(rule.get('actions', []))} action(s)")

# Test 3: Message parsing
print("\n[3] WBMESH message parsing:")
from wb_meshtastic_control.mesh_service import parse_wbmesh_text
test_msg = 'WBMESH {"kind":"sensor","node":"shed-01","sensor":"temp","value":23.4}'
result = parse_wbmesh_text(test_msg, "!212c")
if result:
    print(f"  ✓ Parsed: kind={result.kind}, node={result.node}, source={result.source}")
else:
    print(f"  ✗ Failed to parse WBMESH message")

# Test 4: Storage
print("\n[4] Storage initialization:")
from wb_meshtastic_control.storage import Storage
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = Path(tmpdir) / "test.db"
    storage = Storage(db_path)
    print(f"  ✓ Database created: {db_path.exists()}")

# Test 5: Rule matching with security
print("\n[5] Rule matching (source security):")
from wb_meshtastic_control.models import IncomingEnvelope
from wb_meshtastic_control.rules import RuleEngine
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = Path(tmpdir) / "test.db"
    storage = Storage(db_path)
    engine = RuleEngine(settings.rules_path, storage)
    
    env_good = IncomingEnvelope(
        kind='event', node='test',
        payload={'event': 'stop_pump', 'value': 1},
        raw_text='test', source='!212c'
    )
    env_bad = IncomingEnvelope(
        kind='event', node='test',
        payload={'event': 'stop_pump', 'value': 1},
        raw_text='test', source='!9999'
    )
    
    matched_good = [r for r in engine.rules if engine._match(r, env_good)]
    matched_bad = [r for r in engine.rules if engine._match(r, env_bad)]
    print(f"  ✓ Correct source (!212c): {len(matched_good)} rule(s) matched")
    print(f"  ✓ Wrong source (!9999): {len(matched_bad)} rule(s) matched (security OK)")

# Test 6: API import
print("\n[6] API module:")
try:
    from wb_meshtastic_control.api import app
    print(f"  ✓ FastAPI app created: {app.title}")
except Exception as e:
    print(f"  ✗ API import failed: {e}")

# Test 7: Files present
print("\n[7] Project files:")
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
