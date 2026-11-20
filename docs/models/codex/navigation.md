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
