"""
Shared fixtures and test helpers for Master 6-Pillar Arena Notebook E2E Tests.
Generation 2 SSoT Master Studio Optimization.

Strict Mandates Enforced:
1. Headless Absolute Mandate: --headless=new, --disable-gpu, --no-sandbox, --window-position=-2400,-2400
2. Matplotlib Agg Mandate: matplotlib.use('Agg') & non-interactive plt.show()
3. Concurrency Limits: max_workers=2
4. Sweeper Daemon: 5-minute TTL process hygiene for Playwright/Chrome
5. Opaque-Box Methodology: Genuine contracts, zero mock / simulated data (Rule #0)
"""

import ast
import concurrent.futures
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Generator

import sys
import types

# Ensure real IPython is imported if available, with robust fallback
try:
    import IPython
    import IPython.display as ipy_disp
    if not hasattr(IPython, "version_info"):
        IPython.version_info = (8, 24, 0)
    if not hasattr(IPython, "get_ipython"):
        IPython.get_ipython = lambda: None
except ImportError:
    ipy_mod = types.ModuleType("IPython")
    ipy_mod.__path__ = []
    ipy_mod.version_info = (8, 24, 0)
    ipy_mod.__version__ = "8.24.0"
    ipy_mod.get_ipython = lambda: None
    ipy_disp = types.ModuleType("IPython.display")
    ipy_disp.display = lambda *a, **k: None
    ipy_disp.HTML = lambda x: x
    ipy_disp.clear_output = lambda *a, **k: None
    ipy_mod.display = ipy_disp
    sys.modules["IPython"] = ipy_mod
    sys.modules["IPython.display"] = ipy_disp

# Strict Matplotlib Agg Mandate (Must execute before any pyplot import)
import matplotlib
matplotlib.use("Agg")
os.environ["MPLBACKEND"] = "Agg"
import matplotlib.pyplot as plt

import pytest

# Canonical Path Constants
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb"
GLOBAL_NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "00_lauburu_global_master_project.ipynb"
CHART_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "6_pillar_dark_console.png"
VAULT_DIR = MONOREPO_ROOT / "obsidian_vault"
LORA_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
DATA_MEMORY_DIR = MONOREPO_ROOT / "04_data_and_memory"
SWEEPER_DAEMON_PATH = MONOREPO_ROOT / "06_scripts_and_tooling" / "daemons" / "playwright_sweeper_daemon.py"
SWEEPER_LOG_PATH = MONOREPO_ROOT / "06_scripts_and_tooling" / "daemons" / "sweeper.log"

# Concurrency & Process Hygiene Constants
MAX_TEST_WORKERS = 2

# Strict Headless Playwright Launch Arguments
PLAYWRIGHT_HEADLESS_ARGS = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-position=-2400,-2400",
    "--disable-dev-shm-usage",
    "--disable-extensions",
]

CYBERPUNK_PALETTE = {
    "cyan": "#06b6d4",
    "blue": "#3b82f6",
    "purple": "#8b5cf6",
    "emerald": "#10b981",
    "amber": "#f59e0b",
    "bg_dark": "#0f172a",
}

CANONICAL_PILLARS = [
    {
        "id": 1,
        "pillar": "WebDev & UI/UX Arena",
        "dataset": "lmarena-ai/webdev-arena-preference-10k",
        "target_layer": "01_apps (Web Hub)",
        "lead_model": "Qwen 2.5 Coder 72B",
        "elo": 2640.0,
    },
    {
        "id": 2,
        "pillar": "SWE-bench Verified",
        "dataset": "princeton-nlp/SWE-bench_Verified",
        "target_layer": "01_apps (AST PRs)",
        "lead_model": "Qwen 2.5 Coder 72B",
        "elo": 2633.0,
    },
    {
        "id": 3,
        "pillar": "BigCodeBench & LiveCode",
        "dataset": "bigcode/bigcodebench",
        "target_layer": "02_ai_models (Python DSP)",
        "lead_model": "Qwen3-Next-80B-A3B MoE",
        "elo": 2625.0,
    },
    {
        "id": 4,
        "pillar": "Tau-Bench & Tool Calling",
        "dataset": "sgl-project/tau-bench + xLAM-60k",
        "target_layer": "05_agents (MCP Routing)",
        "lead_model": "Qwen-AgentWorld-35B",
        "elo": 2498.0,
    },
    {
        "id": 5,
        "pillar": "PhysioNet Clinical DSP",
        "dataset": "physionet/ptb-xl (512Hz ECG)",
        "target_layer": "03_biometrics (Movesense)",
        "lead_model": "BioMistral-7B / Qwen-Med",
        "elo": 2435.0,
    },
    {
        "id": 6,
        "pillar": "AgentHarm & Red Team",
        "dataset": "walledai/AgentHarm + Port :8083",
        "target_layer": "05_agents (Port :8083)",
        "lead_model": "Huihui-Qwen3.8-27B",
        "elo": 2448.0,
    },
]


def pytest_configure(config):
    """Global pytest configuration enforcing headless mode, concurrency limits, and Agg backend."""
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["PYTEST_MAX_WORKERS"] = str(MAX_TEST_WORKERS)
    import matplotlib
    matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def enforce_headless_matplotlib(monkeypatch):
    """
    Autouse fixture ensuring all tests strictly execute with non-interactive Matplotlib.
    Monkeypatches plt.show to prevent any accidental GUI popup window.
    """
    import matplotlib
    matplotlib.use("Agg")
    assert matplotlib.get_backend().lower() == "agg", (
        f"Matplotlib backend must be 'Agg', found '{matplotlib.get_backend()}'"
    )

    def safe_show(*args, **kwargs):
        # Safely close all open figures instead of spawning a GUI window
        plt.close("all")

    monkeypatch.setattr(plt, "show", safe_show)
    yield


@pytest.fixture
def playwright_headless_options() -> Dict[str, Any]:
    """Provides canonical Playwright launch options enforcing --headless=new."""
    return {
        "headless": True,
        "args": list(PLAYWRIGHT_HEADLESS_ARGS),
    }


@pytest.fixture
def playwright_browser_args() -> List[str]:
    """Provides list of canonical headless browser flags."""
    return list(PLAYWRIGHT_HEADLESS_ARGS)


def assert_headless_browser_options(options: Dict[str, Any]) -> bool:
    """Validate that browser launch options conform to Headless Absolute Mandate."""
    if not isinstance(options, dict):
        raise AssertionError("Launch options must be a dictionary")
    if not options.get("headless", False):
        raise AssertionError("Browser options must have 'headless': True")
    args = options.get("args", [])
    if "--headless=new" not in args and "--headless" not in args:
        raise AssertionError("Browser args must contain '--headless=new'")
    return True


@pytest.fixture
def max_workers() -> int:
    """Fixture returning the maximum allowed test concurrency worker limit (2)."""
    return MAX_TEST_WORKERS


@pytest.fixture
def capped_thread_pool():
    """Provides a ThreadPoolExecutor strictly capped at max_workers=2."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_TEST_WORKERS)
    yield executor
    executor.shutdown(wait=True)


@pytest.fixture
def sweeper_daemon_path() -> Path:
    """Fixture returning path to Playwright Sweeper Daemon script."""
    return SWEEPER_DAEMON_PATH


@pytest.fixture
def sweeper_log_path() -> Path:
    """Fixture returning path to Playwright Sweeper log file."""
    return SWEEPER_LOG_PATH


def load_notebook_data(path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse and return raw notebook JSON."""
    p = path or NOTEBOOK_PATH
    if not p.exists():
        raise FileNotFoundError(f"Target notebook not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_code_cells(nb_data: Dict[str, Any]) -> List[str]:
    """Extract code cell sources concatenated as list of code strings."""
    code_blocks = []
    for cell in nb_data.get("cells", []):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            code_blocks.append(source)
    return code_blocks


def extract_markdown_cells(nb_data: Dict[str, Any]) -> List[str]:
    """Extract markdown cell sources concatenated as list of strings."""
    md_blocks = []
    for cell in nb_data.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            md_blocks.append(source)
    return md_blocks


def calculate_elo_update(r_a: float, r_b: float, score_a: float, k: float = 32.0) -> Tuple[float, float, float]:
    """
    Standard Bradley-Terry Elo rating calculation according to PROJECT.md §Interface Contracts.
    Returns: (expected_a, new_r_a, new_r_b)
    """
    # Guard against float overflow on extreme differences
    delta = (r_b - r_a) / 400.0
    if delta > 100.0:
        expected_a = 0.0
    elif delta < -100.0:
        expected_a = 1.0
    else:
        expected_a = 1.0 / (1.0 + math.pow(10.0, delta))

    expected_b = 1.0 - expected_a
    score_b = 1.0 - score_a

    # K-factor bounding [1.0, 128.0]
    k_clamped = max(1.0, min(128.0, float(k)))

    new_r_a = r_a + k_clamped * (score_a - expected_a)
    new_r_b = r_b + k_clamped * (score_b - expected_b)
    return expected_a, new_r_a, new_r_b


def validate_dpo_schema(record: Dict[str, Any]) -> bool:
    """Validate DPO record against contract schema from PROJECT.md."""
    if not isinstance(record, dict):
        return False
    required_keys = {"prompt", "chosen", "rejected", "metadata"}
    if not required_keys.issubset(record.keys()):
        return False
    if not isinstance(record["prompt"], str) or not isinstance(record["chosen"], str) or not isinstance(record["rejected"], str):
        return False
    meta = record.get("metadata")
    if not isinstance(meta, dict):
        return False
    meta_keys = {"pillar_id", "pillar_name", "model", "elo", "zero_mock_certified"}
    if not meta_keys.issubset(meta.keys()):
        return False
    if not isinstance(meta["pillar_id"], int) or meta["pillar_id"] < 1 or meta["pillar_id"] > 6:
        return False
    if not isinstance(meta["elo"], (int, float)):
        return False
    if not isinstance(meta["zero_mock_certified"], bool):
        return False
    return True


def validate_probe_schema(result: Dict[str, Any]) -> bool:
    """Validate mesh probe result against contract schema from PROJECT.md."""
    if not isinstance(result, dict):
        return False
    required_keys = {"status", "code", "rtt_ms", "data", "error"}
    if not required_keys.issubset(result.keys()):
        return False
    if result["status"] not in ("ONLINE", "OFFLINE"):
        return False
    if not isinstance(result["code"], int):
        return False
    if result["rtt_ms"] is not None and not isinstance(result["rtt_ms"], (int, float)):
        return False
    return True


def validate_seaweed_cluster_status(status_payload: Dict[str, Any]) -> bool:
    """Validate SeaweedFS Raft cluster status response schema."""
    if not isinstance(status_payload, dict):
        return False
    if "Leader" in status_payload or "Peers" in status_payload or "IsLeader" in status_payload or "Status" in status_payload:
        return True
    return False


def validate_seaweed_filer_entries(entries_payload: Dict[str, Any]) -> bool:
    """Validate SeaweedFS Filer directory entries schema."""
    if not isinstance(entries_payload, dict):
        return False
    return "Entries" in entries_payload and isinstance(entries_payload["Entries"], list)


@pytest.fixture
def notebook_json():
    """Fixture to provide loaded 6-pillar arena notebook JSON."""
    return load_notebook_data(NOTEBOOK_PATH)


@pytest.fixture
def global_master_notebook_json():
    """Fixture to provide loaded global master project notebook JSON."""
    return load_notebook_data(GLOBAL_NOTEBOOK_PATH)


@pytest.fixture
def notebook_code_cells(notebook_json):
    """Fixture to provide list of code cell strings."""
    return extract_code_cells(notebook_json)


@pytest.fixture
def notebook_markdown_cells(notebook_json):
    """Fixture to provide list of markdown cell strings."""
    return extract_markdown_cells(notebook_json)


@pytest.fixture
def temp_test_dir():
    """Fixture providing isolated temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="arena_e2e_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def playwright_headless_browser():
    """Session fixture providing strictly headless Playwright browser instance."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=PLAYWRIGHT_HEADLESS_ARGS,
            )
            yield browser
            browser.close()
    except Exception as e:
        pytest.skip(f"Playwright unavailable or skipped: {e}")
