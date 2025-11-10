from fastapi import APIRouter

from src.emails_system.api.v1 import router as v1_router

router = APIRouter(prefix="/v1")

router.include_router(v1_router)
