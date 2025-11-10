from uuid import UUID

from src.core.db.base_repository import BaseRepository
from src.emails_system.api.v1.schemas.email_settings import (
    CreateEmailSettingsRequest,
    EmailSettingsResponse,
    UpdateEmailSettingsRequest,
)
from src.emails_system.models.email_settings import EmailSettings


class EmailSettingsRepository(
    BaseRepository[
        EmailSettings,
        EmailSettingsResponse,
        CreateEmailSettingsRequest,
        UpdateEmailSettingsRequest,
    ]
):
    def __init__(self, session):
        super().__init__(
            session=session,
            model=EmailSettings,
            entity=EmailSettingsResponse,
            create_entity=CreateEmailSettingsRequest,
            update_entity=UpdateEmailSettingsRequest,
        )

    async def get_by_organization_id(self, organization_id: UUID) -> EmailSettingsResponse | None:
        return await self.get(organization_id, field="organization_id")

    async def get_by_user_id(self, user_id: UUID) -> EmailSettingsResponse | None:
        return await self.get(user_id, field="user_id")

    async def get_list_by_organization(
        self,
        organization_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[EmailSettingsResponse], int]:
        filters = {"organization_id": organization_id}
        return await self.get_list(
            filters=filters,
            limit=limit,
            offset=offset,
        )

    async def get_model_by_organization_id(self, organization_id: UUID) -> EmailSettings | None:
        return await self._get(organization_id, field="organization_id")
