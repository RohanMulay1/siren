from fastapi import APIRouter
from pydantic import BaseModel
from ...memory import get_qdrant_client, count_incidents
from ...config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    qdrant_incidents: int
    environment: str
    version: str = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    try:
        qdrant = get_qdrant_client()
        incident_count = count_incidents(qdrant)
    except Exception:
        incident_count = -1

    return HealthResponse(
        status="ok",
        qdrant_incidents=incident_count,
        environment=settings.environment,
    )
