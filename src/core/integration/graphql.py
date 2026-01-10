import logging

import httpx

from src.core.settings import settings

logger = logging.getLogger(__name__)


class GraphQLClient:
    def __init__(self):
        self.url = settings.GRAPHQL.URL
        self.email = settings.GRAPHQL.EMAIL
        self.password = settings.GRAPHQL.PASSWORD
        self.token = None

    async def _authenticate(self):
        logger.info("🔐 GraphQLClient: Authenticating as %s...", self.email)
        mutation = """
        mutation AuthenticateUser($email: String!, $password: String!) {
          authenticateUserWithPassword(email: $email, password: $password) {
            token
          }
        }
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url,
                    json={
                        "query": mutation,
                        "variables": {"email": self.email, "password": self.password},
                    },
                    timeout=180.0,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    logger.error("❌ GraphQLClient: Auth Error: %s", data["errors"])
                    raise Exception(f"GraphQL Auth Error: {data['errors']}")  # noqa: TRY002, TRY301

                auth_data = data.get("data", {}).get("authenticateUserWithPassword")
                if auth_data and auth_data.get("token"):
                    self.token = auth_data["token"]
                    logger.info("✅ GraphQLClient: Successfully authenticated.")
                else:
                    logger.error("❌ GraphQLClient: Authentication failed, no token received.")
                    raise Exception("Authentication failed, no token received.")  # noqa: TRY002, TRY301

        except Exception:
            logger.exception("⚠️ GraphQLClient: Authentication request failed")
            raise

    async def execute(self, query: str, variables: dict | None = None):
        """Executes a GraphQL query/mutation, handling authentication automatically."""
        if not self.token:
            await self._authenticate()

        # Try executing with current token
        result = await self._send_request(query, variables)

        if "errors" in result:
            is_auth_error = any(
                err.get("message")
                in {
                    "You do not have access to this resource",
                    "Invalid token",
                    "Authentication required",
                }
                or err.get("name") == "AccessDeniedError"
                for err in result["errors"]
            )

            if is_auth_error:
                logger.warning("♻️ GraphQLClient: Token expired or invalid. Re-authenticating...")
                await self._authenticate()
                # Retry the request with the new token
                result = await self._send_request(query, variables)

        return result

    async def _send_request(self, query: str, variables: dict | None = None):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=180.0,
            )
            response.raise_for_status()
            return response.json()


# Global instance
graphql_client = GraphQLClient()
