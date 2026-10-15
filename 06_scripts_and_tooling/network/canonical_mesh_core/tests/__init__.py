"""
Tests package for Lauburu Canonical Mesh Core network monitoring.
"""

import sys
from pathlib import Path

# Ensure canonical_mesh_core is on sys.path
_CORE_DIR = Path(__file__).resolve().parent.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))
