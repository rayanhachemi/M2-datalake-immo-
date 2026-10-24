FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir matplotlib seaborn notebook

COPY src/ ./src/
COPY sql/ ./sql/
COPY notebooks/ ./notebooks/

RUN mkdir -p bronze/dvf bronze/osm bronze/insee silver gold

ENV PYTHONUNBUFFERED=1
