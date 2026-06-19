# Use official Python base image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8010
CMD ["uvicorn", "imc.app:app", "--host", "0.0.0.0", "--port", "8010", "--log-level", "debug"]
