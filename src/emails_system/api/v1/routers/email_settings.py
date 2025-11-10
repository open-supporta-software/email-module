from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.core.api.queries import PaginationQuery
from src.emails_system.api.dependencies import EmailSettingsServiceDependency
from src.emails_system.api.v1.schemas.email_settings import (
    CreateEmailSettingsRequest,
    EmailSettingsResponse,
    UpdateEmailSettingsRequest,
)

router = APIRouter(prefix="/email-settings")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create email settings",
    description="Creates a new email setting in database",
)
async def create_email_setting(
    data: CreateEmailSettingsRequest,
    service: EmailSettingsServiceDependency,
) -> EmailSettingsResponse:
    try:
        return await service.create_email_settings(data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create email settings: {e!s}",
        ) from e


@router.get(
    "/{email_setting_id}",
    status_code=status.HTTP_200_OK,
    summary="Get email settings",
    description="Retrieves the email settings from the database",
)
async def get_email_setting(
    email_setting_id: UUID,
    service: EmailSettingsServiceDependency,
) -> EmailSettingsResponse:
    email_settings = await service.get_email_settings(email_setting_id)

    if not email_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email settings with id {email_setting_id} not found",
        )

    return email_settings


@router.get(
    "/organization/{organization_id}",
    status_code=status.HTTP_200_OK,
    summary="Get email settings list by organization",
    description="Retrieves all email settings for a specific organization with pagination",
)
async def get_email_settings_list_by_organization(
    organization_id: UUID,
    pagination: PaginationQuery,
    service: EmailSettingsServiceDependency,
) -> dict:
    items, total = await service.get_list_by_organization(
        organization_id=organization_id,
        pagination=pagination,
    )

    return {
        "items": items,
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }


@router.patch(
    "/{email_setting_id}",
    status_code=status.HTTP_200_OK,
    summary="Update email settings",
    description="Updates email settings in the database",
)
async def update_email_setting(
    email_setting_id: UUID,
    data: UpdateEmailSettingsRequest,
    service: EmailSettingsServiceDependency,
) -> EmailSettingsResponse:
    updated_settings = await service.update_email_settings(email_setting_id, data)

    if not updated_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email settings with id {email_setting_id} not found",
        )

    return updated_settings


@router.delete(
    "/{email_setting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete email settings",
    description="Soft deletes email settings from the database",
)
async def delete_email_setting(
    email_setting_id: UUID,
    service: EmailSettingsServiceDependency,
) -> None:
    email_settings = await service.get_email_settings(email_setting_id)

    if not email_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email settings with id {email_setting_id} not found",
        )

    await service.delete_email_settings(email_setting_id)
