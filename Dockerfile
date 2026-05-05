FROM python:3.10-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NOWARNINGS=yes \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    ffmpeg \
    mediainfo \
    tini \
    build-essential \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["python", "-m", "bot"]