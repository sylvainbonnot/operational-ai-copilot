from fastapi import APIRouter

from app.core.config import get_settings
from app.models.api import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(version="0.1.0", environment=settings.environment)
