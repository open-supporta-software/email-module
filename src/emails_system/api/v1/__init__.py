from fastapi import APIRouter

from src.emails_system.api.v1.routers import email_settings_router

router = APIRouter()

router.include_router(email_settings_router, prefix="/emails", tags=["emails settings"])
