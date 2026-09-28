# MSLegion

Первоначальный backend-каркас проекта MSLegion.

## Текущий этап

Сейчас реализуется headless backend без пользовательского интерфейса и Telegram-бота.
Первый этап должен дать рабочие HTTP endpoints, PostgreSQL, миграции, административные
операции и callback endpoints.

## Локальный запуск

Требования:

- Python 3.12+
- Docker / Docker Compose

Создайте локальный файл окружения:

```powershell
Copy-Item .env.example .env
```

Поднимите PostgreSQL:

```powershell
docker compose up -d postgres
```

Создайте виртуальное окружение:

```powershell
py -m venv .venv
```

Установите backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
```

Запустите API из каталога `backend`:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Проверка:

- `GET http://127.0.0.1:8000/health` — процесс API работает.
- `GET http://127.0.0.1:8000/ready` — API имеет соединение с PostgreSQL.
- `http://127.0.0.1:8000/docs` — Swagger UI.

## Тесты

Из каталога `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest
```
