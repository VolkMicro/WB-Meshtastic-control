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

## Запуск в Docker Compose (production-ready)

### 1) Подготовка конфигов

```bash
cp .env.example .env
cp config/rules.example.yaml config/rules.yaml
cp config/controls.example.yaml config/controls.yaml
```

Проверьте в `.env`:
- `MESHTASTIC_PORT` = путь к устройству внутри контейнера (обычно `/dev/ttyACM0` или `/dev/serial/by-id/...`)
- `MESHTASTIC_DEVICE` = путь к устройству на хосте (для `devices:` в compose)

### 2) Локальный стенд (встроенный Mosquitto)

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f wb-meshtastic-control
```

### 3) Wiren Board (использовать MQTT хоста)

На WB обычно уже есть `mosquitto` на хосте, поэтому используйте override с `host network`:

```bash
docker compose -f docker-compose.yml -f docker-compose.wb.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.wb.yml logs -f wb-meshtastic-control
```

Проверка:
- `GET /healthz`
- `GET /api/events`
- `GET /api/sensors`

## Масштабирование без правки кода

Чтобы добавить новые реле/каналы, редактируйте только YAML.

### 1) Добавить контрол в `config/controls.yaml`

```yaml
controls:
	gate:
		name: ворота
		topic: /devices/wb-do4/controls/K3/on
		states:
			on: "1"
			off: "0"
		labels:
			on: открыты
			off: закрыты
			unknown: неизвестно
```

### 2) Добавить правило в `config/rules.yaml`

```yaml
rules:
	- id: gate-open
		enabled: true
		match:
			kind: event
			source: "!6985212c"
			event: gate_on
		actions:
			- type: wb_control_switch
				control_id: gate
				state: on
```

Новый action `wb_control_switch` сам берёт topic/payload из `controls.yaml`, поэтому логика единообразная и легче поддерживается на большом доме.

### 3) Статус автоматически масштабируется

Команда `статус` теперь собирается динамически по всем контролам из `controls.yaml`. После добавления нового контрола он попадёт в статус-ответ автоматически.

## HTTP API

- `GET /healthz`
- `GET /api/events`
- `GET /api/sensors`
- `POST /api/mesh/send-text`
- `POST /api/relays/switch`

## Пример правила

См. [config/rules.example.yaml](i:/automation-course/scripts/WB-Meshtastic-control/config/rules.example.yaml).
