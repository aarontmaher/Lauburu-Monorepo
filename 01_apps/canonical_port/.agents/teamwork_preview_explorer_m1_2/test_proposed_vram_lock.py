"""
Unit Test Suite for Proposed DevilsLockGovernor and check_vram_and_lock()
Verifies boundary conditions at 14.9%, 15.0%, 15.1%, live hardware metrics, and fail-closed security.
"""

import os
import sys
import pytest
import tempfile

# Add proposed module to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from proposed_devils_lock_governor import (
    DevilsLockGovernor,
    DevilsLockError,
    ResourceCapExceededError,
    VRAMLockBlockedError,
    VRAMTelemetryError,
    GeneticLeaderboardError,
)


@pytest.fixture
def governor():
    """Fixture providing a fresh DevilsLockGovernor instance with temp lock file."""
    with tempfile.NamedTemporaryFile(suffix=".lock", delete=False) as f:
        lock_path = f.name
    # Remove file so governor sees no lock initially
    if os.path.exists(lock_path):
        os.remove(lock_path)
    
    gov = DevilsLockGovernor(lock_file_path=lock_path, min_vram_pct=15.0)
    yield gov
    
    # Cleanup
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except OSError:
            pass


# =============================================================================
# 1. BOUNDARY VALUE TESTS (14.9%, 15.0%, 15.1%)
# =============================================================================

def test_vram_boundary_under_threshold(governor):
    """At 14.9% free VRAM (< 15.0%), check_vram_and_lock must return is_allowed=False."""
    is_allowed, free_gb, free_pct = governor.check_vram_and_lock(override_free_pct=14.9)
    assert is_allowed is False, f"Expected is_allowed=False for 14.9%, got {is_allowed}"
    assert free_pct == 14.9
    assert free_gb > 0.0
    assert isinstance(is_allowed, bool)
    assert isinstance(free_gb, float)
    assert isinstance(free_pct, float)


def test_vram_boundary_exact_threshold(governor):
    """At 15.0% free VRAM (== 15.0%), check_vram_and_lock must return is_allowed=True."""
    is_allowed, free_gb, free_pct = governor.check_vram_and_lock(override_free_pct=15.0)
    assert is_allowed is True, f"Expected is_allowed=True for 15.0%, got {is_allowed}"
    assert free_pct == 15.0
    assert free_gb > 0.0


def test_vram_boundary_above_threshold(governor):
    """At 15.1% free VRAM (> 15.0%), check_vram_and_lock must return is_allowed=True."""
    is_allowed, free_gb, free_pct = governor.check_vram_and_lock(override_free_pct=15.1)
    assert is_allowed is True, f"Expected is_allowed=True for 15.1%, got {is_allowed}"
    assert free_pct == 15.1
    assert free_gb > 0.0


def test_vram_sub_decimal_precision(governor):
    """Test fine decimal boundaries at 14.99% and 15.01%."""
    # 14.99% is below 15.0% -> Blocked
    is_allowed_under, _, pct_under = governor.check_vram_and_lock(override_free_pct=14.99)
    assert is_allowed_under is False
    assert pct_under == 14.99

    # 15.01% is above 15.0% -> Allowed
    is_allowed_over, _, pct_over = governor.check_vram_and_lock(override_free_pct=15.01)
    assert is_allowed_over is True
    assert pct_over == 15.01


def test_vram_extreme_boundaries(governor):
    """Test extreme VRAM percentages: 0.0%, 100.0%, negative, and over 100%."""
    # 0.0% -> Blocked
    allowed, gb, pct = governor.check_vram_and_lock(override_free_pct=0.0)
    assert allowed is False
    assert pct == 0.0
    assert gb == 0.0

    # 100.0% -> Allowed
    allowed, gb, pct = governor.check_vram_and_lock(override_free_pct=100.0)
    assert allowed is True
    assert pct == 100.0
    assert gb > 0.0

    # Negative -> Blocked
    allowed, gb, pct = governor.check_vram_and_lock(override_free_pct=-5.0)
    assert allowed is False


# =============================================================================
# 2. LIVE HARDWARE & BLACKBOARD INSPECTION (Rule #0 Zero-Mock)
# =============================================================================

def test_vram_live_hardware_inspection(governor):
    """Inspect genuine live hardware metrics without any override."""
    is_allowed, free_gb, free_pct = governor.check_vram_and_lock(override_free_pct=None)
    
    assert isinstance(is_allowed, bool)
    assert isinstance(free_gb, float)
    assert isinstance(free_pct, float)
    
    # Invariant: 0.0 <= free_pct <= 100.0
    assert 0.0 <= free_pct <= 100.0
    assert free_gb >= 0.0
    
    # Invariant: is_allowed strictly equals free_pct >= 15.0
    expected_allowed = free_pct >= 15.0
    assert is_allowed == expected_allowed, f"is_allowed={is_allowed} must match free_pct >= 15.0 (got {free_pct}%)"


def test_get_vram_telemetry_schema(governor):
    """Verify get_vram_telemetry() returns structured dictionary."""
    telemetry = governor.get_vram_telemetry(override_free_pct=14.9)
    assert isinstance(telemetry, dict)
    assert telemetry["is_allowed"] is False
    assert telemetry["free_pct"] == 14.9
    assert telemetry["min_required_pct"] == 15.0
    assert telemetry["is_locked"] is True
    assert "free_vram_gb" in telemetry
    assert "timestamp" in telemetry


# =============================================================================
# 3. PREFLIGHT LOCKS VALIDATION & EXCEPTION RAISING
# =============================================================================

def test_validate_preflight_locks_blocked_on_vram(governor):
    """validate_preflight_locks must raise VRAMLockBlockedError when free VRAM < 15%."""
    with pytest.raises(VRAMLockBlockedError) as exc_info:
        governor.validate_preflight_locks(override_free_pct=14.9)
    assert "14.9" in str(exc_info.value)
    assert "below mandatory 15.0%" in str(exc_info.value)


def test_validate_preflight_locks_approved(governor):
    """validate_preflight_locks returns APPROVED when all gates pass."""
    result = governor.validate_preflight_locks(override_free_pct=25.0)
    assert result["status"] == "APPROVED"
    assert result["resource_cap_ok"] is True
    assert result["vram_lock_ok"] is True
    assert result["free_vram_pct"] == 25.0
    assert "selected_model" in result
    assert result["selected_model"]["model_id"] is not None


# =============================================================================
# 4. RESOURCE CAP & CONCURRENCY
# =============================================================================

def test_resource_cap_lifecycle(governor):
    """Test acquiring and releasing subagent lock."""
    # Initially allowed
    assert governor.check_resource_cap() is True

    # Acquire lock
    acquired = governor.acquire_subagent_lock("task_test_001", {"name": "Test UI Restructure"})
    assert acquired is True
    assert governor.check_resource_cap() is False

    # Second acquire should fail (cap = 1)
    acquired_second = governor.acquire_subagent_lock("task_test_002")
    assert acquired_second is False

    # validate_preflight_locks should raise ResourceCapExceededError
    with pytest.raises(ResourceCapExceededError):
        governor.validate_preflight_locks(override_free_pct=25.0)

    # Release lock
    released = governor.release_subagent_lock()
    assert released is True
    assert governor.check_resource_cap() is True


# =============================================================================
# 5. GENETIC ELO LEADERBOARD SELECTION
# =============================================================================

def test_genetic_elo_model_selection(governor):
    """Test reading canonical_ai_leaderboard.json and ranking by domain UI ELO."""
    top_model = governor.select_highest_elo_model_for_ui()
    assert isinstance(top_model, dict)
    assert "model_id" in top_model
    assert "ui_domain_elo" in top_model
    assert top_model["ui_domain_elo"] > 0
    assert "engine" in top_model
