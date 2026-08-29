"""
Lauburu Universal Web-TUI Portal Package.
=========================================
Subsystem: 01_apps/web_tui_portal
Version: 1.0.0-CANONICAL

FastAPI + WebSocket async PTY engine rendering all 7 applications on Port 8088 at 120 FPS.
"""

from .serve_portal import (
    app,
    REGISTERED_APPS,
    render_app_page,
    reclaim_port,
    main,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "app",
    "REGISTERED_APPS",
    "render_app_page",
    "reclaim_port",
    "main",
]
