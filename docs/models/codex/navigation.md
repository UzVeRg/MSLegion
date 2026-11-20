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


## 2026-11-20 — D006 — NAV-08

- Операция — добавление
- Текст пункта — CI backend определён в `.github/workflows/backend.yml`. На push и pull request запускаются Ruff и весь pytest с PostgreSQL 17 для всех поддерживаемых минорных версий Python. Фикстура асинхронного HTTP-клиента быстрых тестов находится в `backend/tests/conftest.py`.
- Источник — `.github/workflows/backend.yml`, `backend/tests/conftest.py` и `docs/team/development/testing.md`.


## 2026-11-20 — D007 — NAV-09

- Операция — добавление
- Текст пункта — /openapi.json описывает схемы ключей и ответы с ошибками. ErrorEnvelope в ядре используется и при формировании ответа, и при генерации контракта FastAPI. Соответствие спецификации проверяет test_request_context.py.
- Источник — `backend/app/core/exceptions.py`, маршрутизаторы модулей и `backend/tests/test_request_context.py`.


## 2026-11-20 — D008 — NAV-01

- Операция — замена
- Текст пункта — объект FastAPI и его жизненный цикл находятся в `backend/app/main.py`, команда запуска — в `backend/app/__main__.py`. Общий маршрутизатор, /health и /ready — в `backend/app/api/router.py`. Настройки — `backend/app/core/config.py` и `.env.example`, ключи — security.py. База ORM — `backend/app/core/models.py`, движок и сессии — database.py, регистрация моделей для миграций — `backend/alembic/env.py`. Отдельный журнал приложения включается на время lifespan, освобождение пула выполняется при выходе. Общие ошибки и контекст запроса — exceptions.py и middleware.py ядра.
- Источник — `backend/app/core/logging.py`, `backend/app/core/models.py`, `backend/app/main.py`, `backend/tests/test_lifespan.py` и `backend/tests/test_request_context.py`.


## 2026-11-20 — D009 — NAV-10

- Операция — добавление
- Текст пункта — справка CLI находится в `backend/app/__main__.py`, описания проверок в OpenAPI — в `backend/app/api/router.py`, сообщения журнала приложения — в `backend/app/core/middleware.py` и `backend/app/core/exceptions.py`, а поля JSON-журнала — в `backend/app/core/logging.py`. Пояснения ошибок также находятся в настройках, проверке ключей и модулях users и integrations. Шаблон комментария новой миграции находится в `backend/alembic/script.py.mako`. Правило языка приведено в `AGENTS.md` и `docs/team/README.md`.
- Источник — перечисленные исходники и `docs/team/reference/api.md`.


## 2026-11-20 — D010 — NAV-11

- Операция — добавление
- Текст пункта — проверка подписи и времени Telegram initData находится в `backend/app/modules/auth/telegram.py`, тесты — в `backend/tests/test_telegram_init_data.py`.
- Источник — `backend/app/modules/auth/telegram.py` и `backend/tests/test_telegram_init_data.py`.


## 2026-11-20 — D011 — NAV-11

- Операция — замена
- Текст пункта — проверка подписи и времени Telegram initData находится в `backend/app/modules/auth/telegram.py`, привязка личности к UUID — в `backend/app/modules/auth/service.py`. Миграция `20261120_0003` добавляет признак подтверждения к users. Административный маршрут подтверждения находится в `backend/app/modules/users/router.py`. Тесты проверки подписи и сценария PostgreSQL находятся в `backend/tests/test_telegram_init_data.py` и `backend/tests/test_integration_postgres.py`.
- Источник — указанные исходники и `docs/team/reference/api.md`.


## 2026-11-20 — D012 — NAV-12

- Операция — добавление
- Текст пункта — HTTP-вход Telegram, собственный профиль и выход находятся в `backend/app/modules/auth/router.py`. Выдача токена и транзакции — в service.py, проверка действующей сессии и отзыв — в repository.py, модель — в models.py того же модуля. Таблицу user_sessions добавляет миграция `20261120_0004`, секрет TELEGRAM_BOT_TOKEN читается из настроек ядра. Контракт Bearer и режим без токена бота покрывает `backend/tests/test_auth.py`, полный сценарий — `backend/tests/test_integration_postgres.py`.
- Источник — указанные исходники, `backend/app/core/config.py` и `docs/team/reference/api.md`.


## 2026-11-20 — D013 — NAV-03

- Операция — замена
- Текст пункта — модели пользователей, событий и сессий находятся в models.py соответствующих модулей, миграции в `backend/alembic/versions/`. Compose предоставляет postgres и postgres-test. Из backend запускай быстрые тесты командой `..\.venv\Scripts\python.exe -m pytest -m "not integration"`. PostgreSQL-сценарии используют отдельные временные схемы, проверяют миграции и откат до base, привязку Telegram и жизненный цикл сессий, затем удаляют только свои схемы. Порядок запуска приведён в командном руководстве.
- Источник — `backend/tests/test_integration_postgres.py`, `backend/alembic/env.py`, `docs/team/development/testing.md` и `docker-compose.yml`.


## 2026-11-20 — D014 — NAV-04

- Операция — замена
- Текст пункта — проверки ключей X-Admin-Key и X-Callback-Key находятся в `backend/app/core/security.py`, а схема пользовательского Bearer и её зависимость — в `backend/app/modules/auth/router.py`. Раздельные ключи проверяет `backend/tests/test_access.py`. Сценарий сессий в `backend/tests/test_integration_postgres.py` предъявляет действующую пользовательскую сессию каждому служебному маршруту и ожидает отказ.
- Источник — указанные исходники и `docs/team/reference/api.md`.


## 2026-11-20 — D015 — NAV-08

- Операция — замена
- Текст пункта — CI backend определён в `.github/workflows/backend.yml`. На push и pull request запускаются Ruff и весь pytest с PostgreSQL 17 для всех поддерживаемых минорных версий Python. Фикстура асинхронного HTTP-клиента быстрых тестов находится в `backend/tests/conftest.py`. Mini App проверяет `.github/workflows/frontend.yml` через npm ci, Vitest и сборку с проверкой типов.
- Источник — оба workflow и `docs/team/development/testing.md`.


## 2026-11-20 — D016 — NAV-13

- Операция — добавление
- Текст пункта — конфигурация HTTPS-стенда находится в `compose.staging.yml`, `deploy/staging/Caddyfile`, `backend/Dockerfile` и `.env.staging.example`. Caddy отдаёт frontend/dist и проксирует /api, /health и /ready в API. Compose применяет миграции при запуске API и проверяет /ready перед запуском Caddy. Порядок запуска, настройки кнопки Telegram и восстановления отдельной БД — в командном руководстве.
- Источник — указанные файлы и `docs/team/development/staging.md`.


## 2026-11-20 — D017 — NAV-14

- Операция — добавление
- Текст пункта — модуль сообществ находится в `backend/app/modules/communities/`. Маршруты подключены в `backend/app/api/router.py`, модели зарегистрированы в `backend/alembic/env.py`. Подробности и сценарии проверок смотри в [communities.md](communities.md).
- Источник — указанные исходники, миграция `20261120_0005` и `docs/team/reference/api.md`.


## 2026-11-20 — D018 — NAV-14

- Операция — замена
- Текст пункта — модуль сообществ и регистрации серверов находится в `backend/app/modules/communities/`. Маршруты подключены в `backend/app/api/router.py`, модели зарегистрированы в `backend/alembic/env.py`. Подробности разграничения доступа смотри в [communities.md](communities.md).
- Источник — указанные исходники, миграции `20261120_0005` и `20261120_0006`, `docs/team/reference/api.md`.


## 2026-11-20 — D019 — NAV-15

- Операция — добавление
- Текст пункта — регистрация источника server-status и административный запуск обработки находятся в `backend/app/modules/integrations/router.py`, транзакционный обработчик — в processing.py того же модуля. Отдельный ключ SERVER_STATUS_API_KEY проверяется в `backend/app/core/security.py`. Миграция `20261120_0007` добавляет состояния обработки и поля наблюдения сервера. Проверки — в `backend/tests/test_integration_postgres.py`.
- Источник — указанные исходники и `docs/team/reference/api.md`.


## 2026-11-20 — D020 — NAV-16

- Операция — добавление
- Текст пункта — внутренний журнал находится в `backend/app/modules/domain_events/`, исходные записи создают сервис сообществ и обработчик статусов. Маршрут статистики сообщества использует запрос из communities/repository.py. Показатели очереди определены в integrations/repository.py и открыты через административный маршрут. Миграция журнала — `20261120_0008`.
- Источник — перечисленные исходники и `docs/team/reference/api.md`.


## 2026-11-20 — D021 — NAV-17

- Операция — добавление
- Текст пункта — публикации и изображения находятся в content_router.py, content_service.py и content_repository.py модуля communities. Миграция `20261120_0009` добавляет community_posts с двоичным полем изображения и ограничением формата и размера. В runtime-движке SQLAlchemy скрыты значения SQL-параметров.
- Источник — указанные исходники, `backend/app/core/database.py` и `docs/team/reference/api.md`.


## 2026-11-20 — D022 — NAV-18

- Операция — добавление
- Текст пункта — исторический отчёт сообщества использует `get_visible_activity` в communities/repository.py и записи domain_events. Диапазон UTC рассчитывается в communities/service.py. Доступ и агрегаты читаются одним SQL-запросом.
- Источник — `backend/app/modules/communities/`, `backend/app/modules/domain_events/models.py` и `docs/team/reference/api.md`.


## 2026-11-20 — D023 — NAV-13

- Операция — замена
- Текст пункта — Базовый HTTPS-стенд определяют `compose.staging.yml`, `deploy/staging/Caddyfile`, `backend/Dockerfile` и `.env.staging.example`. Caddy отдаёт frontend/dist и проксирует /api, /health и /ready в API. Compose применяет миграции до запуска API. На VPS `deploy/staging/compose.proxy.yml` подключает только web к общей сети прокси и снимает публикацию портов приложения. Сценарий `update.sh` развёртывает проверенный SHA, `backup.sh` создаёт дамп PostgreSQL, а `mslegion-backup.timer` задаёт расписание. Все сценарии и юниты находятся в `deploy/staging/`.
- Источник — указанные файлы и `docs/team/development/staging.md`.
