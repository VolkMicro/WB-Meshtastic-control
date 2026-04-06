from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8091
    data_dir: Path = Path("./data")
    db_path: Path = Path("./data/meshtastic_control.db")
    rules_path: Path = Path("./config/rules.example.yaml")
    controls_path: Path = Path("./config/controls.example.yaml")

    meshtastic_bin: str = "meshtastic"
    meshtastic_channel_index: int = 0
    meshtastic_port: str = ""
    meshtastic_host: str = ""
    meshtastic_ble: str = ""
    meshtastic_poll_restart_sec: int = 5

    wb_mqtt_host: str = "127.0.0.1"
    wb_mqtt_port: int = 1883
    wb_mqtt_username: str = ""
    wb_mqtt_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
