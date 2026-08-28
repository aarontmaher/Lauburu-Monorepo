#!/usr/bin/env python3
"""
test_sync_pipeline.py
Canonical Acceptance Verification Test Script at project root.

Direct standalone execution:
    python3 test_sync_pipeline.py
    python3 test_sync_pipeline.py --json
    python3 test_sync_pipeline.py --type ai_debate_consensus

Exit Code:
    0: Success (all 4 destinations verified with cryptographic SHA-256 parity)
    1: Failure (any destination assertion or parity check failed)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_sync_pipeline import main

if __name__ == "__main__":
    sys.exit(main())
