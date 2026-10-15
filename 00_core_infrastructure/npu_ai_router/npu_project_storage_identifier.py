#!/usr/bin/env python3
"""
00_core_infrastructure/npu_ai_router/npu_project_storage_identifier.py
Forwarder for the NPU & Neo Automatic Project & Storage System Identifier.
Location: 01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena/
"""

from __future__ import annotations
import sys
from pathlib import Path

_SANDBOX_PATH = Path("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena")
if str(_SANDBOX_PATH) not in sys.path:
    sys.path.insert(0, str(_SANDBOX_PATH))

try:
    from npu_project_storage_identifier import (
        NpuProjectStorageIdentifier,
        ProjectMappingVerdict,
        FolderAnalysis,
        CANONICAL_SUBSYSTEMS,
        default_identifier,
        main
    )
except ImportError as e:
    raise ImportError(f"Failed to load npu_project_storage_identifier from {_SANDBOX_PATH}: {e}")

if __name__ == "__main__":
    main()
