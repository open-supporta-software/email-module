import logging

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from src.core.db import postgres_session_manager
from src.core.integration.graphql import graphql_client
from src.core.settings import settings
from src.emails_system.entities import CheckCommentsTask, SendEmailEntity
from src.emails_system.models.email_settings import EmailSettings
from src.emails_system.models.sent_comment import SentComment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настраиваем брокер
broker = RabbitBroker(settings.RABBITMQ.URL)
app = FastStream(broker)
scheduler = AsyncIOScheduler()


async def schedule_mail_checks():
    """Раз в 5 минут собирает ID организаций и кидает задачи в очередь"""
    logger.info("⏰ Scheduler: Запуск проверки комментариев...")

    async with postgres_session_manager.session_factory.begin() as session:
        query = select(EmailSettings.organization_id).distinct()
        result = await session.execute(query)
        ids = result.scalars().all()

        for organization_id in ids:
            task = CheckCommentsTask(organization_id=organization_id)
            await broker.publish(task, queue=settings.QUEUES.READ_COMMENTS)

    logger.info("⏰ Scheduler: Создано %d задач на проверку.", len(ids))


@broker.subscriber(settings.QUEUES.READ_COMMENTS)
async def handle_read_comments(task: CheckCommentsTask):
    logger.info("🔍 Reader: Проверка комментариев для организации %s", task.organization_id)

    # 1. Получаем settings_id для отправки писем
    async with postgres_session_manager.session_factory.begin() as session:
        stmt = (
            select(EmailSettings)
            .where(EmailSettings.organization_id == task.organization_id)
            .limit(1)
        )
        result = await session.execute(stmt)
        email_settings = result.scalar_one_or_none()

        if not email_settings:
            logger.warning(
                "⚠️ Reader: Не найдены настройки email для организации %s",
                task.organization_id,
            )
            return

        settings_id = email_settings.id

    # 2. Запрашиваем комментарии из GraphQL (только от операторов, type: organization)
    query = """
    query GetComments($organizationId: ID!) {
      allTicketComments(
        where: {
          type: organization,
          user: {
            type_not: service
          }
          ticket: {
            organization: { id: $organizationId },
            source: { id: "0e9af80b-b5f0-4667-9f8e-577f1cab1a21" }
          }
        }
        sortBy: [createdAt_DESC]
        first: 100
      ) {
        id
        content
        createdAt
        ticket {
          id
          number
          clientEmail
          contact {
            email
          }
        }
      }
    }
    """

    try:
        response = await graphql_client.execute(
            query, {"organizationId": str(task.organization_id)}
        )
        comments = response.get("data", {}).get("allTicketComments", [])
        logger.warning(comments)
    except httpx.HTTPStatusError:
        logger.exception("❌ Reader: GraphQL Error:")
        return
    except Exception:
        logger.exception("❌ Reader: Ошибка запроса к GraphQL")
        return

    if not comments:
        logger.info("Reader: Комментариев не найдено")
        return

    logger.info("Reader: Найдено %d комментариев", len(comments))

    # 3. Обрабатываем комментарии
    async with postgres_session_manager.session_factory.begin() as session:
        for comment in comments:
            comment_id = comment["id"]

            # Проверяем, отправляли ли уже
            stmt = select(SentComment).where(SentComment.comment_id == comment_id)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                logger.info("Reader: Комментарий %s уже обработан", comment_id)
                continue

            ticket = comment.get("ticket")
            if not ticket:
                logger.warning("Reader: Комментарий %s без тикета", comment_id)
                continue

            # Определяем email получателя
            recipient_email = ticket.get("clientEmail")
            if not recipient_email and ticket.get("contact"):
                recipient_email = ticket["contact"].get("email")

            new_sent_comment = SentComment(
                comment_id=comment_id,
                ticket_id=ticket["id"],
                organization_id=task.organization_id,
            )

            if recipient_email:
                # Отправляем в очередь
                email_task = SendEmailEntity(
                    settings_id=settings_id,
                    to=recipient_email,
                    subject=f"Новый ответ по тикету {ticket.get('number', '')}",
                    body=comment["content"],
                )
                await broker.publish(email_task, queue=settings.QUEUES.SEND_EMAILS)
                new_sent_comment.is_sent = True
                logger.info("Reader: Комментарий %s отправлен на %s", comment_id, recipient_email)
            else:
                new_sent_comment.is_sent = False
                new_sent_comment.error_message = "No email found"
                logger.info("Reader: Не удалось отправить комментарий %s: нет email", comment_id)

            session.add(new_sent_comment)


@app.on_startup
async def startup():  # noqa: RUF029
    scheduler.add_job(schedule_mail_checks, "interval", minutes=1)
    scheduler.start()
    logger.info("🚀 Application started with Scheduler")


@app.on_shutdown
async def shutdown():  # noqa: RUF029
    scheduler.shutdown()
