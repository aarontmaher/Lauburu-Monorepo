"""
01_apps/biometrics Package Root.
"""

import sys
from pathlib import Path

# Ensure movesense_hub is directly accessible
_hub_path = Path(__file__).parent / "movesense_hub"
if str(_hub_path) not in sys.path:
    sys.path.insert(0, str(_hub_path))
