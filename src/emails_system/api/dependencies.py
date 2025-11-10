from typing import Annotated

from fastapi import Depends

from src.core.api.dependencies import TransactionDependency
from src.emails_system.db.repositories.email_settings import EmailSettingsRepository
from src.emails_system.services.email_settings import EmailSettingsService
from src.emails_system.services.emails import EmailsService

EmailsServiceDependency = Annotated[EmailsService, Depends(EmailsService)]


def get_email_settings_repository(transaction: TransactionDependency) -> EmailSettingsRepository:
    return EmailSettingsRepository(transaction.postgres_session)


EmailSettingsRepositoryDependency = Annotated[
    EmailSettingsRepository, Depends(get_email_settings_repository)
]


def get_email_settings_service(
    email_settings_repository: EmailSettingsRepositoryDependency,
) -> EmailSettingsService:
    return EmailSettingsService(repository=email_settings_repository)


EmailSettingsServiceDependency = Annotated[
    EmailSettingsService, Depends(get_email_settings_service)
]
