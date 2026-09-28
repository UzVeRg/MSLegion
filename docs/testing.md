# Тестирование backend

## Быстрые тесты

Обычный набор тестов не требует отдельной тестовой базы данных.

Из каталога `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -m "not integration"
```

## Интеграционный тест PostgreSQL

Интеграционный тест использует отдельный PostgreSQL:

```text
127.0.0.1:5434
database: mslegion_test
```

Рабочая база на `127.0.0.1:5432` не используется.

Из корня репозитория:

```powershell
docker compose up -d postgres-test
docker compose ps
```

Из каталога `backend`:

```powershell
$env:RUN_INTEGRATION_TESTS="true"
..\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:RUN_INTEGRATION_TESTS
```

На Windows интеграционный тест самостоятельно запускает async-сценарий через
`asyncio.SelectorEventLoop`, совместимый с async Psycopg.

Тест перед выполнением создаёт таблицы в `mslegion_test`, а после выполнения
удаляет их.

## Все тесты

После успешной отдельной проверки PostgreSQL можно выполнить оба набора:

```powershell
..\.venv\Scripts\python.exe -m pytest -m "not integration"

$env:RUN_INTEGRATION_TESTS="true"
..\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:RUN_INTEGRATION_TESTS
```
