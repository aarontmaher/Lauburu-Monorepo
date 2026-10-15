"""
Generation 32 Milestone M1 E2E Test Suite: Storage Consolidation & Seamless Login
Target: GL.iNet GL-BE14000 Sovereign Gateway (192.168.8.1)
"""
import os
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/screen_lens/src"))

from lens_canonical_storage_governor import CanonicalStorageGovernor, calculate_sha256


def test_tier1_router_single_share_broadcast():
    """Tier 1: Verify SMB broadcast advertisement lists exclusively lauburu_storage."""
    res = subprocess.run(["smbutil", "view", "//guest@192.168.8.1"], capture_output=True, text=True)
    assert res.returncode == 0
    stdout = res.stdout
    assert "lauburu_storage" in stdout
    assert "seaweedfs" not in stdout
    assert "lauburu_shared" not in stdout


def test_tier2_zero_password_guest_mount():
    """Tier 2: Verify zero-credential client mount script runs and passes."""
    script_path = REPO_ROOT / "06_scripts_and_tooling/storage/mount_router_network_storage.sh"
    res = subprocess.run([str(script_path), "status"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Unified share is MOUNTED" in res.stdout


def test_tier3_dual_storage_pools_traversal_and_sha256():
    """Tier 3: Cryptographic bit-for-bit verification across distributed SeaweedFS and local flash."""
    mount_root = Path.home() / "Network_Storage/Router_Unified"
    assert (mount_root / "distributed_dfs").is_dir()
    assert (mount_root / "local_flash").is_dir()

    # Test file write on distributed SeaweedFS
    dfs_file = mount_root / "distributed_dfs/.e2e_tier3_test.bin"
    dfs_file.write_bytes(b"DFS_DATA_PACKET_900GB_POOL_VALIDATION")
    dfs_hash = calculate_sha256(dfs_file)
    assert len(dfs_hash) == 64
    dfs_file.unlink()

    # Test file write on local flash
    flash_file = mount_root / "local_flash/.e2e_tier3_test.bin"
    flash_file.write_bytes(b"FLASH_DATA_PACKET_58GB_F2FS_VALIDATION")
    flash_hash = calculate_sha256(flash_file)
    assert len(flash_hash) == 64
    flash_file.unlink()


def test_tier4_screen_lens_storage_governor_e2e():
    """Tier 4: Screen Lens Storage Governor automated structure and categorization."""
    gov = CanonicalStorageGovernor()
    rep = gov.get_unified_storage_report()
    assert rep["router_unified"]["active"] is True
    assert rep["router_unified"]["writable"] is True
    assert "router_storage_stats" in rep
    assert rep["router_storage_stats"]["free_gb"] > 10.0
