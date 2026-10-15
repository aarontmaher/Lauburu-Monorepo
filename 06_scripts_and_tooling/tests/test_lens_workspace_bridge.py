import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/notifications")))

from lens_workspace_bridge import PIIRedactionFilter, KeyframeDiffFilter, LensWorkspaceBridge


def test_pii_redaction_filter():
    raw_secret = "Here is my key: AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q and password='my_super_secret_pw!'"
    clean = PIIRedactionFilter.redact(raw_secret)
    assert "[REDACTED_GOOGLE_API_KEY]" in clean
    assert "[REDACTED_SECRET]" in clean
    assert "my_super_secret_pw" not in clean


def test_keyframe_diff_filter():
    diff_filter = KeyframeDiffFilter()
    assert diff_filter.should_dispatch("Frame 1 text", is_critical_event=True) is True
    # Immediate non-critical duplicate should be throttled
    assert diff_filter.should_dispatch("Frame 1 text", is_critical_event=False, min_interval_s=10.0) is False


def test_lens_incident_card_builder():
    bridge = LensWorkspaceBridge()
    card = bridge.create_lens_incident_card(
        event_title="Test Incident",
        screen_summary="Test screen state with API Key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q",
        detected_app="VS Code / Python",
        severity="INFO"
    )
    assert "cardId" in card
    assert "card" in card
    assert "👁️ Screen Lens: Test Incident" in str(card)
    assert "[REDACTED_GOOGLE_API_KEY]" in str(card)
