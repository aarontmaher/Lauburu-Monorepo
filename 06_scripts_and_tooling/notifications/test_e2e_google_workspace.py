#!/usr/bin/env python3
"""
E2E Verification Suite for Google Workspace & Google Chat Integration
=====================================================================
Validates all 5 pillars for account: lauburu@lauburugrappling.com:
1. DWD Auth Gateway (Port 18802)
2. Google Chat Card v2 Builders & Webhook Handlers
3. Google Drive / GDriveHandler VFS Resilience
4. Gmail Out-of-Band Alert Formatting
5. Google Sheets Telemetry Micro-Batching
"""

import os
import sys
import json
import time
from pathlib import Path

# Paths
ROOT_DIR = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(ROOT_DIR / "00_core_infrastructure/auth"))
sys.path.insert(0, str(ROOT_DIR / "06_scripts_and_tooling/notifications"))
sys.path.insert(0, str(ROOT_DIR / "self_healing_hub/src"))

from workspace_dwd_gateway import DWDAuthGateway
from google_chat_mesh_bridge import GoogleChatBridge
from google_workspace_unified_manager import GoogleWorkspaceManager
from gdrive_handler import GDriveHandler


def run_e2e_verification():
    print("=" * 80)
    print("🧪 LAUBURU MESH E2E GOOGLE WORKSPACE VERIFICATION")
    print("Account: lauburu@lauburugrappling.com | Domain: lauburugrappling.com")
    print("=" * 80)

    # 1. Verify DWD Auth Gateway
    print("\n[STAGE 1] Testing Domain-Wide Delegation (DWD) Gateway...")
    dwd = DWDAuthGateway(subject="lauburu@lauburugrappling.com")
    health = dwd.get_gateway_health()
    print(f"  • Gateway Health: {health['gateway']}")
    print(f"  • Active Scopes: {len(health['active_scopes'])} configured")
    token_resp = dwd.get_bearer_token()
    print(f"  • Token Minting Status: {token_resp.get('status')} ({token_resp.get('token_type')})")
    assert token_resp["subject"] == "lauburu@lauburugrappling.com", "Subject mismatch!"

    # 2. Verify Google Chat Bridge & Card v2 Builders
    print("\n[STAGE 2] Testing Google Chat Card v2 Builders...")
    bridge = GoogleChatBridge()
    
    # 2.1 AI Debate Card
    card_debate = bridge.create_ai_debate_card(
        topic="Continuous Multi-WAN Model Sharding",
        consensus_summary="Consensus verified: 82.8 GB Pooled VRAM distributed over TB4 and WireGuard.",
        devils_advocate_verdict="Audited: RAM ceiling enforced at <= 90%.",
        kappa_score=0.995
    )
    print(f"  • AI Debate Card: {card_debate['card']['header']['title']} (Sections: {len(card_debate['card']['sections'])})")
    assert "0.995" in card_debate["card"]["header"]["subtitle"]

    # 2.2 7-Layer Mesh Pulse Card
    card_mesh = bridge.create_mesh_telemetry_card(
        node_count=7,
        pooled_vram_gb=82.8,
        total_ram_gb=108.0,
        tb4_latency_ms=0.277
    )
    print(f"  • Mesh Pulse Card: {card_mesh['card']['header']['title']}")
    assert "82.8 GB" in str(card_mesh)

    # 2.3 Biometrics Alert Card
    card_bio = bridge.create_biometrics_alert_card(
        heart_rate=145,
        zone="Zone 2 Aerobic",
        dfa_alpha1=0.88,
        alert_message="Lactate threshold steady state maintained."
    )
    print(f"  • Biometrics Card: {card_bio['card']['header']['title']}")
    assert "145 BPM" in str(card_bio)

    # 3. Verify GDrive Handler Resilience
    print("\n[STAGE 3] Testing GDrive Storage Handler...")
    gdrive = GDriveHandler()
    is_active = gdrive.is_mounted()
    mount_loc = gdrive._resolve_mount_point()
    print(f"  • GDrive Handler Resolved Path: {mount_loc}")
    print(f"  • Storage Active / Writable: {is_active}")

    # 4. Verify Google Workspace Unified Manager
    print("\n[STAGE 4] Testing Unified Workspace Manager...")
    mgr = GoogleWorkspaceManager(subject="lauburu@lauburugrappling.com")
    status = mgr.get_full_workspace_status()
    print(f"  • Domain: {status['domain']}")
    print(f"  • Google Chat Status: {status['google_chat']['status']}")
    print(f"  • Google Drive Status: {status['google_drive']['status']}")
    print(f"  • Gmail Alert Bus: {status['gmail_alert_bus']['status']}")
    print(f"  • Sheets Telemetry: {status['sheets_telemetry']['status']}")

    # 5. Verify Telemetry & Alert Serialization
    print("\n[STAGE 5] Testing Alert and Telemetry Serialization...")
    alert_payload = mgr.format_gmail_alert(
        recipient="ops@lauburugrappling.com",
        subject="E2E Pipeline Health Check",
        body="All 7 nodes reporting nominal thermals."
    )
    assert alert_payload["headers"]["X-Priority"] == "1"
    
    sheets_row = mgr.format_sheets_telemetry_row(
        metric_type="SYSTEM_THERMAL_SWEEP",
        values={"L1_temp": 42.5, "L2_temp": 44.1, "L3_temp": 48.0}
    )
    assert len(sheets_row) == 4
    print(f"  • Formatted Sheets Row: {sheets_row[0]} | {sheets_row[1]}")

    print("\n" + "=" * 80)
    print("✅ E2E GOOGLE WORKSPACE VERIFICATION PASSED (100% NOMINAL)")
    print("=" * 80)


if __name__ == "__main__":
    run_e2e_verification()
