import sys
from pathlib import Path
import pytest

PORTAL_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/web_tui_portal")
if str(PORTAL_DIR) not in sys.path:
    sys.path.insert(0, str(PORTAL_DIR))

from serve_portal import app, REGISTERED_APPS, MONOREPO_ROOT

def test_registered_apps_structure():
    assert len(REGISTERED_APPS) >= 8
    for app_id, meta in REGISTERED_APPS.items():
        assert "name" in meta
        assert "tier" in meta
        assert "badge_class" in meta
        assert "cmd" in meta or "fallback_cmd" in meta

def test_fastapi_app_endpoints():
    paths = [getattr(r, "path", None) for r in app.routes if hasattr(r, "path")]
    assert "/" in paths
    assert "/api/status" in paths


def test_monorepo_root_exists():
    assert MONOREPO_ROOT.exists()
    assert (MONOREPO_ROOT / "01_apps").exists()
