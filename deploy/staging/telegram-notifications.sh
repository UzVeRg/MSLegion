#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID != 0 ]]; then
    echo 'Запустите обработку уведомлений от root.' >&2
    exit 2
fi

base=/opt/mslegion-staging
exec 9>"$base/update.lock"
flock -s -n 9 || exit 0
release=$(readlink -f "$base/current")
compose=(docker compose --env-file /etc/mslegion/staging.env
    -f "$release/compose.staging.yml" -f "$release/deploy/staging/compose.proxy.yml")
"${compose[@]}" exec -T api python -m app.telegram.worker
