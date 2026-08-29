"""
Presentation Subpackage for Movesense Hub.
Contains Textual TUI dashboard, Web-TUI adapter, and Next.js Canvas Oscilloscope PWA connector.
"""

from .tui import MovesenseReadinessTUIApp, run_app
from .web_adapter import OscilloscopePwaConnector, ReadinessRestAdapter, WebTuiAdapter

__all__ = [
    "MovesenseReadinessTUIApp",
    "run_app",
    "WebTuiAdapter",
    "OscilloscopePwaConnector",
    "ReadinessRestAdapter",
]
