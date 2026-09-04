"""
Path: tests/test_storage_architecture_governance.py
Test Suite: R2 Canonical Read-Only Storage Context Map Governance & Tri-Vault Health Verification
Zero-Mock Compliance: Evaluates authentic filesystem metadata, real SHA256 checksums,
genuine POSIX write rejection, and live Tri-Vault storage invariants without mock substitutions.
"""

import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
PRIMARY_MAP = REPO_ROOT / "07_docs_and_architecture" / "STORAGE_ARCHITECTURE_CONTEXT_MAP.md"
MIRROR_MAP = REPO_ROOT / "obsidian_vault" / "07_STORAGE" / "CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md"
EXPECTED_SHA256 = "80e96726403861ba55f8d9029442fb44e581bfb2da345adc0a27fce024ef0b02"


class TestStorageArchitectureGovernance:
    """Verifies R2 Read-Only Governance, POSIX permissions, and Tri-Vault storage health invariants."""

    def test_both_context_map_files_exist_and_nonzero(self):
        """Assert both primary and mirror context map files exist and have non-zero size."""
        assert PRIMARY_MAP.is_file(), f"Primary map missing at: {PRIMARY_MAP}"
        assert MIRROR_MAP.is_file(), f"Mirror map missing at: {MIRROR_MAP}"

        size_primary = PRIMARY_MAP.stat().st_size
        size_mirror = MIRROR_MAP.stat().st_size
        assert size_primary > 0, "Primary map file is empty (0 bytes)"
        assert size_mirror > 0, "Mirror map file is empty (0 bytes)"
        assert size_primary == size_mirror, (
            f"File sizes do not match: primary={size_primary}, mirror={size_mirror}"
        )

    def test_context_map_permissions_mode_0444(self):
        """Assert both files have strict POSIX mode 0444 (read-only for user, group, other)."""
        mode_primary = stat.S_IMODE(PRIMARY_MAP.stat().st_mode)
        mode_mirror = stat.S_IMODE(MIRROR_MAP.stat().st_mode)

        expected_mode = 0o444
        assert mode_primary == expected_mode, (
            f"Primary mode is {oct(mode_primary)}, expected {oct(expected_mode)}"
        )
        assert mode_mirror == expected_mode, (
            f"Mirror mode is {oct(mode_mirror)}, expected {oct(expected_mode)}"
        )

        # Confirm all write bits (user, group, other) are cleared
        assert (mode_primary & 0o222) == 0, f"Primary has active write bits: {oct(mode_primary)}"
        assert (mode_mirror & 0o222) == 0, f"Mirror has active write bits: {oct(mode_mirror)}"

        # Confirm OS reports not writable
        assert not os.access(PRIMARY_MAP, os.W_OK), "Primary file is unexpectedly writable by current process"
        assert not os.access(MIRROR_MAP, os.W_OK), "Mirror file is unexpectedly writable by current process"

        # Confirm OS reports readable
        assert os.access(PRIMARY_MAP, os.R_OK), "Primary file is not readable"
        assert os.access(MIRROR_MAP, os.R_OK), "Mirror file is not readable"

    def test_adversarial_write_rejection(self):
        """Assert that adversarial write and append attempts raise PermissionError."""
        # Append attempt on primary
        with pytest.raises(PermissionError):
            with open(PRIMARY_MAP, "a", encoding="utf-8") as f:
                f.write("\n<!-- Adversarial append attempt -->\n")

        # Write/truncate attempt on primary
        with pytest.raises(PermissionError):
            with open(PRIMARY_MAP, "w", encoding="utf-8") as f:
                f.write("<!-- Adversarial truncate attempt -->")

        # Append attempt on mirror
        with pytest.raises(PermissionError):
            with open(MIRROR_MAP, "a", encoding="utf-8") as f:
                f.write("\n<!-- Adversarial append attempt -->\n")

        # Write/truncate attempt on mirror
        with pytest.raises(PermissionError):
            with open(MIRROR_MAP, "w", encoding="utf-8") as f:
                f.write("<!-- Adversarial truncate attempt -->")

    def test_sha256_mirror_parity(self):
        """Assert 100% bit-for-bit SHA256 match between primary file and Obsidian mirror."""
        primary_bytes = PRIMARY_MAP.read_bytes()
        mirror_bytes = MIRROR_MAP.read_bytes()

        sha_primary = hashlib.sha256(primary_bytes).hexdigest()
        sha_mirror = hashlib.sha256(mirror_bytes).hexdigest()

        assert sha_primary == sha_mirror, (
            f"SHA256 mismatch between primary and mirror!\n"
            f"Primary: {sha_primary}\n"
            f"Mirror:  {sha_mirror}"
        )
        assert sha_primary == EXPECTED_SHA256, (
            f"Primary SHA256 {sha_primary} does not match expected canonical hash {EXPECTED_SHA256}"
        )
        assert primary_bytes == mirror_bytes, "Raw bytes differ between primary and mirror"

    def test_frontmatter_governance_and_consensus_freeze(self):
        """Assert that frontmatter and text body declare strict consensus freeze."""
        primary_text = PRIMARY_MAP.read_text(encoding="utf-8")
        mirror_text = MIRROR_MAP.read_text(encoding="utf-8")

        assert primary_text == mirror_text, "Content mismatch between primary and mirror text"

        # Governance declarations
        assert "status: READ_ONLY_AWAITING_CLOUD_CONSENSUS" in primary_text
        assert "access_mode: READ_ONLY" in primary_text
        assert "governance: TRI-VAULT & 7-LAYER PHYSICAL MESH" in primary_text
        assert "## 🔒 3. Read-Only Enforcement & Consensus Lock" in primary_text
        assert "Local Frontier Review (Qwen 3.8 Max)" in primary_text
        assert "Cloud Frontier Review (Gemini 3.8 Flash High)" in primary_text
        assert "Aaron's Sovereign Authorization" in primary_text

    def test_git_version_control_tracking(self):
        """Assert that both context map files are tracked/staged in git."""
        result = subprocess.run(
            ["git", "status", "--porcelain", str(PRIMARY_MAP), str(MIRROR_MAP)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        status_output = result.stdout.strip()
        # Ensure neither file is untracked (i.e. neither starts with '??')
        for line in status_output.splitlines():
            assert not line.startswith("??"), f"Context map file is untracked in git: {line}"

        # Verify git index tracks both files
        ls_files_result = subprocess.run(
            [
                "git",
                "ls-files",
                "--stage",
                "07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md",
                "obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        staged_output = ls_files_result.stdout.strip()
        assert "STORAGE_ARCHITECTURE_CONTEXT_MAP.md" in staged_output, "Primary map not tracked in git index"
        assert "CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md" in staged_output, "Mirror map not tracked in git index"

    def test_tri_vault_storage_health(self):
        """Assert Tri-Vault storage health invariants per RULE[user_global] § 5."""
        # Tier 1: Obsidian Vault Health
        obs_vault = REPO_ROOT / "obsidian_vault"
        index_file = obs_vault / "Index.md"
        assert obs_vault.is_dir(), f"Obsidian Vault directory missing at {obs_vault}"
        assert index_file.is_file(), f"Obsidian master Index.md missing at {index_file}"
        assert index_file.stat().st_size > 0, "Obsidian Index.md is empty"

        idx_text = index_file.read_text(encoding="utf-8")
        for req_link in [
            "[[Index]]",
            "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
            "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
        ]:
            assert req_link in idx_text, f"Missing required Wikilink {req_link} in {index_file}"

        # Tier 2: PySpark Data Lake / lora_datasets
        lora_datasets_dir = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
        local_data_dir = REPO_ROOT / "04_data_and_memory"
        assert lora_datasets_dir.is_dir(), f"lora_datasets missing at {lora_datasets_dir}"
        assert local_data_dir.is_dir(), f"04_data_and_memory missing at {local_data_dir}"

        # Tier 3: GitHub Monorepo Tree Health
        git_dir = REPO_ROOT / ".git"
        git_lock = git_dir / "index.lock"
        assert git_dir.is_dir(), "Repository is not a valid git tree"
        assert not git_lock.exists(), f"Stale git index lock detected: {git_lock}"

        # Storage Invariant: Disk Headroom >= 5.0 GB
        host_free_gb = shutil.disk_usage("/Users/aaron").free / (1024**3)
        repo_free_gb = shutil.disk_usage(str(REPO_ROOT)).free / (1024**3)
        assert host_free_gb >= 5.0, f"Host free disk space too low: {host_free_gb:.2f} GB < 5.0 GB"
        assert repo_free_gb >= 5.0, f"Repo free disk space too low: {repo_free_gb:.2f} GB < 5.0 GB"
