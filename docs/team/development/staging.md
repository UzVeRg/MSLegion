# HTTPS-стенд MSLegion

## Публичный стенд на VPS

Порядок подключения по SSH, выпуска, диагностики и восстановления базы приведён в [руководстве по VPS](vps.md). Для команды есть [готовый шаблон SSH](ssh_config.example). Дальше описан отдельный HTTPS-стенд для локальной проверки.

## Локальный запуск

Из корня репозитория соберите Mini App с Node.js 24.15 или новее в ветке 24.

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
if (-not (Test-Path .env.staging)) { Copy-Item .env.staging.example .env.staging }
```

Задайте в `.env.staging` два разных случайных пароля. `POSTGRES_PASSWORD` принадлежит роли `mslegion`, которая инициализирует базу и выполняет миграции. `APP_DATABASE_PASSWORD` принадлежит роли `mslegion_api`, под которой работают API и обработчик Telegram. При обновлении существующего тома сохраните прежний `POSTGRES_PASSWORD` и добавьте `APP_DATABASE_PASSWORD`. Для проверки входа из Telegram укажите токен отдельного тестового бота в `TELEGRAM_BOT_TOKEN`. При необходимости задайте разные `ADMIN_API_KEY`, `CALLBACK_API_KEY` и `SERVER_STATUS_API_KEY`.

```powershell
docker compose --env-file .env.staging -f compose.staging.yml up -d --build --wait
docker compose --env-file .env.staging -f compose.staging.yml ps --all
```

PostgreSQL использует отдельный том. Одноразовый сервис `migrate` обновляет схему и выдаёт права на таблицы. После его завершения с кодом 0 запускается API. Проверьте готовность по `/ready`. Caddy раздаёт `frontend/dist` и проксирует `/api`, `/health` и `/ready` с того же HTTPS-адреса.

По умолчанию стенд слушает только `127.0.0.1` и использует локальный сертификат для `localhost`. Для проверки на Windows можно передать корневой сертификат самому клиенту без изменения системного хранилища.

```powershell
$stagingRoot = Join-Path $env:TEMP 'mslegion-staging-root.crt'
docker compose --env-file .env.staging -f compose.staging.yml cp web:/data/caddy/pki/authorities/local/root.crt $stagingRoot
curl.exe --fail --cacert $stagingRoot https://localhost/ready
```

## Проверка отдельного стенда из Telegram

Укажите в `STAGING_SITE_ADDRESS` публичное DNS-имя, направленное на хост стенда, и задайте доступный извне адрес прослушивания в `STAGING_BIND_ADDRESS`. Откройте порты 80 и 443 на хосте. Caddy получает сертификат для домена и хранит его в отдельном томе. Перед настройкой бота проверьте, что `/` и `/ready` доступны по HTTPS с доверенным сертификатом. [Документация Caddy об автоматическом HTTPS](https://caddyserver.com/docs/automatic-https)

В BotFather настройте кнопку меню тестового бота на адрес Mini App. Для входа должен использоваться токен этого же бота в серверном окружении. Откройте кнопку в клиенте Telegram, дождитесь своего профиля, затем выйдите и проверьте повторный вход. [Кнопка меню в документации Telegram](https://core.telegram.org/bots/webapps#launching-mini-apps-from-the-menu-button)

## Локальная проверка восстановления PostgreSQL

Делайте проверку в базе с отдельным именем. В примере архив создаётся внутри контейнера и переносится через `docker compose cp`, чтобы PowerShell сохранял двоичное содержимое.

```powershell
$staging = @('compose', '--env-file', '.env.staging', '-f', 'compose.staging.yml')
$restoreDatabase = 'mslegion_restore_' + (Get-Date -Format 'yyyyMMddHHmmss')
$backupArchive = Join-Path $env:TEMP "$restoreDatabase.dump"
docker @staging exec -T postgres pg_dump -U mslegion -d mslegion_staging -Fc -f /tmp/staging.dump
docker @staging cp postgres:/tmp/staging.dump $backupArchive
docker @staging exec -T postgres createdb -U mslegion -T template0 $restoreDatabase
docker @staging cp $backupArchive postgres:/tmp/staging-restore.dump
docker @staging exec -T postgres pg_restore -U mslegion -d $restoreDatabase --exit-on-error --single-transaction --no-owner --no-privileges /tmp/staging-restore.dump
```

Сверьте ревизию Alembic, число записей и контрольные данные в исходной и восстановленной базе под ролью `mslegion`. Правила PostgreSQL ограничивают подключения `mslegion_api` базой `mslegion_staging`, в том числе после восстановления архива в отдельную базу. Для публикаций дополнительно сравните хеши изображений и записи внутреннего журнала. Архив сохраняйте вне репозитория. Если стенд принимает новые записи, сравнивайте с состоянием на момент создания дампа.
