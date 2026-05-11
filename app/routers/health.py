from fastapi import APIRouter

from app.models.database import utcnow
from app.models.schemas import HealthResponse

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=utcnow(),
        database="connected",
    )
