# WB Meshtastic Control

MVP для устойчивого управления и телеметрии через Meshtastic mesh, когда обычные каналы алертов нестабильны.

Что делает проект:
- принимает входящие mesh-сообщения от нод через `meshtastic --listen`
- разбирает текстовые payload'ы вида `WBMESH {json}`
- сохраняет события, телеметрию и команды в SQLite
- запускает правила: уведомление, локальное реле Wiren Board, remote GPIO по Meshtastic
- даёт HTTP API для просмотра состояния и отправки команд

## Production Deploy на чистый Wiren Board

Ниже пошаговый сценарий, который можно выполнить на новом контроллере "с нуля".

### 1) Установка Docker на WB

> Не используйте `apt install docker.io` — на WB необходим официальный скрипт
> который настраивает хранилище в `/mnt/data` и iptables под WB-специфику.

```bash
# Одной командой (рекомендуется по официальной документации):
wget -O - https://raw.githubusercontent.com/wirenboard/wb-community/refs/heads/main/scripts/docker-install/wb-docker-manager.sh | bash -s -- --install
```

После успешной установки вы увидите:
```
╔════════════════════════════════════════════════════════════════╗
║  ✓ Docker успешно установлен на контроллер Wiren Board!        ║
╚════════════════════════════════════════════════════════════════╝
```

Проверьте версии:
```bash
docker --version
docker compose version
```

Если `docker compose version` даёт ошибку "command not found", установите плагин вручную:
```bash
apt install -y docker-compose-plugin
```

Справка по официальной установке: https://wiki.wirenboard.com/wiki/Docker

### 2) Клонирование и подготовка конфигов

```bash
apt install -y git
mkdir -p /opt/wb-meshtastic-control
cd /opt/wb-meshtastic-control
git clone https://github.com/VolkMicro/WB-Meshtastic-control.git .

cp .env.example .env
cp config/rules.example.yaml config/rules.yaml
cp config/controls.example.yaml config/controls.yaml
mkdir -p data
```

### 3) Определить путь Meshtastic-устройства

```bash
ls -l /dev/serial/by-id/
```

Вывод будет примерно такой:
```
lrwxrwxrwx 1 root root 13 Apr  6 16:12 usb-Nologo_ProMicro_...-if00 -> ../../ttyACM0
```

> **ВАЖНО:** в `.env` нужен **полный путь**, не только имя файла из вывода `ls`.
>
> ❌ Типичная ошибка (только имя файла — НЕ РАБОТАЕТ):
> ```
> MESHTASTIC_PORT=usb-Nologo_ProMicro_compatible_nRF52840_DA498B180B749DA8-if00
> ```
>
> ✅ Вариант 1 — через by-id (стабильнее, не меняется при перезагрузке):
> ```
> MESHTASTIC_PORT=/dev/serial/by-id/usb-Nologo_ProMicro_compatible_nRF52840_DA498B180B749DA8-if00
> MESHTASTIC_DEVICE=/dev/serial/by-id/usb-Nologo_ProMicro_compatible_nRF52840_DA498B180B749DA8-if00
> ```
>
> ✅ Вариант 2 — через ttyACMx (проще, может сменить номер после перезагрузки):
> ```
> MESHTASTIC_PORT=/dev/ttyACM0
> MESHTASTIC_DEVICE=/dev/ttyACM0
> ```

Узнать реальный ttyACMx из симлинка:
```bash
readlink -f /dev/serial/by-id/<имя_вашего_устройства>
# пример вывода: /dev/ttyACM0
```

После редактирования `.env` проверьте — оба значения должны начинаться с `/dev/`:
```bash
grep MESHTASTIC /opt/wb-meshtastic-control/.env
```

### 4) Настройка приватного источника команд

В [config/rules.yaml](config/rules.yaml) замените `source` на ваш node id (например `!6985212c`) во всех приватных правилах.

### 5) Запуск на WB

На WB обычно уже есть системный `mosquitto`, поэтому используйте host-mode override:

```bash
docker compose -f docker-compose.yml -f docker-compose.wb.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.wb.yml ps
docker compose -f docker-compose.yml -f docker-compose.wb.yml logs -f wb-meshtastic-control
```

Сервис API:
- `http://127.0.0.1:8091/healthz`

## Диагностика (runbook)

### Проверка контейнера

```bash
cd /opt/wb-meshtastic-control
docker compose -f docker-compose.yml -f docker-compose.wb.yml ps
docker compose -f docker-compose.yml -f docker-compose.wb.yml logs --tail=200 wb-meshtastic-control
```

### Проверка serial и Meshtastic

```bash
ls -l /dev/serial/by-id/
docker compose -f docker-compose.yml -f docker-compose.wb.yml exec wb-meshtastic-control \
	sh -lc 'meshtastic --port "$MESHTASTIC_PORT" --info'
```

### Проверка API

```bash
curl -fsS http://127.0.0.1:8091/healthz
curl -fsS "http://127.0.0.1:8091/api/events?limit=5"
curl -fsS http://127.0.0.1:8091/api/sensors
```

### Проверка MQTT-команд

```bash
mosquitto_sub -h 127.0.0.1 -t '/devices/wb-mr6cv3_92/controls/K1/on' -t '/devices/wb-mr6cv3_92/controls/K2/on' -v
```

### Проверка БД событий/действий

```bash
sqlite3 /opt/wb-meshtastic-control/data/meshtastic_control.db "select id,source,raw_text from events order by id desc limit 10;"
sqlite3 /opt/wb-meshtastic-control/data/meshtastic_control.db "select id,rule_id,action_type,status from actions_log order by id desc limit 10;"
```

### Рестарт/обновление

```bash
cd /opt/wb-meshtastic-control
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.wb.yml up -d --build
```

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

См. [config/rules.example.yaml](config/rules.example.yaml).
