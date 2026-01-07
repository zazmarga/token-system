# Базовий образ з Python
FROM python:3.11-slim

# Робоча директорія
WORKDIR /app

# Встановлюємо залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код
COPY . .

# Копіюємо entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
