from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "MSLegion"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+psycopg://mslegion:mslegion@127.0.0.1:5432/mslegion"
    )
    admin_api_key: str | None = Field(default=None, repr=False)
    callback_api_key: str | None = Field(default=None, repr=False)

    test_database_url: str = (
        "postgresql+psycopg://mslegion:mslegion@127.0.0.1:5434/mslegion_test"
    )
    run_integration_tests: bool = False

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        hide_input_in_errors=True,
        extra="ignore",
    )

    @field_validator("admin_api_key", "callback_api_key")
    @classmethod
    def validate_api_key(cls, value: str | None) -> str | None:
        if not value or value.strip() in {"", "change-me", "change-me-callback"}:
            return None
        if not value.isascii() or not value.isprintable() or value.strip() != value:
            raise ValueError(
                "Ключи API должны содержать печатные символы ASCII без пробелов по краям"
            )
        return value

    @model_validator(mode="after")
    def ensure_distinct_keys(self) -> Self:
        if self.admin_api_key and self.admin_api_key == self.callback_api_key:
            raise ValueError("Ключи API для администрирования и приёма событий должны различаться")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
