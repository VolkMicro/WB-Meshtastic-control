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


def parse_wbmesh_text(raw_text: str, source: str) -> IncomingEnvelope | None:
    if not raw_text.startswith("WBMESH "):
        return None
    payload = json.loads(raw_text.removeprefix("WBMESH ").strip())
    kind = str(payload.get("kind", "unknown"))
    node = str(payload.get("node", source or "unknown"))
    return IncomingEnvelope(kind=kind, node=node, payload=payload, raw_text=raw_text, source=source)


class MeshListener:
    def __init__(self, storage: Storage, rules: RuleEngine) -> None:
        self.storage = storage
        self.rules = rules
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def _listen_command(self) -> list[str]:
        # Use absolute path for meshtastic to work reliably in systemd
        meshtastic_bin = "/opt/wb-meshtastic-control/venv/bin/meshtastic"
        command = [meshtastic_bin, "--listen", "--seriallog", "none", "--ch-index", str(settings.meshtastic_channel_index)]
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
                        continue
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
