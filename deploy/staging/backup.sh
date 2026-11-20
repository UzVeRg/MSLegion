#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $EUID != 0 ]]; then
    echo 'Запустите резервное копирование от root.' >&2
    exit 2
fi

release=$(readlink -f /opt/mslegion-staging/current)
backups=/var/backups/mslegion
install -d -m 700 "$backups"
exec 8>"$backups/.lock"
flock 8

compose=(docker compose --env-file /etc/mslegion/staging.env -f "$release/compose.staging.yml"
    -f "$release/deploy/staging/compose.proxy.yml")
archive="$backups/staging-$(date -u +%Y%m%dT%H%M%S%NZ).dump"
temporary=$(mktemp "$backups/.staging.XXXXXXXX")
trap 'rm -f -- "$temporary"' EXIT

"${compose[@]}" exec -T postgres pg_dump -U mslegion -d mslegion_staging -Fc </dev/null > "$temporary"
"${compose[@]}" exec -T postgres pg_restore --list < "$temporary" >/dev/null
mv -T "$temporary" "$archive"
find "$backups" -maxdepth 1 -type f -name 'staging-*.dump' -mtime +13 -delete
echo "Создан архив PostgreSQL: $archive"
