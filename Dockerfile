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

# Команда для запуску FastAPI сервера
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
