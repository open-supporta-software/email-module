from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base_models import BaseModel, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.emails_system.models import ReceivedEmail


class EmailSettings(BaseModel, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "email_settings"
    repr_cols = ("id", "organization_id", "user_id", "description")

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    user_id: Mapped[UUID]
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Общие настройки аккаунта
    email_login: Mapped[str] = mapped_column(String(255))
    email_password: Mapped[str] = mapped_column(String(255))

    # Настройки SMTP (Отправка)
    smtp_host: Mapped[str] = mapped_column(String(255))
    smtp_port: Mapped[int] = mapped_column(Integer, default=465)

    # Настройки IMAP (Чтение)
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)

    # Relationship: One-to-Many (Одни настройки -> Много полученных писем)
    received_emails: Mapped[list["ReceivedEmail"]] = relationship(
        "ReceivedEmail",
        back_populates="email_settings",
    )
