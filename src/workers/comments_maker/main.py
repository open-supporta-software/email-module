import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from src.core.integration.graphql import graphql_client
from src.core.settings import settings
from src.emails_system.entities import CreateCommentTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настраиваем брокер
broker = RabbitBroker(settings.RABBITMQ.URL)
app = FastStream(broker)


@broker.subscriber(settings.QUEUES.CREATE_COMMENTS)
async def handle_create_comment(task: CreateCommentTask):
    """Создает комментарий к существующему тикету через GraphQL API"""
    logger.info("💬 Comment Maker: Создаю комментарий к тикету %s", task.ticket_id)

    # Получаем текущего авторизованного пользователя
    get_user_query = """
    query GetAuthenticatedUser {
      authenticatedUser {
        id
      }
    }
    """

    user_result = await graphql_client.execute(get_user_query)

    if "errors" in user_result:
        logger.error("❌ Comment Maker: GraphQL Error getting user: %s", user_result["errors"])
        raise ValueError(f"GraphQL Error getting user: {user_result['errors']}")

    user_id = user_result.get("data", {}).get("authenticatedUser", {}).get("id")
    if user_id:
        logger.info("👤 Comment Maker: Используется пользователь: %s", user_id)
    else:
        logger.error(
            "❌ Comment Maker: Не удалось получить ID пользователя (Config Warning). "
            "Задача НЕ будет возвращена в очередь во избежание цикла."
        )
        return

    comment_content = f"Ответ пользователя:\n\n{task.body or ''}"

    create_comment_mutation = """
    mutation CreateTicketComment($data: TicketCommentCreateInput!) {
      createTicketComment(data: $data) {
        id
        content
        createdAt
        ticket {
          id
          number
        }
      }
    }
    """

    comment_data = {
        "type": "organization",
        "ticket": {"connect": {"id": task.ticket_id}},
        "user": {"connect": {"id": user_id}},
        "content": comment_content,
        "dv": 1,
        "sender": {"dv": 1, "fingerprint": "4916dd67913b4af8a5f3e3cf72cfa9e3"},
    }

    result = await graphql_client.execute(create_comment_mutation, {"data": comment_data})

    if "errors" in result:
        logger.error("❌ Comment Maker: GraphQL Error: %s", result["errors"])
        errors_str = str(result["errors"])
        if "Constraint" in errors_str or "Validation" in errors_str or "not found" in errors_str:
            logger.error(
                "❌ Comment Maker: Hard Logic Error (probably ticket missing). Dropping task."
            )
            return

        raise ValueError(f"GraphQL Error: {result['errors']}")
    comment_id = result.get("data", {}).get("createTicketComment", {}).get("id")
    logger.info("✅ Comment Maker: Комментарий создан: %s", comment_id)
