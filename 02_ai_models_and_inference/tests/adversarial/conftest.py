#!/usr/bin/env python3
"""
Adversarial Test Suite Fixtures & Configuration
"""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1]
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# Re-export fixtures from tests.e2e.conftest
from tests.e2e.conftest import (
    cluster_matrix,
    model_matrix,
    dht_ring,
    multipath_helper,
    MockDHTRing,
    MultipathChunk,
    HEADER_MAGIC,
    HEADER_FORMAT,
    HEADER_SIZE,
)

__all__ = [
    "cluster_matrix",
    "model_matrix",
    "dht_ring",
    "multipath_helper",
    "MockDHTRing",
    "MultipathChunk",
    "HEADER_MAGIC",
    "HEADER_FORMAT",
    "HEADER_SIZE",
]
