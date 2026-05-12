FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tini sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY wb_meshtastic_control /app/wb_meshtastic_control
COPY config /app/config

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . \
    && python -m pip install "meshtastic[cli]"

COPY . /app

EXPOSE 8091

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "wb_meshtastic_control.api:app", "--host", "0.0.0.0", "--port", "8091"]
