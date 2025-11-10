from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailSettings(BaseSettings):
    USERNAME: str = "username"
    PASSWORD: str = "passwd"
    FROM: str = "test@email.com"
    PORT: int = 1025
    SERVER: str = "localhost"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
        env_prefix="MAIL_",
    )
