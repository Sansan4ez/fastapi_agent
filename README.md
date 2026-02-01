# Шаблон Telegram бота на Aiogram 3 + SQLAlchemy

Данный проект представляет собой комплексный шаблон для разработки масштабируемых Telegram ботов с использованием фреймворка **Aiogram 3**, **SQLAlchemy** для работы с базой данных и **Alembic** для управления миграциями.

Для логирования используется удобная библиотека loguru. Благодаря этому логи красиво подсвечиваются в консоли и фоном записываются в файл логов.

## Технологический стек

- **Telegram API**: Aiogram 3
- **ORM**: SQLAlchemy с aiosqlite
- **База данных**: SQLite
- **Система миграций**: Alembic

## Обзор архитектуры

Проект следует архитектуре, вдохновленной микросервисами и лучшими практиками FastAPI. Каждый функциональный компонент бота организован как мини-сервис, что обеспечивает модульность разработки и обслуживания.

### Структура проекта

```
├── app/
│   ├── migration/
│   │   ├── versions
│   │   ├── env.py
│   ├── dao/
│   │   ├── base.py
│   ├── users/
│   │   ├── keyboards/
│   │   │ ├── inline_kb.py
│   │   │ ├── markup_kb.py
│   │   ├── models.py
│   │   ├── utils.py
│   │   └── router.py
│   ├── database.py
│   ├── log.txt
│   ├── main.py
│   └── config.py
├── data/
│   ├── db.sqlite3
├── alembic.ini
├── .env
└── requirements.txt
```

### Компоненты мини-сервиса

Каждый мини-сервис имеет следующую структуру:

- **keyboards/**: Клавиатуры Telegram (текстовые и инлайн)
- **dao.py**: Объекты доступа к базе данных через SQLAlchemy
- **models.py**: Модели SQLAlchemy, специфичные для сервиса
- **utils.py**: Вспомогательные функции и утилиты
- **router.py**: Обработчики Aiogram для сервиса

## Конфигурация

### Переменные окружения

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=[12345,344334]
```

- `BOT_TOKEN`: Получите у [BotFather](https://t.me/BotFather)
- `ADMIN_IDS`: Список Telegram ID администраторов бота. Можно получить тут Получите у [IDBot Finder Pro](https://t.me/get_tg_ids_universeBOT)

### Зависимости

```
aiogram==3.13.1
aiosqlite==0.20.0
alembic==1.13.3
loguru==0.7.2
pydantic-settings==2.5.2
SQLAlchemy==2.0.35
```

## Управление базой данных

### Конфигурация базовой модели

В проекте используется базовая модель SQLAlchemy с общими полями:

```python
class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    @classmethod
    @property
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### Объекты доступа к данным (DAO)

Проект реализует базовый класс BaseDAO с общими операциями базы данных:

- `find_one_or_none_by_id` - поиск по ID
- `find_one_or_none` - поиск одной записи по фильтру
- `find_all` - поиск всех записей по фильтру
- `add` - добавление записи
- `add_many` - добавление нескольких записей
- `update` - обновление записей
- `delete` - удаление записей
- `count` - подсчет количества записей
- `paginate` - пагинация
- `find_by_ids` - поиск по нескольким ID
- `upsert` - создание или обновление записи
- `bulk_update` - массовое обновление

Сервис-специфичные DAO наследуются от BaseDAO:

```python
from app.dao.base import BaseDAO
from app.users.models import User

class UserDAO(BaseDAO):
    model = User
```

Пример использования:

```python
user_info = await UserDAO.find_one_or_none(telegram_id=user_id)

await UserDAO.add(
    telegram_id=user_id,
    username=message.from_user.username,
    first_name=message.from_user.first_name,
    last_name=message.from_user.last_name,
    referral_id=ref_id
)
```

## Миграции базы данных

1. Определите ваши модели
2. Импортируйте модели в `migration/env.py`
3. Сгенерируйте файл миграции:

```bash
alembic revision --autogenerate -m "Initial revision"
```
1. Примените миграции:

```bash
alembic upgrade head
```

## Главный файл

В корне папки app есть файл `main.py`. Это основной файл проекта через который происходит сборка и запуск телеграмм бота. В этот файл импортируются роутеры, прописываются функции запупска и завершения работы бота, прписываются логи и прочее.

```python
import asyncio
from aiogram.types import BotCommand, BotCommandScopeDefault
from loguru import logger

from app.config import bot, admins, dp
from app.users.router import user_router


# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands():
    commands = [BotCommand(command='start', description='Старт')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция, которая выполнится когда бот запустится
async def start_bot():
    await set_commands()
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, f'Я запущен🥳.')
        except:
            pass
    logger.info("Бот успешно запущен.")


# Функция, которая выполнится когда бот завершит свою работу
async def stop_bot():
    try:
        for admin_id in admins:
            await bot.send_message(admin_id, 'Бот остановлен. За что?😔')
    except:
        pass
    logger.error("Бот остановлен!")


async def main():
    # регистрация роутеров
    dp.include_router(user_router)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)

    # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Начало работы

1. Клонируйте репозиторий:

```bash
git clone https://github.com/Yakvenalex/Aiogram3AlchemySample .
```

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

1. Запустите бота:

```bash
python -m app.main
```

## Лучшие практики

- Поддерживайте модульность сервисов, фокусируясь на конкретной функциональности
- Используйте BaseDAO для согласованных операций с базой данных
- Следуйте установленной структуре проекта для новых функций
- Используйте Alembic для всех изменений схемы базы данных
- Используйте переменные окружения для конфигурации

---

Этот шаблон предоставляет надежную основу для создания масштабируемых и поддерживаемых Telegram ботов с использованием Aiogram 3 и SQLAlchemy.
