# Docker Deployment для Subnet Scanner

Цей проект налаштований для запуску у трьох Docker контейнерах:
- **Frontend**: Next.js (порт 3000)
- **Backend**: FastAPI (порт 8000)
- **Database**: PostgreSQL (порт 5432)

## Швидкий старт

### 1. Запуск всіх сервісів
```bash
docker-compose up -d
```

### 2. Перевірка статусу контейнерів
```bash
docker-compose ps
```

### 3. Перегляд логів
```bash
# Всі сервіси
docker-compose logs -f

# Конкретний сервіс
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### 4. Зупинка сервісів
```bash
docker-compose down
```

### 5. Зупинка з видаленням volumes (УВАГА: видалить дані БД!)
```bash
docker-compose down -v
```

## Доступ до сервісів

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Backend Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

## Конфігурація

### База даних PostgreSQL
- **Host**: postgres (всередині Docker мережі) / localhost (ззовні)
- **Port**: 5432
- **Database**: subnetdb
- **User**: subnetuser
- **Password**: subnetpass123

### Volumes
- `postgres_data`: Зберігає дані PostgreSQL (не втрачаються при перезапуску)
- `./reports`: Папка з результатами сканування
- `./app.log`: Лог файл backend

## Розробка

### Перебудова backend після змін коду
```bash
docker-compose build backend
docker-compose up -d backend
```

### Встановлення нових npm пакетів для frontend
```bash
docker-compose exec frontend npm install <package-name>
```

### Доступ до контейнерів
```bash
# Backend shell
docker-compose exec backend bash

# Frontend shell
docker-compose exec frontend sh

# PostgreSQL shell
docker-compose exec postgres psql -U subnetuser -d subnetdb
```

## Troubleshooting

### Якщо frontend не запускається
```bash
docker-compose exec frontend npm install
docker-compose restart frontend
```

### Якщо backend не може підключитися до БД
```bash
docker-compose logs postgres
docker-compose restart backend
```

### Очистка Docker кешу
```bash
docker system prune -a
docker-compose build --no-cache
```

## Структура проекту

```
subnetscanner/
├── docker-compose.yml      # Конфігурація всіх сервісів
├── Dockerfile             # Збірка backend
├── .dockerignore          # Файли для ігнорування при збірці
├── requirements.txt       # Python залежності
├── app/                   # FastAPI backend
├── frontend/              # Next.js frontend
├── reports/               # Результати сканування (volume)
└── postgres_data/         # Дані PostgreSQL (volume)
```

## Безпека

**УВАГА**: Цей Docker-compose файл призначений для розробки. Для production використання:
1. Змініть паролі бази даних
2. Використовуйте environment файли замість hardcoded значень
3. Налаштуйте SSL/TLS
4. Обмежте доступ до портів
