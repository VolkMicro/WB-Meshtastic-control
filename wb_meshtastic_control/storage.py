from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    node TEXT NOT NULL,
    sensor TEXT,
    event TEXT,
    value_text TEXT,
    source TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS actions_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    event_id INTEGER,
    rule_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE SET NULL
);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def insert_event(self, envelope: dict[str, Any]) -> int:
        payload = envelope["payload"]
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events(created_at, kind, node, sensor, event, value_text, source, raw_text, payload_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now_iso(),
                    envelope["kind"],
                    envelope["node"],
                    payload.get("sensor"),
                    payload.get("event"),
                    str(payload.get("value", "")),
                    envelope["source"],
                    envelope["raw_text"],
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def log_action(self, event_id: int | None, rule_id: str, action_type: str, status: str, details: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO actions_log(created_at, event_id, rule_id, action_type, status, details_json)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (utc_now_iso(), event_id, rule_id, action_type, status, json.dumps(details, ensure_ascii=False)),
            )
            conn.commit()

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def latest_sensor_states(self) -> list[dict[str, Any]]:
        query = """
        SELECT e1.* FROM events e1
        JOIN (
          SELECT node, COALESCE(sensor, event) AS key_name, MAX(id) AS max_id
          FROM events
          GROUP BY node, COALESCE(sensor, event)
        ) latest ON latest.max_id = e1.id
        ORDER BY e1.id DESC
        """
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def latest_relay_state_by_topic(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    json_extract(details_json, '$.topic') AS topic,
                    json_extract(details_json, '$.payload') AS payload
                FROM actions_log
                WHERE action_type IN ('wb_mqtt_relay', 'wb_control_switch') AND status = 'ok'
                ORDER BY id DESC
                """
            ).fetchall()

        latest: dict[str, str] = {}
        for row in rows:
            topic = row["topic"]
            payload = row["payload"]
            if topic is None or payload is None:
                continue
            topic_key = str(topic)
            if topic_key in latest:
                continue
            latest[topic_key] = str(payload)
        return latest
