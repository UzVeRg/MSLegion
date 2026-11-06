# MSLegion

## Локальный запуск (Windows PowerShell)

Нужны Python 3.12–3.14 и Docker Desktop. Команды ниже выполняются из корня репозитория, если не указано иное.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
Copy-Item .env.example .env
docker compose up -d postgres
```

В `.env` заменить `ADMIN_API_KEY` и `CALLBACK_API_KEY`. При изменении пароля PostgreSQL обновить также `DATABASE_URL`.

### Backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000/docs

### Миграции (из `backend`)

```powershell
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "migration_name"
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```

### Тесты (из `backend`)

```powershell
..\.venv\Scripts\python.exe -m pytest -m "not integration"
```

Интеграционные тесты: [docs/testing.md](docs/testing.md).

### Frontend

Пока не реализован: `frontend/package.json` пуст. Команд запуска ещё нет.

## Отложено

- Платежи и экономика — до готовности основных пользовательских сценариев.
- Дополнительные игровые механики — до завершения базового MVP.
- Выделение микросервисов — до появления практической необходимости.
