import logging
from email.mime.text import MIMEText

import aiosmtplib
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from src.core.db import postgres_session_manager
from src.core.settings import settings
from src.emails_system.entities import SendEmailEntity
from src.emails_system.models.email_settings import EmailSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.RABBITMQ.URL)
app = FastStream(broker)


@broker.subscriber(settings.QUEUES.SEND_EMAILS)
async def handle_send_email(task: SendEmailEntity):
    logger.info("📧 Sender: Отправка письма на %s", task.to)

    async with postgres_session_manager.session_factory.begin() as session:
        try:
            # Получаем настройки email по settings_id
            email_settings = await session.get(EmailSettings, task.settings_id)

            if not email_settings:
                logger.error("Email settings not found for settings_id: %s", task.settings_id)
                raise ValueError(f"Email settings not found for settings_id {task.settings_id}")  # noqa: TRY301

            # Формируем сообщение
            msg = MIMEText(task.body, "plain", "utf-8")
            msg["From"] = email_settings.email_login
            msg["To"] = task.to
            msg["Subject"] = task.subject

            # Отправляем через SMTP
            await aiosmtplib.send(
                msg,
                hostname=email_settings.smtp_host,
                port=email_settings.smtp_port,
                username=email_settings.email_login,
                password=email_settings.email_password,
                use_tls=email_settings.smtp_port == 465,
                start_tls=email_settings.smtp_port != 465,
            )

            logger.info("✅ Sender: Письмо успешно отправлено на %s", task.to)

        except Exception:
            logger.exception("❌ Sender: Ошибка при отправке письма")
            raise
