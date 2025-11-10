from faststream.rabbit import RabbitBroker

from src.core.settings import settings
from src.emails_system.entities import SendEmailEntity

broker = RabbitBroker(settings.RABBITMQ.URL)


class EmailsService:
    @staticmethod
    async def send_email(email: SendEmailEntity) -> dict[str, str]:
        try:
            await broker.publish(email.model_dump(), queue=settings.QUEUES.SEND_EMAILS)
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "message": str(e)}

        return {"status": "queued", "to": email.to}
