from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
    HOST: str = "localhost"
    USER: str = "user"
    PORT: int = 5672
    PASSWORD: str = "pass"
    VHOST: str = "/"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
        env_prefix="RABBITMQ_",
    )

    @computed_field
    @property
    def URL(self) -> str:
        password = f":{self.PASSWORD}" if self.PASSWORD else ""
        return f"amqp://{self.USER}{password}@{self.HOST}:{self.PORT}{self.VHOST}"
