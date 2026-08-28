"""
Unit tests for App Catalog API /api/apps on Port 4000 Hub.
Verifies that all 17 applications are properly registered with complete metadata.
"""

import pytest
from fastapi.testclient import TestClient
from ..server import app, CATALOG_APPS


@pytest.fixture
def client():
    return TestClient(app)


def test_get_apps_catalog(client):
    """Verify /api/apps returns 17 valid app definitions."""
    resp = client.get("/api/apps")
    assert resp.status_code == 200
    apps = resp.json()
    assert isinstance(apps, list)
    assert len(apps) == 17

    app_ids = {a["id"] for a in apps}
    expected_ids = {
        "lauburu_super_app",
        "lauburu_zone2_endurance",
        "lauburu_bluetooth_sensor",
        "lauburu_compute_hub",
        "lauburu_grappling_3d",
        "lauburu_termux_daemon",
        "lauburu_shopify_ai",
        "lauburu_swarm_dashboard",
        "lauburu_movesense_hub",
        "lauburu_hemodynamics_cloud",
        "lauburu_openclaw",
        "lauburu_memory_sync",
        "lauburu_red_blue_security",
        "lauburu_lora_evolution",
        "lauburu_kinematics_lab",
        "lauburu_nomad_courier",
        "lauburu_app_store"
    }
    assert expected_ids.issubset(app_ids)

    for a in apps:
        assert "id" in a and a["id"]
        assert "name" in a and a["name"]
        assert "category" in a and a["category"]
        assert "badge" in a and a["badge"]
        assert "route" in a and a["route"]
        assert "port" in a and isinstance(a["port"], int)
        assert "features" in a and isinstance(a["features"], list) and len(a["features"]) > 0
