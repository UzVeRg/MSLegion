"""Переход на ограниченную роль API. Запуск: python deploy/staging/tests/check_database_roles.py."""

import inspect
import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4


def check_inside_api():
    import os
    import subprocess

    import httpx
    import psycopg
    from sqlalchemy.engine import make_url

    url = make_url(os.environ["DATABASE_URL"])
    connection = dict(host=url.host, user=url.username, dbname=url.database)
    with psycopg.connect(**connection, autocommit=True) as db:
        assert db.execute(
            "SELECT current_user, rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == ("mslegion_api", False, False, False, False, False)
        for statement in (
            "CREATE TABLE public.forbidden_test (id int)",
            "UPDATE alembic_version SET version_num = version_num WHERE false",
            "DELETE FROM users WHERE false",
        ):
            try:
                db.execute(statement)
            except psycopg.errors.InsufficientPrivilege:
                pass
            else:
                raise AssertionError(f"Операция разрешена роли API: {statement}")

    try:
        psycopg.connect(**(connection | {"dbname": "restore_test"})).close()
    except psycopg.OperationalError as error:
        assert "pg_hba.conf" in str(error), "Ожидался отказ политики pg_hba"
    else:
        raise AssertionError("Роль API подключилась к восстановленной БД")

    with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False) as client:
        client.get("/ready").raise_for_status()
        profile = client.post(
            "/api/v1/users",
            headers={"X-Admin-Key": os.environ["ADMIN_API_KEY"]},
            json={"display_name": "Проверка прав", "telegram_id": 42},
        )
        assert profile.status_code == 201
        user_id = profile.json()["id"]
        client.put(
            f"/api/v1/users/{user_id}/telegram/confirmation",
            headers={"X-Admin-Key": os.environ["ADMIN_API_KEY"]},
            json={"telegram_id": 42},
        ).raise_for_status()
        client.post(
            "/api/v1/callbacks/server-status",
            headers={"X-Callback-Key": os.environ["SERVER_STATUS_API_KEY"]},
            json={
                "event_id": "role-test",
                "server_id": "01234567-89ab-4cde-8123-000000000000",
                "online": True,
                "observed_at": "2026-01-01T00:00:00Z",
            },
        ).raise_for_status()
        subprocess.run(["python", "-m", "app.telegram.worker"], check=True)
        summary = client.get(
            "/api/v1/admin/callbacks/processing",
            headers={"X-Admin-Key": os.environ["ADMIN_API_KEY"]},
        )
        summary.raise_for_status()
        assert summary.json()["rejected"] == 1


def run():
    root = Path(__file__).resolve().parents[3]
    project = "mslegion-roles-" + uuid4().hex
    secrets_env = {
        key: secrets.token_hex(24)
        for key in (
            "POSTGRES_PASSWORD",
            "APP_DATABASE_PASSWORD",
            "ADMIN_API_KEY",
            "SERVER_STATUS_API_KEY",
        )
    }
    with tempfile.TemporaryDirectory() as directory:
        env_file = Path(directory, "test.env")
        env_file.write_text(
            "\n".join(f"{k}={v}" for k, v in secrets_env.items()), encoding="ascii"
        )
        # Имена проекта и тома уникальны, значения приложения задаются только этим сценарием.
        env = (
            os.environ
            | secrets_env
            | {"TELEGRAM_BOT_TOKEN": "", "CALLBACK_API_KEY": ""}
        )
        legacy = Path(directory, "legacy.yml")
        # Раньше сервер запускался со штатным pg_hba.conf из тома PostgreSQL.
        legacy.write_text('{"services":{"postgres":{"command":["postgres"]}}}', encoding="ascii")
        base = ["docker", "compose", "-p", project, "--env-file", str(env_file),
                "-f", str(root / "compose.staging.yml")]

        def compose(*args, capture=False, stdin=None, extra_env=None):
            result = subprocess.run(
                base + list(args), cwd=root, env=env | (extra_env or {}), check=True,
                input=stdin, text=True, encoding="utf-8", stdout=subprocess.PIPE if capture else None,
            )
            return result.stdout.strip() if capture else None

        def postgres(*args):
            return compose("exec", "-T", "postgres", *args, capture=True)

        def sql(query, database="mslegion_staging"):
            return postgres(
                "psql",
                "-XAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "mslegion",
                "-d",
                database,
                "-c",
                query,
            )

        try:
            compose("build", "api")
            for existing in (False, True):
                if existing:
                    compose("-f", str(legacy), "up", "-d", "--wait", "postgres")
                    compose("run", "--rm", "--no-deps", "migrate", "alembic", "upgrade", "20261123_0011")
                    sql(
                        "INSERT INTO users(id, display_name) VALUES (gen_random_uuid(), 'legacy')"
                    )

                compose("up", "-d", "--wait", "--wait-timeout", "150", "api")
                compose("run", "--rm", "--no-deps", "migrate")
                if existing:
                    assert (
                        sql("SELECT count(*) FROM users WHERE display_name = 'legacy'")
                        == "1"
                    )
                container = compose("ps", "-q", "api", capture=True)
                encoded = subprocess.check_output(
                    [
                        "docker",
                        "inspect",
                        "--format",
                        "{{json .Config.Env}}",
                        container,
                    ],
                    text=True,
                )
                assert all(
                    secrets_env["POSTGRES_PASSWORD"] not in entry
                    for entry in json.loads(encoded)
                )
                local_login = [
                    "exec",
                    "-T",
                    "-e",
                    "PGPASSWORD",
                    "postgres",
                    "psql",
                    "-w",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "mslegion_api",
                    "-d",
                    "mslegion_staging",
                    "-Atc",
                    "SELECT current_user",
                ]
                assert (
                    compose(
                        *local_login,
                        capture=True,
                        extra_env={"PGPASSWORD": secrets_env["APP_DATABASE_PASSWORD"]},
                    )
                    == "mslegion_api"
                )
                try:
                    compose(
                        *local_login,
                        capture=True,
                        extra_env={"PGPASSWORD": "incorrect-test-password"},
                    )
                except subprocess.CalledProcessError as error:
                    assert error.returncode == 2
                else:
                    raise AssertionError(
                        "PostgreSQL разрешила локальный вход с неверным паролем"
                    )
                postgres(
                    "pg_dump",
                    "-U",
                    "mslegion",
                    "-d",
                    "mslegion_staging",
                    "-Fc",
                    "-f",
                    "/tmp/test.dump",
                )
                postgres("createdb", "-U", "mslegion", "restore_test")
                postgres(
                    "pg_restore",
                    "--exit-on-error",
                    "-U",
                    "mslegion",
                    "-d",
                    "restore_test",
                    "/tmp/test.dump",
                )
                assert sql("SELECT count(*) FROM users", "restore_test") == sql(
                    "SELECT count(*) FROM users"
                )
                compose(
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "-",
                    stdin=inspect.getsource(check_inside_api) + "\ncheck_inside_api()",
                )
                compose("down", "--volumes")
            print(
                "Проверены новый том, обновление существующей БД и повторная миграция."
            )
        except subprocess.CalledProcessError:
            diagnostics = compose("logs", "--tail", "40", "postgres", "migrate", "api", capture=True)
            for value in secrets_env.values():
                diagnostics = diagnostics.replace(value, "<скрыто>")
            print(diagnostics)
            raise
        finally:
            compose("down", "--volumes", "--remove-orphans", "--rmi", "local")


if __name__ == "__main__":
    run()
