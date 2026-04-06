from __future__ import annotations

import json
import logging
import re
import subprocess
import threading
import time
from dataclasses import asdict
from typing import Any

from wb_meshtastic_control.config import settings
from wb_meshtastic_control.models import IncomingEnvelope
from wb_meshtastic_control.rules import RuleEngine
from wb_meshtastic_control.storage import Storage


LOGGER = logging.getLogger("wb-meshtastic-control")


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def parse_wbmesh_text(raw_text: str, source: str) -> IncomingEnvelope | None:
    if not raw_text.startswith("WBMESH "):
        return None
    payload_part = raw_text.removeprefix("WBMESH ").strip()
    payload_json = _extract_first_json_object(payload_part)
    if payload_json is None:
        return None

    # Some clients send escaped JSON in text payload: {\"kind\":...}
    if '\\"' in payload_json:
        payload_json = payload_json.replace('\\"', '"')

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        LOGGER.warning("Invalid WBMESH payload from %s: %s", source, raw_text)
        return None
    kind = str(payload.get("kind", "unknown"))
    node = str(payload.get("node", source or "unknown"))
    return IncomingEnvelope(kind=kind, node=node, payload=payload, raw_text=raw_text, source=source)


def parse_natural_command_text(raw_text: str, source: str) -> IncomingEnvelope | None:
    normalized = raw_text.lower().strip()
    normalized = re.sub(r"[!?.,;:]+", " ", normalized)
    normalized = " ".join(normalized.split())
    event_map = {
        "включи бойлер": "boiler_on",
        "выключи бойлер": "boiler_off",
        "отключи бойлер": "boiler_off",
        "включи свет": "light_on",
        "выключи свет": "light_off",
        "отключи свет": "light_off",
        "включи режим охраны": "guard_mode_on",
        "статус": "status_request",
        "status": "status_request",
    }
    event = event_map.get(normalized)
    if event is None:
        return None
    payload = {
        "kind": "event",
        "event": event,
        "value": 1,
        "command_text": raw_text,
    }
    return IncomingEnvelope(kind="event", node=source or "unknown", payload=payload, raw_text=raw_text, source=source)


class MeshListener:
    def __init__(self, storage: Storage, rules: RuleEngine) -> None:
        self.storage = storage
        self.rules = rules
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_seen_key: tuple[str, str] | None = None
        self._last_seen_ts: float = 0.0

    def _listen_command(self) -> list[str]:
        meshtastic_bin = settings.meshtastic_bin
        command = [
            meshtastic_bin,
            "--listen",
            "--seriallog",
            "none",
            "--ch-index",
            str(settings.meshtastic_channel_index),
        ]
        if settings.meshtastic_port:
            command.extend(["--port", settings.meshtastic_port])
        elif settings.meshtastic_host:
            command.extend(["--host", settings.meshtastic_host])
        elif settings.meshtastic_ble:
            command.extend(["--ble", settings.meshtastic_ble])
        return command

    def _extract_text(self, line: str) -> tuple[str, str] | None:
        # Primary format: JSON packet (when CLI emits structured events)
        try:
            packet = json.loads(line)
        except json.JSONDecodeError:
            packet = None

        if packet is not None:
            decoded = packet.get("decoded") or {}
            text = decoded.get("text")
            if text:
                source = str(packet.get("fromId") or packet.get("from") or "unknown")
                return str(text), source

        # Secondary format: python-dict-like event line with text field.
        # Example contains fragments like: 'fromId': '!6985212c', ... 'text': 'включи бойлер'
        text_match = re.search(r"['\"]text['\"]\s*:\s*['\"](.+?)['\"]", line)
        if text_match:
            text = text_match.group(1)
            text = text.replace("\\\"", '"').replace("\\'", "'")
            source_match = re.search(r"![0-9a-fA-F]+", line)
            source = source_match.group(0) if source_match else "unknown"
            return text, source

        # Fallback format: human-readable CLI lines, extract embedded WBMESH payload.
        marker = "WBMESH "
        if marker not in line:
            return None
        raw_text = line[line.index(marker) :].strip()
        match = re.search(r"(![0-9a-fA-F]+)", line)
        source = match.group(1) if match else "unknown"
        return raw_text, source

    def run_forever(self) -> None:
        while not self._stop.is_set():
            command = self._listen_command()
            LOGGER.info("Starting Meshtastic listener: %s", " ".join(command))
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                assert process.stdout is not None
                for line in process.stdout:
                    if self._stop.is_set():
                        process.terminate()
                        break
                    record = self._extract_text(line.strip())
                    if record is None:
                        continue
                    raw_text, source = record
                    envelope = parse_wbmesh_text(raw_text, source)
                    if envelope is None:
                        envelope = parse_natural_command_text(raw_text, source)
                    if envelope is None:
                        continue

                    # Meshtastic CLI can print multiple lines for the same received text packet.
                    # Prevent duplicate execution when identical (source, raw_text) appears in short window.
                    dedup_key = ("msg", envelope.raw_text)
                    now_ts = time.time()
                    if self._last_seen_key == dedup_key and (now_ts - self._last_seen_ts) < 2.0:
                        continue
                    self._last_seen_key = dedup_key
                    self._last_seen_ts = now_ts

                    event_id = self.storage.insert_event(asdict(envelope))
                    self.rules.handle_event(event_id, envelope)
            except Exception:
                LOGGER.exception("Meshtastic listener crashed")
            time.sleep(settings.meshtastic_poll_restart_sec)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run_forever, daemon=True)
        self._thread.start()
