import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from src.core.db import postgres_session_manager
from src.core.settings import settings
from src.emails_system.entities import CheckEmailTask, ProcessEmailTask
from src.emails_system.models.email_settings import EmailSettings
from src.workers.emails_consumer.imap_client import fetch_unseen_emails

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настраиваем брокер
broker = RabbitBroker(settings.RABBITMQ.URL)
app = FastStream(broker)
scheduler = AsyncIOScheduler()


async def schedule_mail_checks():
    """Раз в 5 минут собирает ID настроек и кидает задачи в очередь"""
    logger.info("⏰ Scheduler: Запуск проверки почты...")

    async with postgres_session_manager.session_factory.begin() as session:
        # Берем все настройки
        query = select(EmailSettings.id).where(EmailSettings.deleted_at.is_(None))
        result = await session.execute(query)
        ids = result.scalars().all()

        for settings_id in ids:
            task = CheckEmailTask(settings_id=settings_id)
            # Кидаем в очередь 'settings.QUEUES.RECEIVE_EMAILS'
            await broker.publish(task, queue=settings.QUEUES.RECEIVE_EMAILS)

        logger.info("⏰ Scheduler: Создано %d задач на проверку.", len(ids))


@broker.subscriber(settings.QUEUES.RECEIVE_EMAILS)
async def handle_read_emails(task: CheckEmailTask):
    """Читает настройки из БД, идет в IMAP, парсит письма"""

    async with postgres_session_manager.session_factory.begin() as session:
        setting = await session.get(EmailSettings, task.settings_id)
        if not setting:
            return

        logger.info("🕵️ Reader: Проверяю ящик %s", setting.email_login)

        # Идем в IMAP
        emails = await fetch_unseen_emails(
            host=setting.imap_host,
            port=setting.imap_port,
            login=setting.email_login,
            password=setting.email_password,
        )

        if emails:
            logger.info("✅ Reader: Найдено %d писем для %s", len(emails), setting.email_login)

            # Передаем каждое письмо во второй воркер
            for email_data in emails:
                process_task = ProcessEmailTask(
                    settings_id=setting.id,
                    organization_id=setting.organization_id,
                    subject=email_data["subject"],
                    from_email=email_data["from"],
                    to_email=email_data.get("to"),
                    date=email_data.get("date"),
                    body=email_data["body"],
                )
                await broker.publish(process_task, queue=settings.QUEUES.CREATE_TICKETS)


@app.on_startup
async def startup():  # noqa: RUF029
    scheduler.add_job(schedule_mail_checks, "interval", minutes=1)
    scheduler.start()
    logger.info("🚀 Application started with Scheduler")


@app.on_shutdown
async def shutdown():  # noqa: RUF029
    scheduler.shutdown()
