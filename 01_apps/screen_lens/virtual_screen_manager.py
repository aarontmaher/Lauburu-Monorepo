"""
virtual_screen_manager.py — Import Shim
========================================
Convenience import shim exposing VirtualScreenManager and public symbols
from `01_apps/screen_lens/src/virtual_screen_manager.py`.
"""

import importlib.util
from pathlib import Path
import sys

_src_file = Path(__file__).resolve().parent / "src" / "virtual_screen_manager.py"
_spec = importlib.util.spec_from_file_location("virtual_screen_manager_src", _src_file)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load module spec from {_src_file}")

_mod = importlib.util.module_from_spec(_spec)
sys.modules["virtual_screen_manager_src"] = _mod
_spec.loader.exec_module(_mod)

VirtualScreenManager = _mod.VirtualScreenManager
DisplayVerificationResult = _mod.DisplayVerificationResult
VirtualScreenError = _mod.VirtualScreenError
BetterDisplayNotFoundError = _mod.BetterDisplayNotFoundError
DisplayCreationError = _mod.DisplayCreationError
DisplayConfigurationError = _mod.DisplayConfigurationError
DisplayCaptureError = _mod.DisplayCaptureError
get_virtual_screen_manager = _mod.get_virtual_screen_manager
QUARTZ_AVAILABLE = _mod.QUARTZ_AVAILABLE
PIL_AVAILABLE = _mod.PIL_AVAILABLE

__all__ = [
    "VirtualScreenManager",
    "DisplayVerificationResult",
    "VirtualScreenError",
    "BetterDisplayNotFoundError",
    "DisplayCreationError",
    "DisplayConfigurationError",
    "DisplayCaptureError",
    "get_virtual_screen_manager",
    "QUARTZ_AVAILABLE",
    "PIL_AVAILABLE",
]
