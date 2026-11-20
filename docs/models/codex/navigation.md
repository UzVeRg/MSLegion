# Карта исходников

Базовая запись от 20.11.2026. Применяй дополнения по правилам [указателя](README.md).

## NAV-01 — Точка входа, общие ответы и настройки

- Приложение FastAPI и подключение обработчиков — `backend/app/main.py`.
- Сборка маршрутов, `/health` и `/ready` — `backend/app/api/router.py`.
- Переменные окружения и значения по умолчанию — `backend/app/core/config.py` и `.env.example`.
- База и сессии — `backend/app/core/database.py`. Ключи API — `backend/app/core/security.py`.
- Ошибки и идентификатор запроса — `backend/app/core/exceptions.py` и `backend/app/core/middleware.py`. Проверка в `backend/tests/test_request_context.py`.

## NAV-02 — Модули API

- Пользователи — `backend/app/modules/users/`, тесты в `backend/tests/test_users.py`.
- Приём события и маршрут истории `/api/v1/admin/callbacks` — `backend/app/modules/integrations/`, тесты в `backend/tests/test_callbacks.py`.
- Маршрут `/api/v1/admin/status` — `backend/app/modules/admin/`.
- Контракты маршрутов — файлы `router.py` и `schemas.py` в соответствующих модулях. Справочник команды — `docs/team/reference/api.md`.

## NAV-03 — Данные и проверки

- Миграции — `backend/alembic/versions/`, модели — `models.py` в модулях users и integrations.
- Рабочая и тестовая базы — `docker-compose.yml`, сервисы `postgres` и `postgres-test`.
- Быстрые тесты из `backend` — `..\.venv\Scripts\python.exe -m pytest -m "not integration"`.
- Интеграционный сценарий — `backend/tests/test_integration_postgres.py`. Проверяй тестовую БД и порядок запуска по `docs/team/development/testing.md`.


## 2026-11-20 — D001 — NAV-04

- Операция — добавление
- Текст пункта — граница административного управления пользователями и настройки раздельных ключей проверяются в `backend/tests/test_access.py`. Схемы авторизации OpenAPI и проверка заголовков находятся в `backend/app/core/security.py`.
- Источник — `backend/tests/test_access.py`, `backend/app/core/config.py`, `backend/app/core/security.py`.


## 2026-11-20 — D002 — NAV-03

- Операция — замена
- Текст пункта — модели пользователей и событий находятся в models.py соответствующих модулей, миграции в `backend/alembic/versions/`. Compose предоставляет postgres и postgres-test. Из backend запускай быстрые тесты командой `..\.venv\Scripts\python.exe -m pytest -m "not integration"`. Интеграционный сценарий создаёт временную отдельную схему, применяет и сверяет миграции, проверяет HTTP API и откат до base, затем удаляет только свою схему. Порядок запуска приведён в командном руководстве.
- Источник — `backend/tests/test_integration_postgres.py`, `backend/alembic/env.py`, `docs/team/development/testing.md` и `docker-compose.yml`.


## 2026-11-20 — D003 — NAV-05

- Операция — добавление
- Текст пункта — общие ограничения PostgreSQL для HTTP-ввода находятся в `backend/app/core/validation.py`, проверка содержимого JSONB — в `backend/app/modules/integrations/schemas.py`. Некорректный ввод проверяет test_validation.py, параллельную запись и повторы — test_integration_postgres.py.
- Источник — `backend/tests/test_validation.py` и `backend/tests/test_integration_postgres.py`.


## 2026-11-20 — D004 — NAV-06

- Операция — добавление
- Текст пункта — классы предметных ошибок размещаются в exceptions.py модуля users или integrations. Базовый AppError и преобразование исключений в HTTP-ответ находятся в ядре.
- Источник — `backend/app/core/exceptions.py`, `backend/app/modules/users/exceptions.py` и `backend/app/modules/integrations/exceptions.py`.


## 2026-11-20 — D005 — NAV-07

- Операция — добавление
- Текст пункта — из backend запускай `python -m app`, при разработке можно добавить --reload. Точка входа читает APP_HOST и APP_PORT, на Windows задаёт SelectorEventLoop для Psycopg. Сам объект ASGI остаётся в app.main:app.
- Источник — `backend/app/__main__.py`, `docs/team/development/local-setup.md`.
