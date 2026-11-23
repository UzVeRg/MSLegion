# Mini App MSLegion

## FRONT-01 — Вход и профиль

- Точка входа Vite — `frontend/index.html`, подключение Vue — `frontend/src/main.ts`.
- `frontend/src/telegram.ts` передаёт исходную строку `Telegram.WebApp.initData`. Профиль загружается из API после серверной проверки. Токен хранится в памяти компонента.
- Состояния входа, профиля, истечения сессии и выхода — `frontend/src/App.vue`. HTTP-запросы — `frontend/src/api.ts`.
- Сборка, тесты и прокси разработки — `frontend/package.json` и `frontend/vite.config.ts`. При развёртывании раздавайте `frontend/dist` и проксируйте `/api` с того же адреса.
- Проверки — `frontend/src/App.test.ts` и `.github/workflows/frontend.yml`. Команды запуска описаны в `docs/team/development/local-setup.md` и `docs/team/development/testing.md`.


## 2026-11-20 — D001 — FRONT-02

- Операция — добавление
- Текст пункта — на HTTPS-стенде Caddy раздаёт frontend/dist и проксирует /api с того же адреса. Адрес стенда и настройки бота описаны в командном руководстве. Проверка публичного запуска в клиенте Telegram ещё впереди.
- Источник — `deploy/staging/Caddyfile`, `compose.staging.yml` и `docs/team/development/staging.md`.


## 2026-11-20 — D002 — FRONT-03

- Операция — добавление
- Текст пункта — профиль переключает настройку личных уведомлений через PUT /api/v1/auth/me/telegram-notifications. При включении поддерживаемый Telegram-клиент запрашивает разрешение на личные сообщения.
- Источник — `frontend/src/App.vue`, `frontend/src/telegram.ts` и `frontend/src/App.test.ts`.


## 2026-11-23 — D003 — FRONT-04

- Операция — добавление
- Текст пункта — на текущем экране Mini App раздел «Настройки → Тема» переключает четыре темы: «Чёрный графит» по умолчанию, «Неоготика», «Сеть» и «Подземный клуб». Выбор хранится локально под ключом mslegion.theme. Тема задаёт CSS-переменные цвета и формы. Сохранённые макеты служат референсом для будущих главной и открытого меню.
- Источник — `frontend/src/App.vue`, `frontend/src/style.css`, `frontend/src/App.test.ts` и `docs/team/design/mini-app-themes.md`.
