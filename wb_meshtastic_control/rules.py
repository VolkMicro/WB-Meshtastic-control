from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from wb_meshtastic_control.models import ActionSpec, IncomingEnvelope, RuleSpec
from wb_meshtastic_control.relay_backends import MeshtasticCommandBackend, WBMqttRelayBackend
from wb_meshtastic_control.storage import Storage


class RuleEngine:
    def __init__(self, rules_path: Path, storage: Storage) -> None:
        self.rules_path = rules_path
        self.storage = storage
        self.wb_backend = WBMqttRelayBackend()
        self.mesh_backend = MeshtasticCommandBackend()
        self.rules = self._load_rules()

    def _load_rules(self) -> list[RuleSpec]:
        data = yaml.safe_load(self.rules_path.read_text(encoding="utf-8")) or {}
        rules: list[RuleSpec] = []
        for raw_rule in data.get("rules", []):
            actions = []
            for raw_action in raw_rule.get("actions", []):
                action_type = str(raw_action["type"])
                params = {key: value for key, value in raw_action.items() if key != "type"}
                actions.append(ActionSpec(type=action_type, params=params))
            rules.append(
                RuleSpec(
                    rule_id=str(raw_rule["id"]),
                    enabled=bool(raw_rule.get("enabled", True)),
                    match=dict(raw_rule.get("match", {})),
                    actions=actions,
                )
            )
        return rules

    def _match(self, rule: RuleSpec, envelope: IncomingEnvelope) -> bool:
        if not rule.enabled:
            return False
        payload = envelope.payload
        for key, expected in rule.match.items():
            if key == "equals":
                if payload.get("value") != expected:
                    return False
                continue
            if key == "kind":
                actual = envelope.kind
            elif key == "source":
                actual = envelope.source
            elif key == "node":
                actual = envelope.node
            else:
                actual = payload.get(key)
            if actual != expected:
                return False
        return True

    def _render_text(self, template: str, envelope: IncomingEnvelope) -> str:
        text = template
        values = {"node": envelope.node, "source": envelope.source, **envelope.payload}
        for key, value in values.items():
            text = text.replace("{{ " + key + " }}", str(value))
            text = text.replace("{{" + key + "}}", str(value))
        return text

    def _build_status_text(self) -> str:
        states = self.storage.latest_relay_state_by_topic()
        boiler_topic = "/devices/wb-mr6cv3_92/controls/K1/on"
        light_topic = "/devices/wb-mr6cv3_92/controls/K2/on"

        boiler = states.get(boiler_topic)
        light = states.get(light_topic)

        def to_human(value: str | None) -> str:
            if value == "1":
                return "включен"
            if value == "0":
                return "выключен"
            return "неизвестно"

        return f"Статус: бойлер {to_human(boiler)}, свет {to_human(light)}"

    def handle_event(self, event_id: int, envelope: IncomingEnvelope) -> None:
        for rule in self.rules:
            if not self._match(rule, envelope):
                continue
            for action in rule.actions:
                try:
                    if action.type == "wb_mqtt_relay":
                        self.wb_backend.publish(str(action.params["topic"]), str(action.params["payload"]))
                    elif action.type == "mesh_text":
                        text = self._render_text(str(action.params["text"]), envelope)
                        self.mesh_backend.send_text(str(action.params["dest"]), text)
                    elif action.type == "mesh_status_reply":
                        dest_template = str(action.params.get("dest", "{{source}}"))
                        dest = self._render_text(dest_template, envelope)
                        self.mesh_backend.send_text(dest, self._build_status_text(), require_ack=False)
                    elif action.type == "meshtastic_gpio":
                        self.mesh_backend.gpio_write(
                            str(action.params["dest"]),
                            int(action.params["gpio"]),
                            int(action.params["value"]),
                        )
                    else:
                        raise ValueError(f"Unsupported action: {action.type}")
                    self.storage.log_action(event_id, rule.rule_id, action.type, "ok", action.params)
                except Exception as exc:
                    self.storage.log_action(event_id, rule.rule_id, action.type, "error", {"error": str(exc), **action.params})
