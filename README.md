# WB Meshtastic Control

MVP для устойчивого управления и телеметрии через Meshtastic mesh, когда обычные каналы алертов нестабильны.

Что делает проект:
- принимает входящие mesh-сообщения от нод через `meshtastic --listen`
- разбирает текстовые payload'ы вида `WBMESH {json}`
- сохраняет события, телеметрию и команды в SQLite
- запускает правила: уведомление, локальное реле Wiren Board, remote GPIO по Meshtastic
- даёт HTTP API для просмотра состояния и отправки команд

## Идея протокола

Ноды шлют обычный текст в mesh:

```text
WBMESH {"kind":"sensor","node":"shed-01","sensor":"water_leak","value":1,"unit":"bool","ts":"2026-04-06T12:00:00Z"}
```

Для триггеров/команд можно слать:

```text
WBMESH {"kind":"event","node":"gate-01","event":"button_press","value":1}
```

## Что поддерживается в MVP

- приём сенсорных данных от mesh-нод
- запуск правил по значениям датчиков и событиям
- включение/выключение локального реле на Wiren Board через MQTT
- отправка mesh-команды на удалённую ноду
- вызов remote GPIO Meshtastic (`--gpio-wrb`) для нод, где это разрешено

## Быстрый старт

1. Скопируйте `.env.example` в `.env`.
2. Установите Meshtastic CLI:

```bash
pip install "meshtastic[cli]"
```

3. Установите зависимости проекта:

```bash
pip install -e .
```

4. Проверьте подключение к локальной ноде:

```bash
meshtastic --port /dev/ttyUSB0 --info
```

5. Запустите сервис:

```bash
uvicorn wb_meshtastic_control.api:app --host 0.0.0.0 --port 8091
```

## HTTP API

- `GET /healthz`
- `GET /api/events`
- `GET /api/sensors`
- `POST /api/mesh/send-text`
- `POST /api/relays/switch`

## Пример правила

См. [config/rules.example.yaml](i:/automation-course/scripts/WB-Meshtastic-control/config/rules.example.yaml).
