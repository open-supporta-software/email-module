from fastapi import APIRouter, FastAPI
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware

from src.core.exceptions import register_error_handlers
from src.core.settings import settings
from src.utils.api.v1 import router as utils_router


def create_app() -> FastAPI:
    app = FastAPI(
        debug=settings.DEBUG,
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
        default_response_class=ORJSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.SECURITY.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    api_v1_router = APIRouter(prefix=settings.API_PREFIX + "/v1")
    api_v1_router.include_router(utils_router)

    app.include_router(api_v1_router)

    return app
