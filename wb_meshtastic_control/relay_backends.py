from __future__ import annotations

import subprocess
from typing import Any

import paho.mqtt.client as mqtt

from wb_meshtastic_control.config import settings


class WBMqttRelayBackend:
    def publish(self, topic: str, payload: str) -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if settings.wb_mqtt_username:
            client.username_pw_set(settings.wb_mqtt_username, settings.wb_mqtt_password)
        client.connect(settings.wb_mqtt_host, settings.wb_mqtt_port, keepalive=10)
        result = client.publish(topic, payload=payload, qos=1, retain=False)
        result.wait_for_publish()
        client.disconnect()


class MeshtasticCommandBackend:
    def _base_args(self) -> list[str]:
        args = ["meshtastic", "--ch-index", str(settings.meshtastic_channel_index)]
        if settings.meshtastic_port:
            args.extend(["--port", settings.meshtastic_port])
        elif settings.meshtastic_host:
            args.extend(["--host", settings.meshtastic_host])
        elif settings.meshtastic_ble:
            args.extend(["--ble", settings.meshtastic_ble])
        return args

    def send_text(self, dest: str, text: str) -> None:
        command = [*self._base_args(), "--dest", dest, "--sendtext", text, "--ack"]
        subprocess.run(command, check=True, timeout=60)

    def gpio_write(self, dest: str, gpio: int, value: int) -> None:
        command = [*self._base_args(), "--dest", dest, "--gpio-wrb", str(gpio), str(value)]
        subprocess.run(command, check=True, timeout=60)
