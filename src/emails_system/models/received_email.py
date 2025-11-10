from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base_models import BaseModel, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.emails_system.models import EmailSettings


class ReceivedEmail(BaseModel, TimestampMixin, SoftDeleteMixin):
    """Модель для сохранения входящих писем"""

    __tablename__ = "received_emails"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]

    email_settings_id: Mapped[UUID] = mapped_column(ForeignKey("email_settings.id"))

    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str] = mapped_column(String(255))
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Флаг, что мы создали из этого письма тикет
    is_processed_by_api: Mapped[bool] = mapped_column(default=False)

    # Relationship: Many-to-One (Много писем -> Одни настройки)
    email_settings: Mapped["EmailSettings"] = relationship(
        "EmailSettings", back_populates="received_emails"
    )
