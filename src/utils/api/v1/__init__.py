from fastapi import APIRouter

from src.utils.api.v1.health import router as health_router

router = APIRouter(prefix="/utils")

router.include_router(health_router)
