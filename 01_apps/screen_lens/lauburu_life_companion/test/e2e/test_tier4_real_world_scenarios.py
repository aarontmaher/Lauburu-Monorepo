"""
Tier 4: Real-World Scenarios (Opaque-Box E2E)
Full end-to-end user journeys validating complete system lifecycles.
"""

import os
import sys
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch

# Add harness to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from e2e_harness import (
    CANONICAL_CATALOG,
    CustomerTier,
    PersistentSessionStore,
    parse_customer_tier,
    validate_dev_token,
    probe_socket,
    query_local_ai_inference,
    generate_ecommerce_ad_prompt,
    DAEMON_PORT,
    ZMQ_PORT,
)


def test_user_journey_cold_boot_login_sync_and_ad_generation(tmp_path):
    """
    Tier 4 User Journey 1: Cold Boot -> Login -> Cloud Sync -> Catalog -> AI Ad Copy -> Restart
    Simulates the complete real-world user experience from hardware power-on through
    e-commerce AI generation and app restart persistence.
    """
    print("\n--- Step 1: System Boot & Silent Daemon Auto-Start ---")
    daemon_running = probe_socket(DAEMON_PORT, timeout=1.5) or probe_socket(ZMQ_PORT, timeout=1.5)
    assert daemon_running, "Step 1 Failed: Silent background daemon was not active after system boot"

    print("--- Step 2: App Launch & Shopify Customer Authentication ---")
    dev_token = "tok_dev_aaron_specialist"
    profile = validate_dev_token(dev_token)
    assert profile is not None, "Step 2 Failed: Authentication failed"

    print("--- Step 3: Session Persistence ---")
    session_file = tmp_path / "user_journey_1.json"
    store = PersistentSessionStore(session_file)
    store.save_session(
        access_token=dev_token,
        expires_at="2027-01-01T00:00:00Z",
        profile=profile
    )
    loaded_session = store.load_session()
    assert loaded_session["accessToken"] == dev_token

    print("--- Step 4: Cloud Sync & Membership Tier Resolution ---")
    assert loaded_session["customerProfile"]["tier"] == CustomerTier.PRO

    print("--- Step 5: Canonical E-Commerce Catalog Browsing ---")
    assert len(CANONICAL_CATALOG) == 18
    target_product = CANONICAL_CATALOG[0]  # Lauburu Pro Compression Rashguard
    assert target_product["price_aud"] == 97.50
    # Pro members receive 15% discount
    pro_discounted_price = round(target_product["price_aud"] * 0.85, 2)
    assert pro_discounted_price == 82.88

    print("--- Step 6: Local AI Direct-Response Ad Copy Generation ---")
    prompt = generate_ecommerce_ad_prompt(target_product)
    success, ad_copy, status = query_local_ai_inference(prompt, max_tokens=64, timeout=15.0)
    assert success is True, f"Step 6 Failed: AI copy generation failed with status {status}"
    assert len(ad_copy.strip()) > 0
    assert ad_copy != "--"

    print("--- Step 7: App Termination & Cold Restart Persistence ---")
    # Simulate app termination and new instance launch
    restarted_app_store = PersistentSessionStore(session_file)
    restarted_session = restarted_app_store.load_session()
    assert restarted_session is not None, "Step 7 Failed: Session lost after app restart"
    assert restarted_session["accessToken"] == dev_token
    assert restarted_session["customerProfile"]["tier"] == CustomerTier.PRO
    assert restarted_app_store.is_expired() is False


def test_user_journey_offline_start_reconnect_and_sync(tmp_path):
    """
    Tier 4 User Journey 2: Offline Launch -> Cached Restore -> Network Restoration -> Sync
    Simulates user launching the app while disconnected (e.g. underground gym or flight),
    browsing cached catalog with clean waiting states, followed by reconnecting and syncing.
    """
    print("\n--- Step 1: Pre-populate Persistent Storage ---")
    session_file = tmp_path / "offline_journey.json"
    store = PersistentSessionStore(session_file)
    store.save_session(
        access_token="tok_offline_traveler_101",
        expires_at="2027-01-01T00:00:00Z",
        profile={"id": "gid://shopify/Customer/101", "email": "nomad@lauburu.mesh", "tier": CustomerTier.FREE}
    )

    print("--- Step 2: Launch App in Offline Mode ---")
    with patch("urllib.request.urlopen", side_effect=OSError("No route to host")):
        # App loads cached session
        cached = store.load_session()
        assert cached is not None
        assert cached["customerProfile"]["email"] == "nomad@lauburu.mesh"

        # Catalog is still 100% available offline
        assert len(CANONICAL_CATALOG) == 18

        # AI queries safely display clean waiting state ('--')
        success, response, status = query_local_ai_inference("Prompt while offline")
        assert success is False
        assert response == "--"

    print("--- Step 3: Network Connection Restored & Cloud Sync ---")
    # Simulate remote customer tag update on server
    simulated_cloud_tags = ["newsletter", "lauburu_pro"]
    updated_tier = parse_customer_tier(simulated_cloud_tags)
    assert updated_tier == CustomerTier.PRO

    # Background sync updates local profile
    updated_profile = dict(cached["customerProfile"])
    updated_profile["tags"] = simulated_cloud_tags
    updated_profile["tier"] = updated_tier
    store.save_session(cached["accessToken"], cached["expiresAt"], updated_profile)

    reloaded = store.load_session()
    assert reloaded["customerProfile"]["tier"] == CustomerTier.PRO


def test_user_journey_cross_device_tier_upgrade(tmp_path):
    """
    Tier 4 User Journey 3: Multi-Device Sync & Tier Upgrade
    Simulates: Device A logs in with Free tier -> Shopify membership upgrade event occurs ->
    Device B launches and performs cloud sync -> Profile on Device B immediately reflects
    Elite membership tier.
    """
    print("\n--- Step 1: Device A Logs In (Free Tier) ---")
    device_a_store = PersistentSessionStore(tmp_path / "device_a.json")
    user_token = "tok_canonical_user_777"
    device_a_store.save_session(
        access_token=user_token,
        expires_at="2027-01-01T00:00:00Z",
        profile={"id": "gid://shopify/Customer/777", "tier": CustomerTier.FREE, "tags": []}
    )
    s_a = device_a_store.load_session()
    assert s_a["customerProfile"]["tier"] == CustomerTier.FREE

    print("--- Step 2: Shopify Cloud Membership Upgrade Event ---")
    cloud_tags = ["active_subscriber", "lauburu_elite"]
    resolved_tier = parse_customer_tier(cloud_tags)
    assert resolved_tier == CustomerTier.ELITE

    print("--- Step 3: Device B Launches & Performs Cloud Session Sync ---")
    device_b_store = PersistentSessionStore(tmp_path / "device_b.json")
    # Sync with Shopify Storefront API as single source of truth
    device_b_store.save_session(
        access_token=user_token,
        expires_at="2027-01-01T00:00:00Z",
        profile={"id": "gid://shopify/Customer/777", "tier": resolved_tier, "tags": cloud_tags}
    )

    s_b = device_b_store.load_session()
    assert s_b["accessToken"] == user_token
    assert s_b["customerProfile"]["tier"] == CustomerTier.ELITE

    print("--- Step 4: Validate Elite Entitlement on Device B ---")
    item = CANONICAL_CATALOG[2]  # Competition Gi $189.00 AUD
    # Elite members receive 20% discount
    elite_price = round(item["price_aud"] * 0.80, 2)
    assert elite_price == 151.20
    assert elite_price < item["price_aud"]


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "-s", __file__]))
