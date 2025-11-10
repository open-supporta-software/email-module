from uuid import UUID

from pydantic import BaseModel, EmailStr


class SendEmailEntity(BaseModel):
    settings_id: UUID
    to: EmailStr
    subject: str
    body: str


class CheckEmailTask(BaseModel):
    """Задача для Reader Worker: проверить конкретный ящик"""

    settings_id: UUID


class ProcessEmailTask(BaseModel):
    """Задача для Processor Worker: сохранить/обработать письмо"""

    settings_id: UUID
    organization_id: UUID
    subject: str | None
    from_email: str
    to_email: str | None
    date: str | None
    body: str | None


class CheckCommentsTask(BaseModel):
    """Задача для Reader Worker: проверить новые комментарии"""

    organization_id: UUID


class CreateCommentTask(BaseModel):
    """Задача для Comment Maker Worker: создать комментарий к существующему тикету"""

    ticket_id: str
    settings_id: UUID
    organization_id: UUID
    from_email: str
    body: str | None
