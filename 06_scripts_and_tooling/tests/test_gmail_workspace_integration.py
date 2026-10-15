import pytest
import os
import sys
import json
from pathlib import Path

# Setup paths
ROOT_DIR = Path("/Volumes/Lauburu-Monorepo")
AUTH_DIR = ROOT_DIR / "00_core_infrastructure/auth"
NOTIF_DIR = ROOT_DIR / "06_scripts_and_tooling/notifications"
HUB_SRC = ROOT_DIR / "00_core_infrastructure/self_healing_hub/src"

sys.path.insert(0, str(AUTH_DIR))
sys.path.insert(0, str(NOTIF_DIR))
sys.path.insert(0, str(HUB_SRC))

from workspace_dwd_gateway import DWDAuthGateway
from gmail_workspace_client import GmailWorkspaceClient
from google_workspace_unified_manager import GoogleWorkspaceManager


def test_gmail_config_exists_and_valid():
    cfg_path = ROOT_DIR / "00_core_infrastructure/config/gmail_workspace_config.json"
    assert cfg_path.exists(), "Configuration file must exist"
    data = json.loads(cfg_path.read_text())
    assert "accounts" in data
    assert "lauburu@lauburugrappling.com" in data["accounts"]
    assert "aaron.t.maher@gmail.com" in data["accounts"]
    assert data["default_sender"] in data["accounts"]


def test_dwd_gateway_discovery_and_health():
    gateway = DWDAuthGateway()
    health = gateway.get_gateway_health()
    assert health["gateway"] == "Port 18802 DWD Auth Sentinel"
    assert health["workspace_domain"] == "lauburugrappling.com"
    assert health["gmail_config_exists"] is True
    assert health["adc_exists"] is True


def test_gmail_mime_builder():
    client = GmailWorkspaceClient()
    msg = client.build_mime_message(
        sender="lauburu@lauburugrappling.com",
        to="aaron.t.maher@gmail.com",
        subject="Test Out-of-Band Alert",
        body="Telemetry alert text content",
        html="<p>Telemetry alert HTML content</p>",
        priority="1"
    )
    assert msg["From"] == "lauburu@lauburugrappling.com"
    assert msg["To"] == "aaron.t.maher@gmail.com"
    assert msg["Subject"] == "Test Out-of-Band Alert"
    assert msg["X-Priority"] == "1"
    assert "lauburugrappling.com" in msg["Message-ID"]
    assert msg.is_multipart()


def test_gmail_client_live_account_audit():
    client = GmailWorkspaceClient()
    # Test personal admin account with verified App Password
    status = client.check_account_health("aaron.t.maher@gmail.com")
    assert status["account"] == "aaron.t.maher@gmail.com"
    assert status["app_password_configured"] is True
    assert status["status"] == "HEALTHY"
    assert status["imap_status"] == "AUTHENTICATED"
    assert status["smtp_status"] == "AUTHENTICATED"
    assert isinstance(status["inbox_total"], int)
    assert status["inbox_total"] > 0
    assert status["round_trip_ms"] is not None
    assert status["round_trip_ms"] > 0


def test_gmail_client_clean_awaiting_state():
    client = GmailWorkspaceClient()
    # lauburu@lauburugrappling.com currently awaits domain app password / service account key
    status = client.check_account_health("lauburu@lauburugrappling.com")
    assert status["account"] == "lauburu@lauburugrappling.com"
    assert status["status"] == "AWAITING_CREDENTIALS"
    assert status["inbox_total"] is None  # Zero-mock: must not fabricate fake counts


def test_workspace_manager_integration():
    mgr = GoogleWorkspaceManager()
    status = mgr.get_full_workspace_status(probe_gmail=False)
    assert status["domain"] == "lauburugrappling.com"
    assert status["gmail_alert_bus"]["status"] == "ENABLED"
    assert "lauburu@lauburugrappling.com" in status["gmail_alert_bus"]["configured_accounts"]
    assert "aaron.t.maher@gmail.com" in status["gmail_alert_bus"]["configured_accounts"]


def test_flask_api_routes_registered():
    hub_site_packages = ROOT_DIR / "00_core_infrastructure/self_healing_hub/.venv/lib/python3.13/site-packages"
    if hub_site_packages.exists() and str(hub_site_packages) not in sys.path:
        sys.path.insert(0, str(hub_site_packages))
    from api_server import app
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/workspace/status" in rules
    assert "/api/workspace/gmail/status" in rules
    assert "/api/workspace/gmail/inbox" in rules
    assert "/api/workspace/gmail/send" in rules
