from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class QueuesSettings(BaseSettings):
    SEND_EMAILS: str = "send_emails_queue"
    RECEIVE_EMAILS: str = "receive_emails_queue"
    READ_COMMENTS: str = "read_comments_queue"
    CREATE_TICKETS: str = "create_tickets_queue"
    CREATE_COMMENTS: str = "create_comments_queue"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
        env_prefix="QUEUE_",
    )
