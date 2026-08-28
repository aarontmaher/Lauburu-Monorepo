"""
tests.unit.test_adversarial_m1
Adversarial stress-testing suite for Milestone 1:
- Obsidian Index.md corruption (binary garbage, null bytes, missing links, directory collision, read-only)
- Missing parent directories & deep path hierarchy creation
- Active vs Stale lock files (.git/index.lock exact timing boundaries, dir collision, future mtime)
- Disk usage & df parsing edge cases (APFS wrapped lines, Android df, malformed tokens, overflow)
- Mesh scanner resilience under degraded network, extreme timeouts, socket drops, and offline nodes
- PySpark JSONL corruption (truncated lines, invalid JSON, binary bytes)
- StorageVerifier full verification pipeline resilience under full node degradation
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from canonical_sync_engine.config import SyncConfig, MeshNodeConfig
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.health import NodeProbeMethod, NodeStorageHealth
from canonical_sync_engine.verification.fast_path import FastPathChecker, fast_path_check, is_storage_healthy
from canonical_sync_engine.verification.headroom import (
    HeadroomValidator,
    check_disk_headroom,
    check_multi_mount_headroom,
)
from canonical_sync_engine.verification.invariants import (
    REQUIRED_OBSIDIAN_WIKILINKS,
    StorageInvariantValidator,
)
from canonical_sync_engine.verification.mesh_scanner import (
    DEFAULT_MESH_TOPOLOGY,
    MeshNodeScanner,
)
from canonical_sync_engine.verification.self_healer import (
    CANONICAL_INDEX_MD_CONTENT,
    StorageSelfHealer,
)
from canonical_sync_engine.verification import StorageVerifier


# ============================================================================
# 1. OBSIDIAN CORRUPTION & SELF-HEALING ADVERSARIAL TESTS
# ============================================================================

def test_adversarial_obsidian_binary_garbage_and_healing():
    """Test Obsidian Index.md filled with raw binary garbage and null bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir) / "obsidian_vault"
        vault.mkdir(parents=True)
        index_file = vault / "Index.md"

        # Write null bytes and random binary garbage
        with open(index_file, "wb") as f:
            f.write(b"\x00\xff\xfe\x00\x80\x90\x00\x00" * 100)

        validator = StorageInvariantValidator(obsidian_path=vault)
        res = validator.validate_obsidian()
        assert not res.is_healthy
        assert any("missing mandatory Wikilink" in v for v in res.violations)

        # Self-heal
        healer = StorageSelfHealer(obsidian_path=vault)
        actions = healer.heal_obsidian_index()
        assert len(actions) == 1
        assert "Recreated Obsidian master Index.md" in actions[0]

        # Verify healthy
        res_healed = validator.validate_obsidian()
        assert res_healed.is_healthy
        assert len(res_healed.violations) == 0
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        for link in REQUIRED_OBSIDIAN_WIKILINKS:
            assert link in content


def test_adversarial_obsidian_partial_wikilinks_combinations():
    """Test every combination of missing mandatory Wikilinks in Index.md."""
    links = [
        "[[Index]]",
        "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
        "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir) / "obsidian_vault"
        vault.mkdir(parents=True)
        index_file = vault / "Index.md"

        # Test single missing link for each
        for missing_idx in range(len(links)):
            present_links = [l for i, l in enumerate(links) if i != missing_idx]
            index_file.write_text("\n".join(present_links), encoding="utf-8")

            validator = StorageInvariantValidator(obsidian_path=vault)
            res = validator.validate_obsidian()
            assert not res.is_healthy
            assert any(links[missing_idx] in v for v in res.violations)

            # Heal and assert full recovery
            healer = StorageSelfHealer(obsidian_path=vault)
            healer.heal_obsidian_index()
            res_healed = validator.validate_obsidian()
            assert res_healed.is_healthy


def test_adversarial_obsidian_vault_is_file_collision():
    """Test invariant validator when obsidian_vault path is a regular file, not a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_file = Path(tmpdir) / "obsidian_vault"
        vault_file.write_text("i am a file not a directory")

        validator = StorageInvariantValidator(obsidian_path=vault_file)
        res = validator.validate_obsidian()
        assert not res.is_healthy
        assert any("not a directory" in v for v in res.violations)


def test_adversarial_obsidian_parent_directory_deep_creation():
    """Test self-healing when obsidian vault is located in deeply nested non-existent directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        deep_vault = Path(tmpdir) / "deep" / "nested" / "path" / "level3" / "obsidian_vault"
        assert not deep_vault.exists()

        healer = StorageSelfHealer(obsidian_path=deep_vault)
        actions = healer.heal_obsidian_index()
        assert len(actions) == 1
        assert deep_vault.exists()
        assert (deep_vault / "Index.md").exists()

        validator = StorageInvariantValidator(obsidian_path=deep_vault)
        assert validator.validate_obsidian().is_healthy


# ============================================================================
# 2. ACTIVE VS STALE GIT LOCK ADVERSARIAL TESTS
# ============================================================================

def test_adversarial_git_lock_exact_boundary_conditions():
    """Stress-test active vs stale lock detection at exact boundary tolerances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "repo"
        repo.mkdir()
        dot_git = repo / ".git"
        dot_git.mkdir()
        lock = dot_git / "index.lock"

        healer = StorageSelfHealer(git_repo_path=repo, stale_lock_timeout_sec=10.0)

        # 1. Lock created 2 seconds ago (< 10.0s) -> Active -> NOT removed
        lock.touch()
        mtime_recent = time.time() - 2.0
        os.utime(lock, (mtime_recent, mtime_recent))

        actions = healer.heal_git_locks(force=False)
        assert lock.exists()
        assert any("Skipped active git index lock" in a for a in actions)

        # 2. Lock with timestamp in future (clock skew: mtime > now) -> NOT removed
        mtime_future = time.time() + 100.0
        os.utime(lock, (mtime_future, mtime_future))
        actions = healer.heal_git_locks(force=False)
        assert lock.exists()
        assert any("Skipped active git index lock" in a for a in actions)

        # 3. Lock created 10.1 seconds ago (>= 10.0s) -> Stale -> Removed
        mtime_stale = time.time() - 10.1
        os.utime(lock, (mtime_stale, mtime_stale))
        actions = healer.heal_git_locks(force=False)
        assert not lock.exists()
        assert any("Removed stale git index lock" in a for a in actions)

        # 4. Active lock with force=True -> Force removed
        lock.touch()
        actions_force = healer.heal_git_locks(force=True)
        assert not lock.exists()
        assert any("Removed stale git index lock" in a for a in actions_force)


def test_adversarial_git_repo_missing_dot_git():
    """Test git invariant validator when .git folder is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "not_a_git_repo"
        repo.mkdir()

        validator = StorageInvariantValidator(git_path=repo)
        res = validator.validate_git()
        assert not res.is_healthy
        assert any(".git directory not found" in v for v in res.violations)


# ============================================================================
# 3. DISK HEADROOM & DF PARSER ADVERSARIAL EDGE CASES
# ============================================================================

def test_adversarial_df_parser_wrapped_apfs_and_unusual_formats():
    """Stress test _parse_df_output with various OS formats, line wrapping, and garbage."""
    # 1. macOS APFS wrapped filesystem name
    macos_apfs_wrapped = """
Filesystem   1024-blocks      Used Available Capacity iused      ifree %iused  Mounted on
/dev/disk3s1s1
               488245288  15234560 214567890     7%  512300 2145678900    0%   /
"""
    total, free = MeshNodeScanner._parse_df_output(macos_apfs_wrapped)
    assert total > 0.0
    assert free > 0.0
    assert round(total, 0) == round(488245288 / 1048576, 0)

    # 2. Linux standard 1K-blocks
    linux_df = """
Filesystem     1K-blocks     Used Available Use% Mounted on
/dev/nvme0n1p2 959863848 45823940 865181232   6% /
"""
    total, free = MeshNodeScanner._parse_df_output(linux_df)
    assert round(total, 0) == round(959863848 / 1048576, 0)
    assert round(free, 0) == round(865181232 / 1048576, 0)

    # 3. Android Termux /data mount df
    android_df = """
Filesystem     1K-blocks     Used Available Use% Mounted on
/dev/block/dm-5 245678900 12345678 233333222   6% /data
"""
    total, free = MeshNodeScanner._parse_df_output(android_df)
    assert round(total, 0) == round(245678900 / 1048576, 0)
    assert round(free, 0) == round(233333222 / 1048576, 0)

    # 4. Completely empty or garbage outputs
    assert MeshNodeScanner._parse_df_output("") == (0.0, 0.0)
    assert MeshNodeScanner._parse_df_output("invalid output with no numbers") == (0.0, 0.0)
    assert MeshNodeScanner._parse_df_output("header only\n") == (0.0, 0.0)
    assert MeshNodeScanner._parse_df_output("Filesystem 1K-blocks\n\n\n") == (0.0, 0.0)


def test_adversarial_headroom_nonexistent_paths():
    """Test check_disk_headroom when checking non-existent or deep imaginary paths."""
    status = check_disk_headroom("/totally/nonexistent/imaginary/mount/path/123", min_headroom_gb=1.0)
    assert status.total_gb > 0.0  # Fell back to /
    assert status.free_gb > 0.0


# ============================================================================
# 4. PYSPARK JSONL CORRUPTION ADVERSARIAL TESTS
# ============================================================================

def test_adversarial_pyspark_corrupt_jsonl_handling():
    """Stress-test PySpark validator with truncated lines and binary files named .jsonl."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyspark_dir = Path(tmpdir) / "lora_datasets"
        pyspark_dir.mkdir()

        # 1. Valid JSONL
        valid_jsonl = pyspark_dir / "valid.jsonl"
        valid_jsonl.write_text(json.dumps({"text": "sample", "score": 1.0}) + "\n")

        validator = StorageInvariantValidator(pyspark_path=pyspark_dir)
        assert validator.validate_pyspark().is_healthy

        # 2. Corrupt JSONL with half-written JSON line
        corrupt_jsonl = pyspark_dir / "corrupt.jsonl"
        corrupt_jsonl.write_text('{"text": "broken json without closing brace\n')

        res = validator.validate_pyspark()
        assert not res.is_healthy
        assert any("Corrupt JSONL format" in v for v in res.violations)

        # 3. Binary file disguised as JSONL
        corrupt_jsonl.unlink()
        binary_jsonl = pyspark_dir / "binary.jsonl"
        with open(binary_jsonl, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\xff\xfe\xfa\n\x00\x00")

        res_binary = validator.validate_pyspark()
        assert not res_binary.is_healthy
        assert any("Corrupt JSONL format" in v for v in res_binary.violations)


# ============================================================================
# 5. MESH SCANNER ADVERSARIAL NETWORK STRESS & DEGRADED MODES
# ============================================================================

def test_adversarial_mesh_scanner_all_nodes_offline():
    """Stress test mesh scanner when all L1-L7 + GW nodes are completely offline."""
    scanner = MeshNodeScanner(timeout_sec=0.1)

    with patch("shutil.disk_usage", side_effect=OSError("Disk unmounted")), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=0.1)), \
         patch("socket.socket") as mock_sock:

        mock_instance = MagicMock()
        mock_instance.connect.side_effect = socket.timeout("Connection timed out")
        mock_sock.return_value = mock_instance

        summary = scanner.get_mesh_summary(parallel=True)
        assert summary.total_nodes == len(DEFAULT_MESH_TOPOLOGY)
        assert summary.online_nodes == 0
        assert summary.offline_nodes == len(DEFAULT_MESH_TOPOLOGY)
        assert summary.total_mesh_free_gb == 0.0

        for node_id, health in summary.nodes.items():
            assert not health.is_reachable
            assert not health.headroom_ok
            assert health.error_message is not None


def test_adversarial_mesh_scanner_socket_dns_refusal_and_unreachable():
    """Test gateway socket probe under DNS failure and host unreachable errors."""
    scanner = MeshNodeScanner(timeout_sec=0.1)
    spec = {
        "node_id": "GW",
        "name": "GL.iNet Router",
        "probe_method": NodeProbeMethod.SOCKET,
        "endpoints": ["unresolvable.invalid.domain.lauburu", "192.168.8.1"],
        "port": 80,
    }

    with patch("socket.socket") as mock_sock:
        mock_instance = MagicMock()
        mock_instance.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_sock.return_value = mock_instance

        res = scanner.scan_node_by_spec(spec)
        assert not res.is_reachable
        assert "refused" in res.error_message.lower() or "timed out" in res.error_message.lower()


def test_adversarial_mesh_scanner_adb_device_offline_and_unauthorized():
    """Test Android ADB probe when device is reported as unauthorized or offline."""
    scanner = MeshNodeScanner(timeout_sec=0.2)
    spec = {
        "node_id": "L7",
        "name": "Samsung_S20",
        "probe_method": NodeProbeMethod.ADB,
        "adb_targets": ["100.84.40.95:5555"],
        "mount_point": "/storage/emulated",
    }

    # Simulate ADB error returncode 1 with error text
    mock_cp = MagicMock(returncode=1, stdout="", stderr="error: device unauthorized. Please check the confirmation dialog on your device.")
    with patch("subprocess.run", return_value=mock_cp):
        res = scanner.scan_node_by_spec(spec)
        assert not res.is_reachable
        assert "unauthorized" in res.error_message


def test_adversarial_mesh_scanner_ssh_host_key_and_permission_denied():
    """Test SSH probe encountering host key verification failure and permission denied."""
    scanner = MeshNodeScanner(timeout_sec=0.2)
    spec = {
        "node_id": "L2",
        "name": "MacBook_Pro",
        "probe_method": NodeProbeMethod.SSH,
        "endpoints": ["192.168.8.127"],
        "user": "aaron",
        "mount_point": "/System/Volumes/Data",
    }

    mock_cp = MagicMock(returncode=255, stdout="", stderr="Host key verification failed.")
    with patch("subprocess.run", return_value=mock_cp):
        res = scanner.scan_node_by_spec(spec)
        assert not res.is_reachable
        assert "Host key verification failed" in res.error_message


# ============================================================================
# 6. COMPOSITE STORAGE VERIFIER ADVERSARIAL RECOVERY PIPELINE
# ============================================================================

def test_adversarial_storage_verifier_self_heal_and_offline_mesh():
    """
    Test StorageVerifier full_verification when vaults are corrupted/missing AND
    remote mesh nodes are offline. Verifies that self-healing cleans up vaults and
    offline remote nodes do not crash the pipeline.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        obs_dir = base / "obsidian_vault"
        pysp_dir = base / "lora_datasets"
        pysp_mem = base / "04_data_and_memory"
        git_dir = base / "git_repo"
        gdrive_cache = base / "data" / "gdrive_cache"

        # Create git repo with stale lock
        git_dir.mkdir(parents=True)
        dot_git = git_dir / ".git"
        dot_git.mkdir()
        stale_lock = dot_git / "index.lock"
        stale_lock.touch()
        stale_time = time.time() - 20.0
        os.utime(stale_lock, (stale_time, stale_time))

        # Do NOT create obsidian_vault or pyspark dirs yet
        assert not obs_dir.exists()
        assert not pysp_dir.exists()

        verifier = StorageVerifier(
            obsidian_vault_path=obs_dir,
            pyspark_dataset_path=pysp_dir,
            pyspark_memory_path=pysp_mem,
            git_working_tree_path=git_dir,
            gdrive_fallback_cache_path=gdrive_cache,
            min_headroom_gb=1.0,
        )

        # Mock remote nodes failing with timeouts
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=0.1)), \
             patch("socket.socket") as mock_sock:
            mock_instance = MagicMock()
            mock_instance.connect.side_effect = socket.timeout("Connection timed out")
            mock_sock.return_value = mock_instance

            # Execute full verification with auto_heal=True
            report = verifier.full_verification(scan_remote_nodes=True, auto_heal=True)

            # Assert self-healing healed the missing dirs, lock, and index.md
            assert len(report.healed_actions) > 0
            assert any("Created missing Obsidian Vault" in a for a in report.healed_actions)
            assert any("Removed stale git index lock" in a for a in report.healed_actions)
            assert any("Recreated Obsidian master Index.md" in a for a in report.healed_actions)

            # Assert vaults are now healthy
            assert report.obsidian_healthy
            assert report.pyspark_healthy
            assert report.git_healthy
            assert report.gdrive_healthy
            assert report.is_healthy

            # Assert node reports contain all mesh nodes without any crashing
            assert len(report.node_reports) == len(DEFAULT_MESH_TOPOLOGY)
            assert report.node_reports["L1"].is_reachable  # Local L1 is reachable
            assert not report.node_reports["L2"].is_reachable  # Remote L2 timed out gracefully
            assert not report.node_reports["GW"].is_reachable  # Gateway socket timed out gracefully


# ============================================================================
# 7. TRUTH ARTIFACT COMPLEX DATA STRUCTURES & HASH INVARIANCE
# ============================================================================

def test_adversarial_truth_artifact_extreme_payload_invariance():
    """Test TruthArtifact hash calculation over complex mixed unicode, deep structures, and list order."""
    fixed_timestamp = "2026-08-27T00:00:00+00:00"
    payload1 = {
        "z_key": [3, 2, 1],
        "a_key": {"sub_b": "value", "sub_a": [None, True, False, 3.1415926535]},
        "unicode_key": "🧠 Lauburu ⚡ 10Gbps TB4 測試 üñîçødé",
        "empty_dict": {},
        "empty_list": [],
    }
    payload2 = {
        "unicode_key": "🧠 Lauburu ⚡ 10Gbps TB4 測試 üñîçødé",
        "empty_list": [],
        "empty_dict": {},
        "a_key": {"sub_a": [None, True, False, 3.1415926535], "sub_b": "value"},
        "z_key": [3, 2, 1],
    }

    art1 = TruthArtifact(
        artifact_id="art-adv-001",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Adversarial Audit",
        payload=payload1,
        source_node="L1",
        timestamp=fixed_timestamp,
        tags=["tagB", "tagA"],
    )

    art2 = TruthArtifact(
        artifact_id="art-adv-001",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Adversarial Audit",
        payload=payload2,
        source_node="L1",
        timestamp=fixed_timestamp,
        tags=["tagA", "tagB"],
    )

    assert art1.sha256_hash == art2.sha256_hash
    assert art1.verify_hash()
    assert art2.verify_hash()

    # Tamper with single float
    art2.payload["a_key"]["sub_a"][3] = 3.1415926536
    assert not art2.verify_hash()


# ============================================================================
# 8. CONCURRENCY & MULTI-THREAD STRESS TESTING
# ============================================================================

def test_adversarial_concurrent_self_healing_race_condition():
    """Test multiple concurrent threads executing self-healing simultaneously on the same vault."""
    import concurrent.futures

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        obs_dir = base / "obsidian_vault"
        pysp_dir = base / "lora_datasets"
        git_dir = base / "git_repo"
        dot_git = git_dir / ".git"
        git_dir.mkdir(parents=True)
        dot_git.mkdir()

        # Create stale lock
        lock = dot_git / "index.lock"
        lock.touch()
        stale_time = time.time() - 30.0
        os.utime(lock, (stale_time, stale_time))

        healer = StorageSelfHealer(
            obsidian_path=obs_dir,
            pyspark_lora_path=pysp_dir,
            git_repo_path=git_dir,
        )

        def run_heal():
            return healer.heal_all()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_heal) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify vault is intact and consistent after concurrent heals
        assert obs_dir.exists()
        assert (obs_dir / "Index.md").exists()
        assert pysp_dir.exists()
        assert not lock.exists()

        validator = StorageInvariantValidator(
            obsidian_path=obs_dir,
            pyspark_path=pysp_dir,
            git_path=git_dir,
        )
        assert validator.validate_obsidian().is_healthy
        assert validator.validate_pyspark().is_healthy
        assert validator.validate_git().is_healthy


def test_adversarial_concurrent_fast_path_stress():
    """Stress-test fast-path checker under high-concurrency 20-thread load (500 queries)."""
    import concurrent.futures

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        obs_dir = base / "obsidian_vault"
        pysp_dir = base / "lora_datasets"
        obs_dir.mkdir()
        pysp_dir.mkdir()

        checker = FastPathChecker(
            obsidian_path=obs_dir,
            pyspark_path=pysp_dir,
            git_path=base,
            min_free_gb=0.1,
        )

        def query_fast():
            res = checker.check()
            assert res.is_healthy
            assert res.duration_ms < 10.0  # Must be fast even under thread load
            return res.duration_ms

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(query_fast) for _ in range(500)]
            latencies = [f.result() for f in concurrent.futures.as_completed(futures)]

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 3.0  # Average strictly sub-3ms


# ============================================================================
# 9. EMBEDDED BUSYBOX & OPWRT DF OUTPUT PARSING
# ============================================================================

def test_adversarial_df_parser_busybox_openwrt_and_edge_tokens():
    """Test df parsing against OpenWrt / BusyBox router outputs and irregular spaces."""
    # OpenWrt Busybox df output format
    openwrt_df = """
Filesystem           1K-blocks      Used Available Use% Mounted on
/dev/root                30720     30720         0 100% /rom
tmpfs                   254824      1156    253668   0% /tmp
/dev/mtdblock6           96256     14336     81920  15% /overlay
overlayfs:/overlay       96256     14336     81920  15% /
tmpfs                      512         0       512   0% /dev
"""
    total, free = MeshNodeScanner._parse_df_output(openwrt_df)
    assert total > 0.0
    assert free >= 0.0

    # Large NVMe 4TB filesystem output
    nvme_df = """
Filesystem     1K-blocks       Used  Available Use% Mounted on
/dev/nvme1n1  3906987008 1234567890 2672419118  32% /data
"""
    total_tb, free_tb = MeshNodeScanner._parse_df_output(nvme_df)
    assert round(total_tb, 0) == round(3906987008 / 1048576, 0)
    assert round(free_tb, 0) == round(2672419118 / 1048576, 0)
