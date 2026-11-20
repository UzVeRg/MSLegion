# Локальный запуск и миграции

## Подготовка в Windows PowerShell

Понадобятся Python 3.12–3.14 и запущенный Docker Desktop.

1. Из корня репозитория создайте виртуальное окружение и установите backend с зависимостями разработки.

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
   ```

2. Если файла `.env` ещё нет, создайте его из шаблона.

   ```powershell
   Copy-Item .env.example .env
   ```

   Задайте два разных случайных ключа `ADMIN_API_KEY` и `CALLBACK_API_KEY` в локальном `.env`. Сгенерировать каждый можно командой `py -c "import secrets; print(secrets.token_urlsafe(32))"`. Пустые значения и ключи из прежнего шаблона отключают доступ к соответствующим маршрутам (HTTP 401). Если меняете реквизиты PostgreSQL, согласуйте переменные `POSTGRES_*` с `DATABASE_URL`. Для интеграционных тестов согласуйте также `TEST_DATABASE_URL` с настройками тестового сервиса.

3. Запустите PostgreSQL и дождитесь состояния `healthy` в выводе `docker compose ps`.

   ```powershell
   docker compose up -d postgres
   docker compose ps
   ```

## Запуск backend

Из корня репозитория перейдите в `backend`, примените миграции и запустите API.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Готовность приложения и базы проверяет [GET /ready](http://127.0.0.1:8000/ready).
- Маршруты можно проверять в [интерактивной документации API](http://127.0.0.1:8000/docs).
- Запуск тестов описан в [руководстве по тестированию](testing.md).

Для frontend и Telegram-бота пока есть только заготовки.

## Изменение схемы базы

После изменения моделей из каталога `backend` создайте черновик миграции.

```powershell
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "migration_name"
```

Проверьте сгенерированные операции `upgrade` и `downgrade`. Затем примените миграцию к локальной базе и проверьте её текущую ревизию.

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```
