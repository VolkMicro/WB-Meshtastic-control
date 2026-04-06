from __future__ import annotations

from wb_meshtastic_control.config import settings
from wb_meshtastic_control.mesh_service import MeshListener
from wb_meshtastic_control.relay_backends import MeshtasticCommandBackend, WBMqttRelayBackend
from wb_meshtastic_control.rules import RuleEngine
from wb_meshtastic_control.storage import Storage


storage = Storage(settings.db_path)
rule_engine = RuleEngine(settings.rules_path, storage)
mesh_listener = MeshListener(storage, rule_engine)
mesh_commands = MeshtasticCommandBackend()
wb_relays = WBMqttRelayBackend()
