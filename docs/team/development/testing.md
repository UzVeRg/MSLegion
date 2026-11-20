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

Проверьте, что `TEST_DATABASE_URL` указывает на отдельную тестовую базу. Роль теста должна иметь право создавать схемы. Каждый прогон создаёт собственную схему со случайным именем, устанавливает для соединений её `search_path` и удаляет только эту схему. Проверка проходит путь от пустой схемы через `alembic upgrade head`, сравнение моделей с миграциями и HTTP-запросы до `alembic downgrade base`.

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

Интеграционный тест запускает асинхронный сценарий через
`asyncio.SelectorEventLoop`, совместимый с асинхронным Psycopg на Windows.

## Все тесты

После успешной отдельной проверки PostgreSQL можно выполнить оба набора:

```powershell
..\.venv\Scripts\python.exe -m pytest -m "not integration"

$env:RUN_INTEGRATION_TESTS="true"
..\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:RUN_INTEGRATION_TESTS
```
