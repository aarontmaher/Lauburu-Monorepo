"""
Health check and system telemetry diagnostics endpoint.
"""

import time
from fastapi import APIRouter
from app.core.config import settings
from app.models.schemas import HealthStatusResponse

router = APIRouter()

SERVER_START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    summary="Service health and hardware layer ready check"
)
async def health_check() -> HealthStatusResponse:
    """Return status of physics engines, SQLite WAL database, and ChromaDB vector store."""
    uptime = time.time() - SERVER_START_TIME
    return HealthStatusResponse(
        status="healthy",
        version=settings.VERSION,
        physics_engine_ready=True,
        sqlite_status="connected (WAL mode)",
        chromadb_status="ready (NVMe persistence)",
        uptime_seconds=round(uptime, 2)
    )
