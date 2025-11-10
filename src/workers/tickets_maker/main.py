import logging
from email.utils import parseaddr

import httpx
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from src.core.db import postgres_session_manager
from src.core.integration.graphql import graphql_client
from src.core.settings import settings
from src.emails_system.entities import CreateCommentTask, ProcessEmailTask, SendEmailEntity
from src.emails_system.models.received_email import ReceivedEmail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настраиваем брокер
broker = RabbitBroker(settings.RABBITMQ.URL)
app = FastStream(broker)


@broker.subscriber(settings.QUEUES.CREATE_TICKETS)
async def handle_process_email(task: ProcessEmailTask):  # noqa: C901, PLR0912, PLR0914, PLR0915
    """Сохраняет письмо в БД и создает тикет или комментарий через GraphQL API"""
    logger.info("💾 Processor: Обрабатываю письмо '%s'", task.subject)

    name, email = parseaddr(task.from_email)
    if not name:
        name = email

    existing_ticket_query = """
    query GetExistingTickets($organizationId: ID!, $email: String!) {
      allTickets(
        where: {
          organization: { id: $organizationId }
          status: {
            id_in: [
              "6ef3abc4-022f-481b-90fb-8430345ebfc2"
              "aa5ed9c2-90ca-4042-8194-d3ed23cb7919"
              "c14a58e0-6b5d-4ec2-b91c-980a90509c7f"
            ]
          }
          OR: [
            { clientEmail: $email }
            { contact: { email: $email } }
          ]
        }
        sortBy: [createdAt_DESC]
        first: 1
      ) {
        id
        number
        status { id name }
      }
    }
    """

    existing_ticket = None
    try:
        existing_result = await graphql_client.execute(
            existing_ticket_query,
            {"organizationId": str(task.organization_id), "email": email},
        )
        tickets = existing_result.get("data", {}).get("allTickets", [])
        if tickets:
            existing_ticket = tickets[0]
            logger.info(
                "🎫 Processor: Найден существующий тикет %s (№%s) для %s",
                existing_ticket["id"],
                existing_ticket.get("number", "N/A"),
                email,
            )
    except Exception:
        logger.exception("⚠️ Processor: Ошибка при проверке существующих тикетов")

    # Если найден существующий тикет - создаем комментарий
    if existing_ticket:
        comment_task = CreateCommentTask(
            ticket_id=existing_ticket["id"],
            settings_id=task.settings_id,
            organization_id=task.organization_id,
            from_email=task.from_email,
            body=task.body,
        )
        await broker.publish(comment_task, queue=settings.QUEUES.CREATE_COMMENTS)
        logger.info(
            "💬 Processor: Отправлена задача на создание комментария к тикету %s",
            existing_ticket["id"],
        )

        # Сохраняем письмо в БД
        async with postgres_session_manager.session_factory.begin() as session:
            try:
                new_email = ReceivedEmail(
                    organization_id=task.organization_id,
                    email_settings_id=task.settings_id,
                    subject=task.subject,
                    from_email=task.from_email,
                    body_text=task.body,
                    is_processed_by_api=True,
                )
                session.add(new_email)
                await session.commit()
                logger.info("💾 Processor: Письмо сохранено (комментарий).")
            except Exception:
                logger.exception("Ошибка сохранения письма")
                await session.rollback()
        return

    # 3. Check if contact exists
    contact_id = None

    get_contact_query = """
    query GetContact($email: String!) {
      allContacts(where: { email: $email }) {
        id
        name
      }
    }
    """

    try:
        contact_result = await graphql_client.execute(get_contact_query, {"email": email})

        contacts = contact_result.get("data", {}).get("allContacts", [])
        if contacts:
            contact_id = contacts[0]["id"]
            logger.info("👤 Processor: Found existing contact: %s", contact_id)
        else:
            logger.info("👤 Processor: Contact not found. Creation is currently disabled.")

    except Exception:
        logger.exception("⚠️ Processor: Error during contact check")

    # 4. Check/Create Property
    property_id = None
    get_property_query = """
    query GetProperty($organizationId: ID!) {
      allProperties(where: { organization: { id: $organizationId } }) {
        id
        name
      }
    }
    """

    try:
        property_result = await graphql_client.execute(
            get_property_query, {"organizationId": str(task.organization_id)}
        )
        properties = property_result.get("data", {}).get("allProperties", [])
        if properties:
            property_id = properties[0]["id"]
            logger.info("🏢 Processor: Found existing property: %s", property_id)
        else:
            logger.info("🏢 Processor: Property not found. Creating new one.")
            create_property_mutation = """
            mutation CreateProperty($data: PropertyCreateInput!) {
              createProperty(data: $data) {
                id
              }
            }
            """
            property_data = {
                "dv": 1,
                "sender": {"dv": 1, "fingerprint": "4916dd67913b4af8a5f3e3cf72cfa9e3"},
                "organization": {"connect": {"id": str(task.organization_id)}},
                "type": "building",
                "address": "г Екатеринбург, ул Мира, д 32",  # noqa: RUF001
                "name": "ИРИТ-РТФ",
                "area": "7",
                "yearOfConstruction": None,
            }
            create_prop_result = await graphql_client.execute(
                create_property_mutation, {"data": property_data}
            )
            if "errors" in create_prop_result:
                logger.error(
                    "❌ Processor: Failed to create property: %s", create_prop_result["errors"]
                )
            else:
                property_id = (
                    create_prop_result.get("data", {}).get("createProperty", {}).get("id")
                )
                logger.info("✅ Processor: Created new property: %s", property_id)

    except Exception:
        logger.exception("⚠️ Processor: Error during property check/creation")

    if not property_id:
        property_id = "51a649ec-8ca4-4947-b13a-7b086af58f3b"

    # 5. Create Ticket
    details_text = task.body or ""
    ticket_title = task.subject or "No Subject"

    # Common fields for data
    # We will construct the mutation dynamically based on contact presence

    if contact_id:
        # Case A: Contact exists - link it
        mutation = """
        mutation CreateTicket($organizationId: ID!, $details: String!, $title: String!, $contactId: ID!, $propertyId: ID!) {
          createTicket(
            data: {
              dv: 1
              sender: {
                dv: 1
                fingerprint: "8d93dcf6a16945f7b1b274de1"
              }
              organization: { connect: { id: $organizationId } }
              source: { connect: { id: "0e9af80b-b5f0-4667-9f8e-577f1cab1a21" } }
              property: { connect: { id: $propertyId } }
              details: $details
              title: $title
              contact: { connect: { id: $contactId } }
            }
          ) {
            id
            number
            clientPhone
            property { id }
            contact { id }
            unitName
            unitType
          }
        }
        """  # noqa: E501
        variables = {
            "organizationId": str(task.organization_id),
            "details": details_text,
            "title": ticket_title,
            "contactId": contact_id,
            "propertyId": property_id,
        }
    else:
        # Case B: No contact - use clientName / clientEmail
        mutation = """
        mutation CreateTicket($organizationId: ID!, $details: String!, $title: String!, $clientName: String, $clientEmail: String, $propertyId: ID!) {
          createTicket(
            data: {
              dv: 1
              sender: {
                dv: 1
                fingerprint: "8d93dcf6a16945f7b1b274de1"
              }
              organization: { connect: { id: $organizationId } }
              source: { connect: { id: "0e9af80b-b5f0-4667-9f8e-577f1cab1a21" } }
              property: { connect: { id: $propertyId } }
              details: $details
              title: $title
              clientName: $clientName
              clientEmail: $clientEmail
            }
          ) {
            id
            number
            clientPhone
            property { id }
            contact { id }
            unitName
            unitType
          }
        }
        """  # noqa: E501
        variables = {
            "organizationId": str(task.organization_id),
            "details": details_text,
            "title": ticket_title,
            "clientName": name,
            "clientEmail": email,
            "propertyId": property_id,
        }

    ticket_created = False
    try:
        result = await graphql_client.execute(mutation, variables)

        if "errors" in result:
            logger.error("❌ Processor: GraphQL Error: %s", result["errors"])
        else:
            logger.info(
                "✅ Processor: Ticket created: %s",
                result.get("data", {}).get("createTicket", {}).get("id"),
            )
            ticket_created = True

    except httpx.HTTPStatusError as e:
        logger.exception(
            "⚠️ Processor: GraphQL HTTP Error %s: %s", e.response.status_code, e.response.text
        )
    except Exception:
        logger.exception("⚠️ Processor: Failed to create ticket via GraphQL")

    async with postgres_session_manager.session_factory.begin() as session:
        try:
            new_email = ReceivedEmail(
                organization_id=task.organization_id,
                email_settings_id=task.settings_id,
                subject=task.subject,
                from_email=task.from_email,
                body_text=task.body,
                is_processed_by_api=ticket_created,
            )
            session.add(new_email)
            await session.commit()
            logger.info("💾 Processor: Успешно сохранено.")

            # Отправляем автоответ пользователю
            try:
                auto_reply = SendEmailEntity(
                    settings_id=task.settings_id,
                    to=task.from_email,
                    subject="Ваша жалоба принята",
                    body="Ваша жалоба принята, скоро вам ответит оператор",
                )
                await broker.publish(auto_reply, queue=settings.QUEUES.SEND_EMAILS)
                logger.info("📨 Processor: Автоответ отправлен на %s", task.from_email)
            except Exception:
                logger.exception("⚠️ Processor: Ошибка отправки автоответа (письмо сохранено)")
        except Exception:
            logger.exception("Ошибка сохранения")
            await session.rollback()
