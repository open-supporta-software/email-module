from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware

from src.core.exceptions import register_error_handlers
from src.core.settings import settings
from src.emails_system.api import router as emails_system_router
from src.emails_system.services.emails import broker
from src.utils.api import router as utils_router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        await broker.start()
        yield
        await broker.stop()

    app = FastAPI(
        debug=settings.DEBUG,
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.SECURITY.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    api_v1_router = APIRouter(prefix=settings.API_PREFIX)
    api_v1_router.include_router(utils_router)
    api_v1_router.include_router(emails_system_router)

    app.include_router(api_v1_router)

    return app
