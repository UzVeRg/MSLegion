"""Обновить схему стенда и выдать рабочей роли права на операции API и воркера."""

import os

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection


def prepare_role(connection: Connection) -> None:
    role = connection.exec_driver_sql("""
        SELECT shobj_description(oid, 'pg_authid') AS marker,
               rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
               OR EXISTS (SELECT FROM pg_auth_members WHERE roleid = r.oid OR member = r.oid)
               OR EXISTS (SELECT FROM pg_shdepend WHERE refclassid = 'pg_authid'::regclass
                          AND refobjid = r.oid AND deptype = 'o') AS elevated
        FROM pg_roles AS r WHERE rolname = 'mslegion_api'
    """).one_or_none()
    if role is None:
        connection.exec_driver_sql("CREATE ROLE mslegion_api NOINHERIT")
        connection.exec_driver_sql("COMMENT ON ROLE mslegion_api IS 'Рабочая роль API MSLegion'")
    elif role.marker != "Рабочая роль API MSLegion" or role.elevated:
        raise RuntimeError("Имя mslegion_api занято посторонней или привилегированной ролью")


def set_api_password(connection: Connection, password: str) -> None:
    raw = connection.connection.driver_connection
    verifier = raw.pgconn.encrypt_password(password.encode(), b"mslegion_api", b"scram-sha-256")
    # Драйвер передаёт проверочное значение параметром. В журнал попадут только имена команд.
    connection.exec_driver_sql("SET LOCAL log_parameter_max_length = 0")
    connection.exec_driver_sql("SET LOCAL log_parameter_max_length_on_error = 0")
    with psycopg.Cursor(raw) as cursor:
        cursor.execute(
            "SELECT set_config('mslegion.api_verifier', %s, true)", (verifier.decode("ascii"),)
        )
    connection.exec_driver_sql("""
        DO $$
        BEGIN
            EXECUTE 'ALTER ROLE mslegion_api LOGIN PASSWORD ' ||
                    quote_literal(current_setting('mslegion.api_verifier'));
        EXCEPTION WHEN OTHERS THEN
            RAISE EXCEPTION 'Не удалось задать пароль рабочей роли MSLegion';
        END $$;
    """)


def grant_api_access(connection: Connection) -> None:
    connection.exec_driver_sql("""
        REVOKE CREATE, TEMPORARY ON DATABASE mslegion_staging FROM PUBLIC, mslegion_api;
        REVOKE CREATE ON SCHEMA public FROM PUBLIC, mslegion_api;
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM mslegion_api;
        GRANT CONNECT ON DATABASE mslegion_staging TO mslegion_api;
        GRANT USAGE ON SCHEMA public TO mslegion_api;
        GRANT SELECT, INSERT ON public.users, public.user_sessions, public.communities,
              public.community_memberships, public.community_servers, public.community_posts,
              public.integration_events, public.telegram_notifications, public.domain_events,
              public.mafia_rooms
              TO mslegion_api;
        GRANT DELETE ON public.community_memberships, public.community_servers,
              public.community_posts, public.user_sessions TO mslegion_api;
        GRANT UPDATE (telegram_verified, telegram_notifications_since, updated_at)
              ON public.users TO mslegion_api;
        GRANT UPDATE (revoked_at) ON public.user_sessions TO mslegion_api;
        -- Для SELECT FOR UPDATE при изменении состава достаточно права на один столбец.
        GRANT UPDATE (name) ON public.communities TO mslegion_api;
        GRANT UPDATE (online, status_observed_at, status_event_id)
              ON public.community_servers TO mslegion_api;
        GRANT UPDATE (image, image_type) ON public.community_posts TO mslegion_api;
        GRANT UPDATE (processing_state) ON public.integration_events TO mslegion_api;
        GRANT UPDATE (state, attempted_at) ON public.telegram_notifications TO mslegion_api;
        GRANT UPDATE (state, updated_at) ON public.mafia_rooms TO mslegion_api;
    """)


def main() -> None:
    password = os.environ["APP_DATABASE_PASSWORD"]
    if not password or password == os.environ["PGPASSWORD"]:
        raise ValueError("Задайте отдельный непустой пароль для рабочей роли API")
    engine = create_engine(os.environ["DATABASE_URL"], hide_parameters=True)
    with engine.begin() as connection:
        if connection.exec_driver_sql("SELECT current_database(), current_user").one() != (
            "mslegion_staging", "mslegion"
        ):
            raise RuntimeError("Для выпуска требуется база mslegion_staging и роль mslegion")
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(hashtext('mslegion.staging'))")
        prepare_role(connection)
        alembic = Config("alembic.ini")
        alembic.attributes["connection"] = connection
        command.upgrade(alembic, "head")
        grant_api_access(connection)
        set_api_password(connection, password)
    print("Схема PostgreSQL и права рабочей роли API обновлены.")


if __name__ == "__main__":
    main()
