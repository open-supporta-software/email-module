from uuid import UUID

from src.core.api.queries import Pagination
from src.emails_system.api.v1.schemas.email_settings import (
    CreateEmailSettingsRequest,
    EmailSettingsFilters,
    EmailSettingsResponse,
    UpdateEmailSettingsRequest,
)
from src.emails_system.db.repositories.email_settings import EmailSettingsRepository


class EmailSettingsService:
    def __init__(
        self,
        repository: EmailSettingsRepository,
    ):
        self.repository = repository

    async def create_email_settings(
        self,
        data: CreateEmailSettingsRequest,
    ) -> EmailSettingsResponse:
        return await self.repository.create(data)

    async def get_email_settings(
        self,
        email_setting_id: UUID,
    ) -> EmailSettingsResponse | None:
        return await self.repository.get(email_setting_id, field="id")

    async def get_by_organization(
        self,
        organization_id: UUID,
    ) -> EmailSettingsResponse | None:
        return await self.repository.get_by_organization_id(organization_id)

    async def get_list_by_organization(
        self,
        organization_id: UUID,
        pagination: Pagination,
    ) -> tuple[list[EmailSettingsResponse], int]:
        return await self.repository.get_list_by_organization(
            organization_id=organization_id,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_list(
        self,
        filters: EmailSettingsFilters | None = None,
        pagination: Pagination | None = None,
    ) -> tuple[list[EmailSettingsResponse], int]:
        # Преобразуем Pydantic модель в dict, исключаем None значения
        filters_dict = filters.model_dump(exclude_none=True) if filters else None

        pagination = pagination or Pagination()

        return await self.repository.get_list(
            filters=filters_dict,
            limit=pagination.limit,
            offset=pagination.offset,
        )

    async def get_by_user(
        self,
        user_id: UUID,
    ) -> EmailSettingsResponse | None:
        return await self.repository.get_by_user_id(user_id)

    async def update_email_settings(
        self,
        email_setting_id: UUID,
        data: UpdateEmailSettingsRequest,
    ) -> EmailSettingsResponse | None:
        return await self.repository.update(
            data,
            value=email_setting_id,
            field="id",
        )

    async def delete_email_settings(self, email_setting_id: UUID) -> None:
        await self.repository.delete(email_setting_id, field="id")

    async def restore_email_settings(self, email_setting_id: UUID) -> EmailSettingsResponse | None:
        return await self.repository.restore(email_setting_id, field="id")
