from fastapi import APIRouter

router = APIRouter(prefix="", tags=["health"])


@router.get("/healthcheck")
async def healthcheck():
    return {"is_success": True}
