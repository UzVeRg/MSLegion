# Технологический стек

## Используется в репозитории

| Область | Технологии |
| --- | --- |
| Backend | Python 3.12–3.14, FastAPI, Uvicorn и `asyncio` |
| Схемы и конфигурация | Pydantic v2 и pydantic-settings |
| Данные | PostgreSQL 17 в локальном Compose, асинхронный SQLAlchemy 2.x, Psycopg 3 и Alembic |
| Вход и сессии | Проверка Telegram `initData` на backend, серверные сессии в PostgreSQL с ограниченным сроком и отзывом |
| Разработка и проверка | pytest, pytest-asyncio, HTTPX для тестов API и Ruff |
| Локальная инфраструктура | Docker Compose для рабочей и отдельной тестовой базы PostgreSQL |

Диапазоны версий и группы зависимостей определены в [`backend/pyproject.toml`](../../../backend/pyproject.toml). Контейнеры описаны в [`docker-compose.yml`](../../../docker-compose.yml). Параметры конфигурации перечислены в [`.env.example`](../../../.env.example).

## Запланировано

| Область | Технологии и условие внедрения |
| --- | --- |
| Пользовательский интерфейс | Vue 3, TypeScript, Vite и Telegram Mini App API |
| Telegram-бот | aiogram 3 для Telegram-адаптера |
| Внешние HTTP-запросы | `HTTPX AsyncClient`, когда появится исходящая интеграция |
| Развёртывание | Caddy или nginx в качестве обратного прокси, выбор при подготовке развёртывания |
| Кэш и фоновые задачи | Redis и Taskiq при появлении конкретных требований |
| Обновления в реальном времени и медиа | WebSocket для подходящего сценария и S3-совместимое хранилище при необходимости |

Приоритеты внедрения определяет [план развития](../planning/roadmap.md).
