from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.settings import settings


class PostgresSessionManager:
    def __init__(self):
        self.engine = self._create_engine()
        self.session_factory = self._create_session_factory()

    @staticmethod
    def _create_engine() -> AsyncEngine:
        return create_async_engine(
            settings.POSTGRES.URL,
            poolclass=AsyncAdaptedQueuePool,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=settings.DB_ECHO,
        )

    def _create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autobegin=False,
        )

    async def get_session(self) -> AsyncSession:
        return self.session_factory()


postgres_session_manager = PostgresSessionManager()
