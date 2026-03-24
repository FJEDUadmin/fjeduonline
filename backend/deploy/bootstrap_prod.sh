#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f ".env.prod" ]]; then
  echo "[ERROR] .env.prod not found. Copy from .env.prod.example first."
  exit 1
fi

echo "[INFO] Starting one-shot production bootstrap..."
echo "[INFO] Building and launching production stack..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

echo "[INFO] Deployment started."
echo "[INFO] Check status with: docker compose -f docker-compose.prod.yml ps"
echo "[INFO] Follow logs with: docker compose -f docker-compose.prod.yml logs -f"
