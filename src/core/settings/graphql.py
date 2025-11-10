from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphQLSettings(BaseSettings):
    URL: str = "http://host.docker.internal:3000/api/graphql"
    EMAIL: str = "email@email.com"
    PASSWORD: str = "Qwerty123!"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
        env_prefix="GRAPHQL_",
    )
