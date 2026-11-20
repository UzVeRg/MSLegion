# Mini App MSLegion

## FRONT-01 — Вход и профиль

- Точка входа Vite — `frontend/index.html`, подключение Vue — `frontend/src/main.ts`.
- `frontend/src/telegram.ts` передаёт исходную строку `Telegram.WebApp.initData`. Профиль загружается из API после серверной проверки. Токен хранится в памяти компонента.
- Состояния входа, профиля, истечения сессии и выхода — `frontend/src/App.vue`. HTTP-запросы — `frontend/src/api.ts`.
- Сборка, тесты и прокси разработки — `frontend/package.json` и `frontend/vite.config.ts`. При развёртывании раздавайте `frontend/dist` и проксируйте `/api` с того же адреса.
- Проверки — `frontend/src/App.test.ts` и `.github/workflows/frontend.yml`. Команды запуска описаны в `docs/team/development/local-setup.md` и `docs/team/development/testing.md`.
