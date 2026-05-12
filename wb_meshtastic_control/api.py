from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from wb_meshtastic_control.service import mesh_commands, mesh_listener, storage, wb_relays

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SendTextRequest(BaseModel):
    dest: str
    text: str


class RelaySwitchRequest(BaseModel):
    topic: str
    payload: str


class GpioWriteRequest(BaseModel):
    dest: str
    gpio: int
    value: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    mesh_listener.start()
    yield


app = FastAPI(title="WB Meshtastic Control", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/test-meshtastic")
def test_meshtastic() -> dict[str, str]:
    """Test Meshtastic device connection"""
    import subprocess
    try:
        result = subprocess.run(
            [settings.meshtastic_bin, "--port", settings.meshtastic_port, "--info"],
            capture_output=True, text=True, timeout=10
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Command timed out"}
    except Exception as e:
        return {"status": "exception", "error": str(e)}


@app.get("/start-listener")
def start_listener() -> dict[str, str]:
    """Manually start Meshtastic listener for testing"""
    try:
        mesh_listener.start()
        return {"status": "listener_start_attempted"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/events")
def list_events(limit: int = 50) -> list[dict]:
    return storage.list_events(limit=limit)


@app.get("/api/sensors")
def list_sensors() -> list[dict]:
    return storage.latest_sensor_states()


@app.post("/api/mesh/send-text")
def send_text(request: SendTextRequest) -> dict[str, str]:
    mesh_commands.send_text(request.dest, request.text)
    return {"status": "sent"}


@app.post("/api/mesh/gpio-write")
def mesh_gpio_write(request: GpioWriteRequest) -> dict[str, str]:
    mesh_commands.gpio_write(request.dest, request.gpio, request.value)
    return {"status": "sent"}


@app.post("/api/relays/switch")
def relay_switch(request: RelaySwitchRequest) -> dict[str, str]:
    wb_relays.publish(request.topic, request.payload)
    return {"status": "ok"}
