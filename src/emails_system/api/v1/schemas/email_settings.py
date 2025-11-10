from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.core.api.queries import BaseFilters, BaseSortParams

Description = Annotated[str, Field(min_length=1, max_length=255)]
Url = Annotated[str, Field(min_length=1, max_length=255)]
Port = Annotated[int, Field(ge=1, le=65535)]
Password = Annotated[str, Field(min_length=1, max_length=255)]


class EmailSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    description: str | None
    email_login: str
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    created_at: datetime
    updated_at: datetime


class CreateEmailSettingsRequest(BaseModel):
    """DTO для создания email settings"""

    organization_id: UUID
    user_id: UUID
    email_login: str
    email_password: Password
    description: Description | None = None
    smtp_host: Url
    smtp_port: Port = 587
    imap_host: Url
    imap_port: Port = 993


class UpdateEmailSettingsRequest(BaseModel):
    """DTO для обновления email settings"""

    description: Description | None = None
    email_password: Password | None = None
    smtp_host: Url | None = None
    smtp_port: Port | None = None
    imap_host: Url | None = None
    imap_port: Port | None = None


class EmailSettingsFilters(BaseFilters):
    """Фильтры для списка email settings"""

    organization_id: UUID | None = None
    user_id: UUID | None = None
    email_login: str | None = None


class EmailSettingsSortParams(BaseSortParams):
    """Параметры сортировки для email settings"""

    sort_by: str = "created_at"  # можно сортировать по: created_at, updated_at, description
