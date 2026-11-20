# Контекст MSLegion

Базовая запись от 20.11.2026. Применяй дополнения по правилам [указателя](README.md).

## PROJ-01 — Назначение и архитектура

MSLegion — проект с одним основным интерфейсом Telegram Mini App и модульным монолитом FastAPI. Исходный список из 50 идей служит продуктовым каталогом. Telegram-бот запланирован как адаптер. PostgreSQL хранит постоянные данные.

Источник: `docs/team/architecture/overview.md`.

## PROJ-02 — Реализованное состояние

Backend предоставляет проверки `/health` и `/ready`, создание и чтение пользователей, приём и просмотр событий интеграций, административный статус. Ключи API проверяются на маршрутах из групп callbacks и admin. Пользовательские маршруты пока доступны без пользовательской авторизации. `frontend/package.json` и `backend/app/telegram/bot.py` — пустые заготовки.

Источник: `backend/app/api/router.py`, маршрутизаторы в `backend/app/modules/`, `frontend/package.json`, `backend/app/telegram/bot.py`.

## PROJ-03 — Стек и приоритеты

Основной стек — Python 3.12–3.14, FastAPI, асинхронные SQLAlchemy и Psycopg, PostgreSQL, Alembic. Ближайшие задачи — защита пользовательского API, Telegram-авторизация, сессии, профиль и роли. Для Mini App запланированы Vue 3, TypeScript и Vite. Платежи, экономика и выделение сервисов отложены.

Источник: `backend/pyproject.toml`, `docs/team/architecture/stack.md`, `docs/team/planning/roadmap.md`.


## 2026-11-20 — D001 — PROJ-02

- Операция — замена
- Текст пункта — backend предоставляет публичные проверки /health и /ready. Создание и чтение пользователей, административный статус и история событий требуют X-Admin-Key, приём события требует отдельный X-Callback-Key. Незаданный или старый шаблонный ключ отключает соответствующий доступ. Telegram-вход, пользовательский профиль, frontend и бот ещё предстоит реализовать.
- Источник — `backend/app/core/config.py`, `backend/app/core/security.py`, маршрутизаторы в `backend/app/modules/` и `docs/team/reference/api.md`.


## 2026-11-20 — D002 — PROJ-04

- Операция — добавление
- Текст пункта — /health проверяет процесс, /ready проверяет доступ к столбцам ORM обеих рабочих таблиц через сессию запроса. Административный статус получает оба счётчика в переданной сессии и при ошибке базы возвращает unavailable с пустыми счётчиками.
- Источник — `backend/app/api/router.py`, `backend/app/modules/admin/service.py`, `docs/team/reference/api.md`.
