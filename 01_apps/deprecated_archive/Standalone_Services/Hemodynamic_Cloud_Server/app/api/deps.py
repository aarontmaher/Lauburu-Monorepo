"""
FastAPI dependency injectors for database managers and services.
"""

from app.storage.sqlite_manager import SqliteManager, get_sqlite_manager
from app.storage.chroma_manager import ChromaManager, get_chroma_manager
from app.services.inversion_service import InversionService, get_inversion_service
from app.services.trend_hunting_service import TrendHuntingService, get_trend_hunting_service


def get_db() -> SqliteManager:
    return get_sqlite_manager()


def get_vector_store() -> ChromaManager:
    return get_chroma_manager()


def get_inversion() -> InversionService:
    return get_inversion_service()


def get_trends() -> TrendHuntingService:
    return get_trend_hunting_service()
