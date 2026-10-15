import pytest
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/notifications")))
from mesh_cross_device_chat_agent import MeshCrossDeviceAgent


def test_mesh_cross_device_agent_card_builder():
    agent = MeshCrossDeviceAgent()
    mock_sweep = {
        "timestamp": "2026-09-02T05:25:00Z",
        "nodes": {
            "L1_mac_mini": {"status": "ONLINE", "role": "Host Controller"},
            "L2_macbook_pro": {"status": "ONLINE", "role": "TB4 Bridge"},
            "L3_linux_head": {"status": "ONLINE", "uptime": "up 11 days"},
            "L5_macbook_air": {"status": "ONLINE", "role": "Metal Worker"},
            "L6_pixel_10_pro_xl": {"status": "ONLINE", "battery_pct": 60, "temp_c": 27.9},
            "L7_samsung_s20": {"status": "ONLINE", "battery_pct": 84, "model": "SM-G986B"}
        }
    }
    
    card = agent.create_cross_device_pulse_card(mock_sweep)
    assert "cardId" in card
    assert "card" in card
    assert "PIXEL 10 PRO XL" in str(card)
    assert "SAMSUNG S20+" in str(card)
    assert "60% (27.9°C)" in str(card)
    assert "84% (ADB Active)" in str(card)
