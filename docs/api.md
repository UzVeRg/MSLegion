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

## Callbacks

### `POST /api/v1/callbacks/events`

Требует заголовок `X-Callback-Key`.

Пример тела:

```json
{
  "source": "manual-test",
  "event_id": "event-001",
  "event_type": "ping",
  "payload": {
    "value": 1
  }
}
```

Успех: `200 OK`.

Повторная отправка того же сочетания `source` и `event_id` также возвращает
`200 OK`, но поле `duplicate` становится `true` и новая запись не создаётся.

## Admin

Административные endpoints требуют заголовок `X-Admin-Key`.

### `GET /api/v1/admin/status`

Возвращает состояние базы данных и количество основных записей.

### `GET /api/v1/admin/callbacks`

Возвращает историю входящих callback-событий.

Поддерживает `offset`, `limit`, `source` и `event_type`.
