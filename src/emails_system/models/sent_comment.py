from uuid import UUID, uuid4

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.base_models import BaseModel, TimestampMixin


class SentComment(BaseModel, TimestampMixin):
    """Модель для отслеживания отправленных комментариев"""

    __tablename__ = "sent_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ticket_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(nullable=True)

    is_sent: Mapped[bool] = mapped_column(default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
