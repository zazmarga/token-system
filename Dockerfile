# Базовий образ з Python
FROM python:3.11-slim

# Робоча директорія
WORKDIR /app

# Встановлюємо залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код
COPY . .

# Запускаємо сервер
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
