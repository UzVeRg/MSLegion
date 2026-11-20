# HTTPS-стенд MSLegion

## Публичный стенд на VPS

Стенд доступен по адресу [mslegion.miniapp.silentoken.com](https://mslegion.miniapp.silentoken.com/) и через кнопку «Открыть MSLegion» у [@MSLegion_Bot](https://t.me/MSLegion_Bot).

`legioner` работает в `/srv/mslegion/repository`. Администратор развёртывает проверенные коммиты из отдельной копии Git в `/opt/mslegion-staging/source.git`. Каталог `/opt/mslegion-staging` доступен только root, активная сборка находится по ссылке `/opt/mslegion-staging/current`. Конфигурация окружения хранится в `/etc/mslegion/staging.env` с владельцем `root:root` и правами `600`. Каталог `/etc/mslegion` имеет права `700`.

`deploy/staging/compose.proxy.yml` подключает только веб-контейнер к общей сети Docker `remnawave-network`, заданной в `STAGING_PROXY_NETWORK`. Публичные 80 и 443 обслуживает `caddy-remnawave`. В `/opt/caddy-remnawave/Caddyfile` домен направлен на `mslegion-staging-web:80`, сертификатом управляет внешний Caddy. Перед правкой сохраните копию файла, проверьте всю конфигурацию командой `caddy validate` внутри контейнера и примените через `caddy reload`. Caddyfile смонтирован отдельным файлом. При записи новой конфигурации и восстановлении сохраняйте исходный файл и меняйте его содержимое.

Для первого развёртывания установите Docker и Compose с поддержкой `!reset`. Создайте `/opt/mslegion-staging/releases` с правами `700`, клонируйте репозиторий в `/opt/mslegion-staging/source.git` командой `git clone --bare --single-branch --branch main` с адресом GitHub и путём назначения. Запустите от root копию `update.sh` из проверенного коммита. Node.js хоста для этого режима не нужен.

Для обновления проверьте изменения выбранного коммита `main`, включая Dockerfile, Compose и сценарии. Затем передайте полный SHA от root.

```bash
bash /opt/mslegion-staging/current/deploy/staging/update.sh <проверенный-SHA>
```

Сценарий собирает и тестирует frontend в контейнере Node.js, собирает API, сохраняет дамп перед обновлением и ожидает готовности Compose. При сбое ссылка `current` сохраняет прежнее значение. Проверьте состояние контейнеров и ревизию Alembic перед повтором. Для возврата приложения проверьте совместимость прежней версии со схемой БД и используйте прежний каталог выпуска. После обновления проверьте HTTPS-ответы `/`, `/health` и `/ready`.

Файлы `mslegion-backup.service` и `mslegion-backup.timer` из `deploy/staging/` устанавливаются в `/etc/systemd/system`. После `systemctl daemon-reload` включите расписание командой `systemctl enable --now mslegion-backup.timer`. Таймер запускает копирование ежедневно в 01:00 UTC, архивы хранятся 14 суток в `/var/backups/mslegion` на VPS. Разовый запуск выполняется командой `systemctl start mslegion-backup.service`. Проверяйте расписание и результаты через `systemctl list-timers mslegion-backup.timer` и `journalctl -u mslegion-backup.service`.

## Запуск

Из корня репозитория соберите Mini App с Node.js 24.15 или новее в ветке 24.

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
if (-not (Test-Path .env.staging)) { Copy-Item .env.staging.example .env.staging }
```

Задайте `POSTGRES_PASSWORD` в `.env.staging`. Используйте случайное значение из букв, цифр, дефисов и подчёркиваний, так как пароль входит в URL соединения. Для теста из Telegram укажите токен отдельного тестового бота в `TELEGRAM_BOT_TOKEN`. При необходимости задайте разные `ADMIN_API_KEY`, `CALLBACK_API_KEY` и `SERVER_STATUS_API_KEY`.

```powershell
docker compose --env-file .env.staging -f compose.staging.yml up -d --build --wait
docker compose --env-file .env.staging -f compose.staging.yml ps
```

PostgreSQL использует отдельный том. API применяет миграции перед запуском и становится готовым после успешного ответа `/ready`. Caddy раздаёт `frontend/dist` и проксирует `/api`, `/health` и `/ready` с того же HTTPS-адреса.

По умолчанию стенд слушает только `127.0.0.1` и использует локальный сертификат для `localhost`. Для проверки на Windows можно передать корневой сертификат самому клиенту без изменения системного хранилища.

```powershell
$stagingRoot = Join-Path $env:TEMP 'mslegion-staging-root.crt'
docker compose --env-file .env.staging -f compose.staging.yml cp web:/data/caddy/pki/authorities/local/root.crt $stagingRoot
curl.exe --fail --cacert $stagingRoot https://localhost/ready
```

## Проверка из Telegram

Укажите в `STAGING_SITE_ADDRESS` публичное DNS-имя, направленное на хост стенда, и задайте доступный извне адрес прослушивания в `STAGING_BIND_ADDRESS`. Откройте порты 80 и 443 на хосте. Caddy получает сертификат для домена и хранит его в отдельном томе. Перед настройкой бота проверьте, что `/` и `/ready` доступны по HTTPS с доверенным сертификатом. [Документация Caddy об автоматическом HTTPS](https://caddyserver.com/docs/automatic-https)

В BotFather настройте кнопку меню тестового бота на адрес Mini App. Для входа должен использоваться токен этого же бота в серверном окружении. Откройте кнопку в клиенте Telegram, дождитесь своего профиля, затем выйдите и проверьте повторный вход. [Кнопка меню в документации Telegram](https://core.telegram.org/bots/webapps#launching-mini-apps-from-the-menu-button)

## Проверка восстановления PostgreSQL

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

Сверьте ревизию Alembic, число записей и контрольные данные в исходной и восстановленной базе. Для публикаций дополнительно сравните хеши изображений и записи внутреннего журнала. Архив сохраняйте вне репозитория. Если стенд принимает новые записи, сравнивайте с состоянием на момент создания дампа.
