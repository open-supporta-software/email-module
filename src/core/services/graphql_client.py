from typing import Any

import httpx
from loguru import logger

from src.core.settings import settings


class GraphQLClient:
    def __init__(self, url: str = settings.GRAPHQL.URL):
        self.url = url

    async def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.url,
                    json={"query": query, "variables": variables},
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()

                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                    raise Exception(f"GraphQL errors: {result['errors']}")  # noqa: TRY002, TRY301

                return result["data"]
            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred: {e}")
                raise
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                raise

    async def create_ticket(self, variables: dict[str, Any]) -> dict[str, Any]:
        mutation = """
        mutation createTicket($data: TicketCreateInput!) {
            createTicket(data: $data) {
                id
                number
                clientPhone
                property {
                    id
                }
                contact {
                    id
                }
                unitName
                unitType
            }
        }
        """

        return await self.execute(mutation, variables={"data": variables})


graphql_client = GraphQLClient()
