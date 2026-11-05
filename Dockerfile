FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir matplotlib seaborn notebook folium

COPY src/ ./src/
COPY sql/ ./sql/
COPY notebooks/ ./notebooks/

RUN mkdir -p bronze/dvf bronze/osm bronze/insee silver gold

ENV PYTHONUNBUFFERED=1
