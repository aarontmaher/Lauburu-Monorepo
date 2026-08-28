"""
Central API v1 router combining all endpoint modules.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import hemodynamics, sessions, rag, health, ai_stream

api_router = APIRouter()

api_router.include_router(hemodynamics.router, prefix="/hemodynamics", tags=["hemodynamics"])
api_router.include_router(sessions.router, prefix="/session", tags=["sessions"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions-plural-alias"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(ai_stream.router, prefix="/ai", tags=["ai-diagnostic"])
api_router.include_router(ai_stream.router, prefix="/ai/diagnostic", tags=["ai-diagnostic-alias"])
api_router.include_router(health.router, tags=["health"])
