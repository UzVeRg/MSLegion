# VPS MSLegion

| Параметр | Значение |
| --- | --- |
| Сервер | `2.26.120.47`, SSH `22/tcp`, Ubuntu 24.04 LTS |
| Публичный стенд | [mslegion.miniapp.silentoken.com](https://mslegion.miniapp.silentoken.com/), HTTPS `443/tcp`, HTTP `80/tcp` перенаправляет на HTTPS |
| Telegram | [@MSLegion_Bot](https://t.me/MSLegion_Bot), кнопка «Открыть MSLegion» |
| Репозиторий | [UzVeRg/MSLegion](https://github.com/UzVeRg/MSLegion), ветка `main` |

## Кто и как подключается

| Учётная запись | Доступ и назначение |
| --- | --- |
| `legioner` | Общая учётная запись команды. Каждый участник входит со своим SSH-ключом. Доступна рабочая копия `/srv/mslegion/repository`. Пользователь вне групп `sudo` и `docker`. У команды один Linux UID и общие права на файлы рабочей копии. |
| `root` | Администратор VPS. Docker, релизы, секреты, резервные копии, Caddy и управление SSH-ключами. Используйте свой уже настроенный административный доступ. У администратора есть подключение `NewPanelDE` в Termius. |

### Ключ и конфиг OpenSSH

1. На своём компьютере подготовьте личный ключ Ed25519. В примере `Legioner` — имя файла без расширения. Если ключ с таким именем уже есть, используйте его или выберите свободное имя. На запрос `ssh-keygen` задайте парольную фразу.
2. Передайте администратору только файл `Legioner.pub` или его строку. Администратор сверяет отпечаток и добавляет публичный ключ отдельной строкой в `/home/legioner/.ssh/authorized_keys`. Приватный файл остаётся у владельца ключа.
3. Вставьте блок из [шаблона SSH](ssh_config.example) в свой файл `config` без расширения. Если файла ещё нет, создайте его. Разместите блок перед общим `Host *`, если в нём заданы те же параметры.

| Что менять | Где и как |
| --- | --- |
| Файл `config` | Windows: `%USERPROFILE%\.ssh\config`. Linux/macOS: `~/.ssh/config`. |
| `Host mslegion` | Локальный псевдоним. Если выбрали другой, подставьте его в SSH и SCP. |
| `HostName`, `Port` | Адрес VPS и порт SSH. Меняются, если администратор переносит сервер или SSH. |
| `User` | Для команды `legioner`. Для отдельного административного блока `root`. |
| `IdentityFile` | Путь к своему приватному ключу. `~/.ssh/MSLegion/Legioner` на Windows соответствует `%USERPROFILE%\.ssh\MSLegion\Legioner`. Если путь содержит пробелы, заключите его в кавычки. |
| `IdentitiesOnly yes` | Для этого хоста SSH выбирает явно настроенные ключи. |
| `mslegion-root` | Необязательный локальный псевдоним администратора. Раскомментируйте блок только при наличии отдельно выданного root-ключа и задайте свой `IdentityFile`. |

Команды на Windows в PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh\MSLegion"
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\MSLegion\Legioner" -C "mslegion-имя"
ssh-keygen -lf "$env:USERPROFILE\.ssh\MSLegion\Legioner.pub"
notepad "$env:USERPROFILE\.ssh\config"
```

На Linux и macOS:

```bash
mkdir -p ~/.ssh/MSLegion
chmod 700 ~/.ssh ~/.ssh/MSLegion
ssh-keygen -t ed25519 -f ~/.ssh/MSLegion/Legioner -C "mslegion-имя"
ssh-keygen -lf ~/.ssh/MSLegion/Legioner.pub
${EDITOR:-nano} ~/.ssh/config
chmod 600 ~/.ssh/config
```

При первом входе сравните показанный отпечаток сервера с подтверждённым администратором. Отпечаток ключа **ED25519** этого VPS по проверенному SSH-соединению от 20.11.2026:

```text
SHA256:ikH3O9roWeaA6UWBItZO/8B42GSFfq8b4MyCNEmso+Q
```

Клиент сохраняет принятый ключ сервера в `~/.ssh/known_hosts`. При сообщении об изменении ключа сверьте новый отпечаток с администратором по доверенному каналу. [Параметры OpenSSH](https://man.openbsd.org/ssh_config)

### Команды для команды

Локально, после добавления вашего публичного ключа:

```bash
ssh -G mslegion
ssh mslegion
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=7 mslegion 'id; hostname'
ssh mslegion 'git -C /srv/mslegion/repository status --short --branch'
ssh -t mslegion 'cd /srv/mslegion/repository && exec bash -l'
```

Вход без псевдонима на Windows:

```powershell
ssh -i "$env:USERPROFILE\.ssh\MSLegion\Legioner" -o IdentitiesOnly=yes -p 22 legioner@2.26.120.47
```

Вход без псевдонима на Linux и macOS:

```bash
ssh -i ~/.ssh/MSLegion/Legioner -o IdentitiesOnly=yes -p 22 legioner@2.26.120.47
```

Для диагностики добавьте `-v` к `ssh mslegion`. `Permission denied (publickey)` обычно требует проверить `User`, `IdentityFile` и наличие вашего публичного ключа на VPS. `BatchMode=yes` отключает запросы ввода. Если приватный ключ защищён парольной фразой, для автоматизации заранее загрузите его в свой SSH-агент или выполните обычный интерактивный вход.

После входа под `legioner` проверьте рабочую копию перед обновлением. Согласуйте операции с другими участниками, которые могут работать в том же каталоге.

```bash
cd /srv/mslegion/repository
git status --short --branch
git branch --show-current
git log -1 --oneline
# Если рабочая копия чистая и выбрана main:
git pull --ff-only origin main
exit
```

При необходимости передайте обычный рабочий файл через личный подкаталог в home. В примере замените `имя` и `local-file.txt`:

```bash
ssh mslegion 'mkdir -p ~/exchange/имя'
scp ./local-file.txt mslegion:exchange/имя/
scp mslegion:exchange/имя/local-file.txt ./
```

Подкаталоги `legioner` доступны всем, кто использует эту учётную запись. Доступ к VPS по SSH и доступ к GitHub — отдельные настройки. Изменения для выпуска отправляйте на GitHub со своей рабочей машины.

### Управление доступом

Команды администратора в уже открытой root-сессии:

```bash
id legioner
stat -c '%a %U:%G %n' /home/legioner/.ssh /home/legioner/.ssh/authorized_keys
ssh-keygen -lf /home/legioner/.ssh/authorized_keys
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Ожидаемые владелец и права — `legioner:legioner`, `700` для `.ssh` и `600` для `authorized_keys`. При выдаче или отзыве доступа меняйте только строку ключа конкретного участника. Проверяйте новый вход во второй сессии, пока доступ администратора открыт.

Файл редактируют командой `${EDITOR:-nano} /home/legioner/.ssh/authorized_keys`. При подготовке нового VPS создайте каталог и файл, если их ещё нет. Исправьте владельца и права после записи публичных ключей:

```bash
install -d -o legioner -g legioner -m 700 /home/legioner/.ssh
touch /home/legioner/.ssh/authorized_keys
chown legioner:legioner /home/legioner/.ssh/authorized_keys
chmod 600 /home/legioner/.ssh/authorized_keys
```

Для задач Codex начинайте с `ssh -o BatchMode=yes -o StrictHostKeyChecking=yes mslegion 'id; hostname'`, затем сверяйте права и публичные проверки. Если задача требует root, используйте отдельно предоставленный администратором доступ. При временном доступе администратор может добавить отдельный публичный ключ с ограничениями и сроком действия. После работы удалите эту запись и проверьте, что временный ключ больше не принимается. Команды на изменение стенда выполняйте только в рамках порученной задачи.

## Где что находится на VPS

| Путь или имя | Назначение |
| --- | --- |
| `/srv/mslegion/repository` | Рабочая копия команды под `legioner`. Обновление этой копии само по себе не меняет стенд. |
| `/opt/mslegion-staging/source.git` | Отдельная копия Git для развёртывания от root. |
| `/opt/mslegion-staging/releases/<SHA>` | Сборки и Compose-файлы конкретных выпусков. `/opt/mslegion-staging/current` указывает на успешно развёрнутый выпуск. |
| `/etc/mslegion/staging.env` | Переменные окружения. `root:root`, права `600`. Родительский каталог имеет права `700`. В Git хранится шаблон `.env.staging.example`. |
| `/opt/caddy-remnawave/Caddyfile` | Общий публичный Caddy. Домен Mini App направлен на `mslegion-staging-web:80`. |
| `mslegion-staging` | Имя проекта Compose. Сервисы `postgres`, `api`, `web`. PostgreSQL 17 хранит базу `mslegion_staging` в томе `mslegion-staging_postgres_data`. |
| `remnawave-network` | Общая сеть публичного Caddy, указана в `STAGING_PROXY_NETWORK`. Из проекта к ней подключён только `web`. API и PostgreSQL используют сеть проекта, порты приложения на хосте не публикуются. |
| `/var/backups/mslegion` | Дампы PostgreSQL с правами `600`. Ежедневное копирование в 01:00 UTC, хранение 14 суток на VPS. |
| `/etc/systemd/system/mslegion-backup.{service,timer}` | Установленные юниты копирования. Исходники в `deploy/staging/`. |

## Как применять изменения

### Выпуск из Git

1. Проверьте изменения выбранного коммита из `main`, включая Compose, Dockerfile, сценарии и миграции. Подготовьте полный 40-символьный SHA.
2. Из root-сессии запустите скрипт из текущего выпуска. В примере замените `ПОЛНЫЙ_SHA`:

   ```bash
   bash /opt/mslegion-staging/current/deploy/staging/update.sh ПОЛНЫЙ_SHA
   readlink -f /opt/mslegion-staging/current
   ```

3. Скрипт проверяет принадлежность коммита к `main` и движение вперёд от текущего выпуска, собирает и тестирует frontend в контейнере Node.js, собирает API, создаёт дамп перед обновлением и ждёт готовности Compose. API применяет миграции при запуске. После успеха `current` указывает на выбранный SHA. Проверьте HTTPS и повторите вход из меню бота.

При сбое `current` остаётся на предыдущем выпуске, хотя контейнеры или схема уже могли измениться. Посмотрите `ps`, журналы и ревизию Alembic. После устранения причины можно повторить запуск того же SHA. Для возврата к предыдущему коду сначала проверьте его совместимость с фактической схемой БД и сохраните свежую копию БД. Скрипт обновления сам откат не выполняет.

Для первого запуска на новом VPS создайте под root каталоги `/opt/mslegion-staging` и `releases` с правами `700`, подготовьте Compose с поддержкой `!reset`, общую сеть прокси и защищённый `staging.env`. Клонируйте `git clone --bare --single-branch --branch main https://github.com/UzVeRg/MSLegion.git /opt/mslegion-staging/source.git` и запустите проверенную копию `update.sh` с нужным SHA. Публикуйте маршрут в Caddy после успешного ответа внутреннего `/ready`. Node.js на хосте не требуется.

### Диагностика и изменения окружения

Команды под root на VPS. Массив `compose` нужно заново объявить в каждой сессии Bash после обновления выпуска:

```bash
release=$(readlink -f /opt/mslegion-staging/current)
compose=(docker compose --env-file /etc/mslegion/staging.env
  -f "$release/compose.staging.yml" -f "$release/deploy/staging/compose.proxy.yml")
"${compose[@]}" config --quiet
"${compose[@]}" ps
"${compose[@]}" logs --tail=100 api web
"${compose[@]}" logs --tail=100 postgres
"${compose[@]}" exec -T api alembic current
docker exec caddy-remnawave wget -qO- http://mslegion-staging-web/ready
df -h /opt/mslegion-staging /var/backups/mslegion
```

Ожидаемый результат — три здоровых сервиса и `{"status":"ok","database":"ok"}` на `/ready`. С ноутбука или любого внешнего клиента проверьте публичные ответы. В PowerShell используйте `curl.exe` вместо `curl`:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' https://mslegion.miniapp.silentoken.com/
curl -fsS https://mslegion.miniapp.silentoken.com/health
curl -fsS https://mslegion.miniapp.silentoken.com/ready
```

### Включение Telegram-уведомлений

После выпуска с миграцией `20261120_0010` установите таймер в root-сессии. Он использует серверный `TELEGRAM_BOT_TOKEN` из существующего окружения контейнера API.

```bash
release=$(readlink -f /opt/mslegion-staging/current)
units="$release/deploy/staging"
systemd-analyze verify "$units/mslegion-telegram-notifications.service" "$units/mslegion-telegram-notifications.timer"
install -m 644 "$units/mslegion-telegram-notifications.service" "$units/mslegion-telegram-notifications.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now mslegion-telegram-notifications.timer
systemctl list-timers --all mslegion-telegram-notifications.timer
journalctl -u mslegion-telegram-notifications.service -n 30 --no-pager
```

Для сквозной проверки откройте Mini App под тестовым владельцем, включите уведомления и разрешите личные сообщения. Если клиент не показывает запрос разрешения, откройте чат с ботом и нажмите «Старт». Передайте два наблюдения с разным статусом для тестового сервера. Первое задаёт исходный статус, после второго бот присылает уведомление. Для проверки отключения выключите подписку и повторите переход.

В первой команде на Windows замените `/dev/null` на `NUL`. При ошибке HTTPS проверьте DNS, состояние общего Caddy и ответ внутреннего `/ready` отдельно.

В PowerShell адрес проверяют командой `Resolve-DnsName mslegion.miniapp.silentoken.com -Type A`. Ожидается `2.26.120.47`. На VPS сертификат можно проверить с учётом имени сайта:

```bash
openssl s_client -connect 127.0.0.1:443 -servername mslegion.miniapp.silentoken.com \
  -verify_hostname mslegion.miniapp.silentoken.com -verify_return_error </dev/null
```

Значения окружения меняйте в `/etc/mslegion/staging.env` от root. Для изменения *ключей API или токена бота* выполните `"${compose[@]}" config --quiet && "${compose[@]}" up -d --wait api` и перепроверьте `/ready` и затронутый сценарий. Compose применяет новое окружение при пересоздании API. Пароль действующей PostgreSQL меняют согласованно в самой роли БД и окружении: одно редактирование `POSTGRES_PASSWORD` не меняет пароль в уже созданной БД. Используйте `config --quiet`, чтобы проверять Compose без вывода подставленных значений. [Проверка конфигурации Compose](https://docs.docker.com/reference/cli/docker/compose/config/)

| Переменная | Где применяется |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Проверка подписи данных входа. Должен соответствовать боту, из которого открывается Mini App. |
| `ADMIN_API_KEY`, `CALLBACK_API_KEY`, `SERVER_STATUS_API_KEY` | Раздельные ключи административных маршрутов, приёма событий и источника статусов серверов. |
| `POSTGRES_PASSWORD` | Пароль роли `mslegion`. Используйте символы из шаблона staging, подходящие для URL подключения. |
| `STAGING_PROXY_NETWORK` | Имя существующей сети Docker внешнего Caddy. |
| `STAGING_SITE_ADDRESS`, `STAGING_BIND_ADDRESS`, `STAGING_HTTP_PORT`, `STAGING_HTTPS_PORT` | Параметры базового Compose. На VPS дополнение задаёт для web адрес `:80` без публикации портов, а публичные домен и TLS задаются в общем Caddy. |

Перед передачей журналов проверьте, что они не содержат значений секретов, токенов сессий и данных входа Telegram.

### Маршрут и сертификат Caddy

Обычные выпуски MSLegion не требуют правки общего Caddyfile. Для фактического домена используется такой блок:

```caddyfile
mslegion.miniapp.silentoken.com {
    reverse_proxy mslegion-staging-web:80
}
```

Если меняете маршрут или домен, сначала сохраните копию файла и проверьте кандидат целиком:

```bash
docker exec -i caddy-remnawave caddy validate --config /dev/stdin --adapter caddyfile < /путь/к/кандидату
```

После проверки запишите содержимое кандидата в существующий `/opt/caddy-remnawave/Caddyfile`, сохранив inode: контейнер монтирует этот файл отдельно. Затем примените конфигурацию и проверьте доступность своего маршрута и затронутых сайтов:

```bash
docker exec caddy-remnawave caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
docker logs --since 10m caddy-remnawave 2>&1 | grep -F mslegion.miniapp.silentoken.com
```

При неудачном применении верните содержимое из копии в тот же файл, снова выполните `caddy reload` и проверьте состояние общего прокси. [Документация Caddy](https://caddyserver.com/docs/running)

### Резервные копии PostgreSQL

Команды под root на VPS:

```bash
systemctl list-timers --all mslegion-backup.timer
systemctl start mslegion-backup.service
systemctl show mslegion-backup.service -p Result -p ExecMainStatus
journalctl -u mslegion-backup.service -n 30 --no-pager
ls -lh /var/backups/mslegion/
```

Ожидаемый результат разового запуска — `Result=success`, `ExecMainStatus=0` и новый `staging-*.dump`. Если обновляли юниты в Git, после выпуска установите проверенные версии из текущего релиза:

```bash
cd /opt/mslegion-staging/current/deploy/staging
systemd-analyze verify mslegion-backup.service mslegion-backup.timer
install -m 644 mslegion-backup.service mslegion-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now mslegion-backup.timer
systemctl restart mslegion-backup.timer
systemctl list-timers --all mslegion-backup.timer
```

Чтобы проверить выбранный дамп, откройте root-сессию, объявите массив `compose` из диагностики и замените `ИМЯ_АРХИВА.dump` фактическим именем. Команды создают отдельную временную БД и удаляют её при завершении:

```bash
(
  set -e
  archive=/var/backups/mslegion/ИМЯ_АРХИВА.dump
  test -s "$archive"
  restore_db="mslegion_restore_$(date -u +%Y%m%d%H%M%S)_$$"
  "${compose[@]}" exec -T postgres createdb -U mslegion -T template0 "$restore_db"
  trap '"${compose[@]}" exec -T postgres dropdb -U mslegion "$restore_db"' EXIT
  "${compose[@]}" exec -T postgres pg_restore -U mslegion -d "$restore_db" \
    --exit-on-error --single-transaction --no-owner --no-privileges < "$archive"
  "${compose[@]}" exec -T postgres psql -U mslegion -d "$restore_db" -v ON_ERROR_STOP=1 \
    -c 'SELECT version_num FROM alembic_version; SELECT count(*) FROM users;'
)
```

Сверяйте ревизию, счётчики и контрольные записи с состоянием на момент копирования. Восстановление в активную базу планируйте отдельно с остановкой записи и проверкой совместимости схемы. [Документация pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html)
