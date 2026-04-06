#!/usr/bin/env python
from wb_meshtastic_control.mesh_service import parse_wbmesh_text

test = 'WBMESH {"kind":"event","node":"shed","event":"button","value":1}'
print(f'Input string: [{test}]')
print(f'Starts with WBMESH: {test.startswith("WBMESH ")}')
result = parse_wbmesh_text(test, '!212c')
print(f'Result: {result}')
if result:
    print(f'  Kind: {result.kind}, Node: {result.node}, Source: {result.source}')
else:
    print('  ERROR: Parser returned None')
