# MSLegion API

Текущий API предназначен для разработки и административной проверки backend без
пользовательского интерфейса.

## System

### `GET /health`

Проверяет, что процесс FastAPI запущен.

Успех: `200 OK`.

### `GET /ready`

Проверяет доступность PostgreSQL.

Успех: `200 OK`.
Если база данных недоступна: `503 Service Unavailable`.

## Users

Префикс: `/api/v1/users`.

### `POST /api/v1/users`

Создаёт пользователя.

Пример тела:

```json
{
  "telegram_id": 123456789,
  "display_name": "Test User"
}
```

`telegram_id` опционален. Внутренним идентификатором пользователя является UUID.

Успех: `201 Created`.
Повторный `telegram_id`: `409 Conflict`.

### `GET /api/v1/users`

Возвращает список пользователей.

Query parameters:

- `offset` — от `0`;
- `limit` — от `1` до `100`, по умолчанию `50`.

Успех: `200 OK`.

### `GET /api/v1/users/{user_id}`

Возвращает одного пользователя по внутреннему UUID.

Успех: `200 OK`.
Пользователь не найден: `404 Not Found`.
