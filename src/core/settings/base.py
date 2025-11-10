from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.common import singleton
from src.core.settings.logger import LoggerSettings
from src.core.settings.postgres import PostgreSQLSettings
from src.core.settings.security import SecuritySettings


@singleton
class Settings(BaseSettings):
    APP_TITLE: str = "Default Title"
    APP_DESCRIPTION: str = "Default Description"
    APP_VERSION: str = "0.1.0"

    DOCS_URL: str | None = "/docs"
    REDOC_URL: str | None = "/redoc"

    DEBUG: bool = False
    DB_ECHO: bool = False
    LOGGER: LoggerSettings = LoggerSettings()

    DOMAIN: str = "example.site"

    POSTGRES: PostgreSQLSettings = PostgreSQLSettings()
    SECURITY: SecuritySettings = SecuritySettings()

    API_PREFIX: str = "/api"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
    )


settings = Settings()
