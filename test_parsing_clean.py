#!/usr/bin/env python
import json

# Test 1: Direct parsing logic
raw_text = 'WBMESH {"kind":"event","node":"test","value":1}'
print(f"Test string: {raw_text}")
print(f"Starts with 'WBMESH ': {raw_text.startswith('WBMESH ')}")

if raw_text.startswith("WBMESH "):
    try:
        payload_str = raw_text.removeprefix("WBMESH ").strip()
        payload = json.loads(payload_str)
        print(f"✓ Parsing OK: {payload}")
    except json.JSONDecodeError as e:
        print(f"✗ JSON error: {e}")
else:
    print("✗ Does not start with WBMESH ")

# Test 2: Using the function
print("\nTest 2: Using parse_wbmesh_text")
from wb_meshtastic_control.mesh_service import parse_wbmesh_text
result = parse_wbmesh_text(raw_text, "!212c")
print(f"Function result: {result}")
if result:
    print(f"  Kind: {result.kind}, Node: {result.node}, Source: {result.source}")
