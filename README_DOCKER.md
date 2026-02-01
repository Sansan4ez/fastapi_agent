# Docker Setup для PostgreSQL с pgvector

## Быстрый старт

### 1. Запуск БД для разработки

```bash
# Запустить PostgreSQL с pgvector
docker-compose up -d postgres

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f postgres
```

### 2. Запуск тестовой БД

```bash
# Запустить тестовую БД (используется tmpfs, данные не сохраняются)
docker-compose --profile test up -d postgres_test

# Тестовая БД будет доступна на порту 5433
```

### 3. Остановка и очистка

```bash
# Остановить контейнеры
docker-compose down

# Остановить и удалить volumes (все данные будут удалены!)
docker-compose down -v
```

## Конфигурация

### Переменные окружения (.env)

Скопируйте `.env.example` в `.env` и настройте:

```bash
cp .env.example .env
```

Основные параметры БД:
- `DB_HOST` - хост БД (localhost для Docker)
- `DB_PORT` - порт БД (5432 по умолчанию)
- `DB_NAME` - имя базы данных
- `DB_USER` - пользователь БД
- `DB_PASSWORD` - пароль БД

### Проверка pgvector

```bash
# Подключиться к БД
docker exec -it fastapi_agent_postgres psql -U postgres -d fastapi_agent

# Проверить расширение
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

# Выйти
\q
```

## Миграции Alembic

```bash
# Создать миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

## Работа с векторами (pgvector)

Пример создания таблицы с векторным полем:

```sql
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536)  -- для OpenAI embeddings
);

-- Создание индекса для быстрого поиска
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

В SQLAlchemy:

```python
from sqlalchemy import Column, Integer, Text
from pgvector.sqlalchemy import Vector

class Embedding(Base):
    __tablename__ = 'embeddings'

    id = Column(Integer, primary_key=True)
    content = Column(Text)
    embedding = Column(Vector(1536))  # размерность вектора
```

## Продакшен

Для продакшена рекомендуется использовать управляемый сервис PostgreSQL:

### Yandex Cloud Managed Service for PostgreSQL

1. Создайте кластер PostgreSQL через консоль Yandex Cloud
2. Включите расширение pgvector в настройках кластера
3. Обновите переменные окружения:
   - `DB_HOST` - адрес кластера
   - `DB_PORT` - порт (обычно 6432)
   - `DB_NAME` - имя БД
   - `DB_USER` - пользователь
   - `DB_PASSWORD` - пароль

### Альтернативы
- Selectel Database
- VK Cloud Solutions
- Self-hosted с репликацией и бэкапами

## Бэкапы (для локальной разработки)

```bash
# Создать бэкап
docker exec fastapi_agent_postgres pg_dump -U postgres fastapi_agent > backup.sql

# Восстановить из бэкапа
docker exec -i fastapi_agent_postgres psql -U postgres fastapi_agent < backup.sql
```

## Полезные команды

```bash
# Перезапустить БД
docker-compose restart postgres

# Посмотреть логи только БД
docker-compose logs -f postgres

# Зайти в контейнер
docker exec -it fastapi_agent_postgres bash

# Очистить всё и начать заново
docker-compose down -v && docker-compose up -d postgres
```
