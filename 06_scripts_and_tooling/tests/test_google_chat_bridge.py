import pytest
import json
import sys
from pathlib import Path
import tempfile
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "notifications"))
from google_chat_mesh_bridge import GoogleChatBridge


def test_google_chat_bridge_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "chat_config.json"
        bridge = GoogleChatBridge(config_path=cfg_path)
        
        test_url = "https://chat.googleapis.com/v1/spaces/TEST_SPACE/messages?key=123"
        bridge.save_config(test_url, workspace_email="lauburu@lauburugrappling.com")
        
        assert bridge.webhook_url == test_url
        assert bridge.workspace_email == "lauburu@lauburugrappling.com"
        assert cfg_path.exists()
        
        # Verify read back
        bridge2 = GoogleChatBridge(config_path=cfg_path)
        assert bridge2.webhook_url == test_url
        assert bridge2.workspace_email == "lauburu@lauburugrappling.com"


def test_create_ai_debate_card():
    bridge = GoogleChatBridge()
    card = bridge.create_ai_debate_card(
        topic="Test Topic",
        consensus_summary="Consensus details here",
        devils_advocate_verdict="Devil verdict details",
        kappa_score=0.995
    )
    
    assert "cardId" in card
    assert "card" in card
    assert card["card"]["header"]["title"] == "🏛️ Lauburu Tri-Orchestrator AI Debate"
    assert "0.995" in card["card"]["header"]["subtitle"]
    assert len(card["card"]["sections"]) == 4


def test_create_mesh_telemetry_card():
    bridge = GoogleChatBridge()
    card = bridge.create_mesh_telemetry_card(
        node_count=7,
        pooled_vram_gb=82.8,
        total_ram_gb=108.0,
        tb4_latency_ms=0.277
    )
    
    assert "cardId" in card
    assert "card" in card
    assert "82.8 GB" in str(card)
    assert "0.277 ms RTT" in str(card)


def test_create_biometrics_alert_card():
    bridge = GoogleChatBridge()
    card = bridge.create_biometrics_alert_card(
        heart_rate=145,
        zone="Zone 2 Aerobic",
        dfa_alpha1=0.88,
        alert_message="Optimal lactate steady state maintained."
    )
    
    assert "cardId" in card
    assert "145 BPM" in str(card)
    assert "0.88" in str(card)
