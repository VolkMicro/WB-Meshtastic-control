from __future__ import annotations

import subprocess
import time
from typing import Any

import paho.mqtt.client as mqtt

from wb_meshtastic_control.config import settings


class WBMqttRelayBackend:
    def publish(self, topic: str, payload: str) -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if settings.wb_mqtt_username:
            client.username_pw_set(settings.wb_mqtt_username, settings.wb_mqtt_password)
        client.connect(settings.wb_mqtt_host, settings.wb_mqtt_port, keepalive=10)
        client.loop_start()
        try:
            result = client.publish(topic, payload=payload, qos=1, retain=False)
            result.wait_for_publish(timeout=5)
            if not result.is_published():
                raise TimeoutError(f"MQTT publish timeout for topic {topic}")
        finally:
            client.loop_stop()
            client.disconnect()


class MeshtasticCommandBackend:
    def _base_args(self) -> list[str]:
        args = ["/opt/wb-meshtastic-control/venv/bin/meshtastic", "--ch-index", str(settings.meshtastic_channel_index)]
        if settings.meshtastic_port:
            args.extend(["--port", settings.meshtastic_port])
        elif settings.meshtastic_host:
            args.extend(["--host", settings.meshtastic_host])
        elif settings.meshtastic_ble:
            args.extend(["--ble", settings.meshtastic_ble])
        return args

    def send_text(self, dest: str, text: str, require_ack: bool = True) -> None:
        command = [*self._base_args(), "--dest", dest, "--sendtext", text]
        if require_ack:
            command.append("--ack")

        attempt = subprocess.run(command, check=False, timeout=60, capture_output=True, text=True)
        if attempt.returncode == 0:
            return

        stderr = attempt.stderr or ""
        stdout = attempt.stdout or ""
        combined = f"{stdout}\n{stderr}"
        transient_lock = (
            "serial device couldn't be opened" in combined
            or "Resource temporarily unavailable" in combined
            or "Errno 11" in combined
        )

        if transient_lock:
            subprocess.run(["pkill", "-f", "/opt/wb-meshtastic-control/venv/bin/meshtastic --listen"], check=False, timeout=5)
            time.sleep(1.0)
            retry = subprocess.run(command, check=False, timeout=60, capture_output=True, text=True)
            if retry.returncode == 0:
                return
            raise subprocess.CalledProcessError(retry.returncode, command, output=retry.stdout, stderr=retry.stderr)

        raise subprocess.CalledProcessError(attempt.returncode, command, output=attempt.stdout, stderr=attempt.stderr)

    def gpio_write(self, dest: str, gpio: int, value: int) -> None:
        command = [*self._base_args(), "--dest", dest, "--gpio-wrb", str(gpio), str(value)]
        subprocess.run(command, check=True, timeout=60)
