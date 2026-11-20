#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $EUID != 0 || $# != 1 || ! $1 =~ ^[0-9a-f]{40}$ ]]; then
    echo 'Запустите от root и укажите полный проверенный SHA коммита из main.' >&2
    exit 2
fi

revision=$1
base=/opt/mslegion-staging
source_repo=$base/source.git
release=$base/releases/$revision
env_file=/etc/mslegion/staging.env

exec 9>"$base/update.lock"
flock -n 9
git --git-dir="$source_repo" fetch --no-tags origin refs/heads/main
git --git-dir="$source_repo" merge-base --is-ancestor "$revision" FETCH_HEAD

current_revision=
if [[ -L $base/current ]]; then
    current_revision=$(basename "$(readlink -f "$base/current")")
    git --git-dir="$source_repo" merge-base --is-ancestor "$current_revision" "$revision"
fi

if [[ ! -d $release ]]; then
    build_dir=$(mktemp -d "$base/releases/.build.XXXXXXXX")
    trap 'if [[ -d $build_dir ]]; then rm -rf -- "$build_dir"; fi' EXIT
    git --git-dir="$source_repo" archive "$revision" | tar -x -C "$build_dir"
    docker run --rm --mount "type=bind,src=$build_dir/frontend,dst=/app" -w /app \
        node:24.21.0-bookworm-slim sh -ec 'npm ci --no-audit --no-fund && npm test && npm run build'
    test -s "$build_dir/frontend/dist/index.html"
    mv -T "$build_dir" "$release"
fi

compose=(docker compose --env-file "$env_file" -f "$release/compose.staging.yml"
    -f "$release/deploy/staging/compose.proxy.yml")
"${compose[@]}" config --quiet
"${compose[@]}" build api
if [[ -n $current_revision && $current_revision != "$revision" ]]; then
    bash "$base/current/deploy/staging/backup.sh"
fi
"${compose[@]}" up -d --wait --wait-timeout 180
ln -sfn "$release" "$base/.current-next"
mv -Tf "$base/.current-next" "$base/current"
echo "Стенд обновлён до $revision."
