# Dockerfile для FastAPI backend
FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код проекту
COPY . .

# Встановлюємо змінну середовища для вибору PostgreSQL
ENV DOCKER_ENV=true

# Відкриваємо порт 8000
EXPOSE 8000

# Install PostgreSQL client for health checks
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Команда для запуску FastAPI сервера
CMD ["/bin/sh", "-c", "/wait.sh postgres uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
