"""
FastAPI Main Application Entrypoint for Hemodynamic Cloud Server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.api.deps import get_inversion
from app.api.v1.endpoints.hemodynamics import websocket_telemetry_stream
from app.api.v1.endpoints.health import health_check
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import ZeroPiiSanitizationMiddleware
from app.models.schemas import HealthStatusResponse
from app.storage.chroma_manager import get_chroma_manager
from app.storage.sqlite_manager import get_sqlite_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database managers
    get_sqlite_manager()
    get_chroma_manager()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Private Cloud Hemodynamic Inversion & Zero-PII Telemetry Server",
    lifespan=lifespan
)

# 1. Zero-PII Sanitization Middleware (Strict PII Rejection Gate)
app.add_middleware(ZeroPiiSanitizationMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount API v1 Routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# 4. Root Health Endpoint
@app.get("/health", response_model=HealthStatusResponse, tags=["health"])
async def root_health_check():
    return await health_check()

# 5. Root WebSocket Endpoint
@app.websocket("/ws/live-stream")
async def root_websocket_live_stream(websocket: WebSocket):
    inversion_service = get_inversion()
    await websocket_telemetry_stream(websocket=websocket, service=inversion_service)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
