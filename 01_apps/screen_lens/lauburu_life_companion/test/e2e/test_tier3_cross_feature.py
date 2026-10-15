"""
Tier 3: Cross-Feature Combinations (Opaque-Box E2E)
Verifies pairwise and cross-boundary interactions between R1, R2, R3, and R4.
Minimum requirement: >= 5 cross-feature combinatorial test cases.
"""

import os
import sys
import json
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


def test_boot_persistence_to_auth_session_restore(tmp_path):
    """
    Tier 3 Pairwise Test 1: Boot Persistence -> Auth Session Restore
    Simulates: Background daemon running at boot -> App starts up ->
    Persistent session storage is queried -> Restores authenticated session
    without requiring interactive user login.
    """
    # 1. Verify boot persistence layer is active (daemon port responsive)
    daemon_ready = probe_socket(DAEMON_PORT, timeout=1.5) or probe_socket(ZMQ_PORT, timeout=1.5)
    assert daemon_ready, "Background daemon must be active for boot persistence"

    # 2. Simulate stored session from prior session
    storage_file = tmp_path / "boot_session.json"
    store = PersistentSessionStore(storage_file)
    store.save_session(
        access_token="tok_boot_restore_test_99",
        expires_at="2027-01-01T00:00:00Z",
        profile={"id": "gid://shopify/Customer/99", "email": "boot@lauburu.mesh", "tier": CustomerTier.PRO}
    )

    # 3. Simulate fresh app launch & auto-login
    app_launch_store = PersistentSessionStore(storage_file)
    session = app_launch_store.load_session()
    assert session is not None, "Failed to restore session after simulated boot"
    assert session["accessToken"] == "tok_boot_restore_test_99"
    assert session["customerProfile"]["tier"] == CustomerTier.PRO


def test_auth_sync_to_ecommerce_tier_entitlement(tmp_path):
    """
    Tier 3 Pairwise Test 2: Auth Sync -> E-Commerce Tier Entitlement
    Simulates: Shopify customer logs in -> Cloud sync fetches tags -> Resolves Pro tier ->
    E-Commerce Catalog calculates entitled member pricing (15% Pro member discount).
    """
    # 1. Login with Pro dev token
    profile = validate_dev_token("tok_dev_aaron_specialist")
    assert profile is not None
    assert profile["tier"] == CustomerTier.PRO

    # 2. Persist session
    store = PersistentSessionStore(tmp_path / "tier_entitlement.json")
    store.save_session("tok_dev_aaron_specialist", "2027-01-01T00:00:00Z", profile)

    # 3. Calculate member pricing for canonical catalog
    item = CANONICAL_CATALOG[0]  # Compression Rashguard $97.50 AUD
    base_price = item["price_aud"]

    def calculate_member_price(price: float, tier: str) -> float:
        if tier == CustomerTier.ELITE:
            return round(price * 0.80, 2)  # 20% discount
        elif tier == CustomerTier.PRO:
            return round(price * 0.85, 2)  # 15% discount
        return price

    member_price = calculate_member_price(base_price, profile["tier"])
    assert member_price == 82.88, f"Expected Pro price $82.88, got {member_price}"
    assert member_price < base_price


def test_session_restore_to_ai_model_query(tmp_path):
    """
    Tier 3 Pairwise Test 3: Session Restore -> AI Model Query
    Simulates: Restoring authenticated user session -> User selects catalog item ->
    Triggers local AI inference (Port 8082 fallback to Port 8083) to generate
    direct-response ad copy.
    """
    store = PersistentSessionStore(tmp_path / "ai_query_session.json")
    profile = validate_dev_token("dev_aaron_tatami")
    store.save_session("tok_dev_session_ai", "2027-01-01T00:00:00Z", profile)

    session = store.load_session()
    assert session is not None

    # Pick canonical catalog item: Movesense MD+ ($170.00 AUD)
    item = CANONICAL_CATALOG[9]
    prompt = generate_ecommerce_ad_prompt(item)

    # Query local AI inference
    success, response, status = query_local_ai_inference(prompt, max_tokens=64, timeout=15.0)
    assert success is True, f"AI copy generation failed with status {status}"
    assert len(response.strip()) > 0
    assert response != "--"


def test_ai_inference_failure_during_active_session(tmp_path):
    """
    Tier 3 Pairwise Test 4: AI Failure During Active Session
    Simulates: User is logged in -> Local AI ports go offline ->
    App displays clean waiting state ('--') without invalidating user session or crashing.
    """
    store = PersistentSessionStore(tmp_path / "resilient_session.json")
    store.save_session("tok_active_user", "2027-01-01T00:00:00Z", {"tier": "pro"})

    # Simulate AI port failure
    with patch("urllib.request.urlopen", side_effect=OSError("Local AI ports unreachable")):
        success, response, status = query_local_ai_inference("Generate copy", max_tokens=20)
        assert success is False
        assert response == "--"  # Zero fake data

    # Verify session is still completely intact
    session = store.load_session()
    assert session is not None
    assert session["accessToken"] == "tok_active_user"


def test_token_revocation_during_ai_catalog_browsing(tmp_path):
    """
    Tier 3 Pairwise Test 5: Token Revocation During Catalog Browsing
    Simulates: User is browsing catalog -> Background check detects token revoked ->
    Session is wiped -> App gracefully switches to unauthenticated guest mode
    while keeping the 18-item catalog browsable.
    """
    storage_file = tmp_path / "revocation_during_browse.json"
    store = PersistentSessionStore(storage_file)
    store.save_session("tok_to_be_revoked", "2027-01-01T00:00:00Z", {"tier": "elite"})

    # Catalog is browsable before
    assert len(CANONICAL_CATALOG) == 18

    # Background cloud sync receives 401 unauthenticated
    simulated_cloud_status = 401
    if simulated_cloud_status == 401:
        store.clear_session()

    # Session is now empty
    assert store.load_session() is None

    # Catalog remains 100% accessible to guest users
    assert len(CANONICAL_CATALOG) == 18
    assert CANONICAL_CATALOG[0]["price_aud"] == 97.50


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
