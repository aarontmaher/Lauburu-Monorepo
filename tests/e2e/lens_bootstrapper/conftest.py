# -*- coding: utf-8 -*-
"""
Pytest configuration and shared fixtures for Sovereign Lens Bootstrapper E2E tests.
"""

import os
import sys
from pathlib import Path
import pytest

TEST_SUITE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_SUITE_DIR.parent.parent

# Ensure project root and test directories are on python path
for p in [
    str(PROJECT_ROOT),
    str(TEST_SUITE_DIR),
    str(PROJECT_ROOT / "00_core_infrastructure" / "lens_bootstrapper"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def bootstrapper_dir() -> Path:
    return PROJECT_ROOT / "00_core_infrastructure" / "lens_bootstrapper"


@pytest.fixture(scope="session")
def obsidian_vault_dir() -> Path:
    return PROJECT_ROOT / "obsidian_vault"
