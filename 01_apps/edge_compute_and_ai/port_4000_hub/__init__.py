"""
Lauburu Canonical Port 4000 Hub.
Consolidated FastAPI server for user accounts, Shopify subscription integration,
and Bluetooth Movesense/Polar 128Hz telemetry ingestion.
"""

from .server import app

__all__ = ["app"]
