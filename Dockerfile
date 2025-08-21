FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    MPLCONFIGDIR=/tmp/mpl-cache

# deps extras do seu projeto
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev libxslt1-dev \
    libpq-dev dbus \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p "$MPLCONFIGDIR"

WORKDIR /app

# 1) requirements com patch p/ Linux
COPY requirements.txt /app/requirements.txt
RUN set -eux; \
    cp /app/requirements.txt /app/requirements.linux.txt; \
    # remover qualquer linha Windows-only
    sed -ri '/^[[:space:]]*(pypiwin32|pywin32|win10toast)\b.*/d' /app/requirements.linux.txt || true; \
    # corrigir pins problemáticos
    sed -i 's/^scikit-learn==1\.4\.1$/scikit-learn==1.4.2/' /app/requirements.linux.txt || true; \
    sed -i 's/^proxy-requests==0\.6\.2$/proxy-requests==0.5.2/' /app/requirements.linux.txt || true; \
    sed -i 's/^numpy==2\..*/numpy==1.26.4/' /app/requirements.linux.txt || true; \
    python -m pip install --upgrade pip setuptools wheel; \
    python -m pip install --no-cache-dir -r /app/requirements.linux.txt

# 2) código
COPY . /app

# 3) launcher robusto
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
'# garante machine-id pro dbus (evita erro do gdbus)' \
'if [ ! -s /etc/machine-id ]; then command -v dbus-uuidgen >/dev/null 2>&1 && dbus-uuidgen --ensure=/etc/machine-id || true; fi' \
'cd /app/estados/sp' \
'PYTHONPATH=/app:/app/estados/sp exec python tjsp_executor.py "$@"' \
> /usr/local/bin/run-tjsp && chmod +x /usr/local/bin/run-tjsp

CMD ["/bin/bash"]
