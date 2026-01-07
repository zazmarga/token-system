#!/bin/sh
set -e

# Застосовуємо міграції
alembic upgrade head

# Запускаємо сервер
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
