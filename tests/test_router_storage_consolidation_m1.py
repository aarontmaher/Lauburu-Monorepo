"""
Unit & Integration Tests for Generation 32 Milestone M1: Storage Consolidation & Seamless Login
Subsystems:
  - 00_core_infrastructure/router_foundation (Samba4 config, template, consolidate_router_storage.sh)
  - 06_scripts_and_tooling/storage/mount_router_network_storage.sh
  - 01_apps/screen_lens/src/lens_canonical_storage_governor.py
"""
import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/screen_lens/src"))

from lens_canonical_storage_governor import CanonicalStorageGovernor, calculate_sha256


class TestRouterConfigurationFiles:
    """Validates syntax and configuration parameters of router storage files."""

    def test_consolidate_router_storage_script_syntax(self):
        script_path = REPO_ROOT / "00_core_infrastructure/router_foundation/router/usr/bin/consolidate_router_storage.sh"
        assert script_path.exists(), f"Missing script at {script_path}"
        # Validate syntax via sh -n
        res = subprocess.run(["sh", "-n", str(script_path)], capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in script: {res.stderr}"

    def test_consolidate_router_storage_script_status_execution(self):
        script_path = REPO_ROOT / "00_core_infrastructure/router_foundation/router/usr/bin/consolidate_router_storage.sh"
        assert script_path.exists(), f"Missing script at {script_path}"
        # Validate runtime execution via sh <script> status returns exit code 0
        res = subprocess.run(["sh", str(script_path), "status"], capture_output=True, text=True)
        assert res.returncode == 0, f"Runtime error in script status: {res.stderr}"
        assert "Lauburu Router Storage Consolidation Status" in res.stdout

    def test_samba4_uci_config_single_share(self):
        config_path = REPO_ROOT / "00_core_infrastructure/router_foundation/router/etc/config/samba4"
        assert config_path.exists(), f"Missing config at {config_path}"
        content = config_path.read_text()

        # Must export only lauburu_storage
        assert "config sambashare" in content
        assert "option name 'lauburu_storage'" in content
        assert "seaweedfs" not in content.lower() or "option name 'seaweedfs'" not in content
        assert "lauburu_shared" not in content

        # Required options
        assert "option guest_ok 'yes'" in content
        assert "option guest_only 'yes'" in content
        assert "option force_root '1'" in content
        assert "option path '/mnt/lauburu_storage'" in content

    def test_smb_conf_template_guest_and_encryption_parameters(self):
        template_path = REPO_ROOT / "00_core_infrastructure/router_foundation/router/etc/samba/smb.conf.template"
        assert template_path.exists(), f"Missing template at {template_path}"
        content = template_path.read_text()

        # Encryption must be disabled to prevent macOS login loops
        assert "smb encrypt = disabled" in content
        assert "server smb encrypt = disabled" in content

        # Guest account & mapping
        assert "guest account = nobody" in content
        assert "map to guest = Bad User" in content

        # Subnet restriction
        assert "hosts allow = 192.168.8.0/24 127.0.0.1 100.0.0.0/8" in content
        assert "hosts deny = 0.0.0.0/0" in content

    def test_mount_router_network_storage_script_syntax(self):
        mount_script = REPO_ROOT / "06_scripts_and_tooling/storage/mount_router_network_storage.sh"
        assert mount_script.exists(), f"Missing mount script at {mount_script}"
        res = subprocess.run(["bash", "-n", str(mount_script)], capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in mount script: {res.stderr}"

        content = mount_script.read_text()
        assert "Router_Unified" in content
        assert "lauburu_storage" in content


class TestScreenLensCanonicalStorageGovernor:
    """Tests Screen Lens Storage Governor directory enforcement and auto-organization."""

    @pytest.fixture
    def temp_storage_env(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="lauburu_gov_test_"))
        unified_root = temp_dir / "Router_Unified"
        unified_root.mkdir(parents=True, exist_ok=True)
        (unified_root / "distributed_dfs").mkdir(parents=True, exist_ok=True)
        (unified_root / "local_flash").mkdir(parents=True, exist_ok=True)
        yield unified_root
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_governor_initialization(self, temp_storage_env):
        gov = CanonicalStorageGovernor(custom_router_mount=temp_storage_env)
        assert gov.router_mount == temp_storage_env

    def test_governor_enforce_router_unified_structure(self, temp_storage_env):
        gov = CanonicalStorageGovernor(custom_router_mount=temp_storage_env)
        res = gov.enforce_router_unified_structure()
        assert res["active"] is True
        assert res["writable"] is True

        # Verify all canonical paths were created
        for sub in gov.router_dfs_structure:
            assert (temp_storage_env / sub).exists()
        for sub in gov.router_flash_structure:
            assert (temp_storage_env / sub).exists()

    def test_governor_auto_organize_storage(self, temp_storage_env):
        gov = CanonicalStorageGovernor(custom_router_mount=temp_storage_env)
        gov.enforce_router_unified_structure()

        staging = temp_storage_env / "local_flash/staging"
        staging.mkdir(parents=True, exist_ok=True)

        # Create unorganized sample files in staging
        f_ecg = staging / "movesense_raw_ecg_sample.csv"
        f_ecg.write_text("timestamp,ecg\n0.00,0.12\n")

        f_lora = staging / "continuous_lora_sample.parquet"
        f_lora.write_bytes(b"PAR1_MOCK_PARQUET_HEADER_DATA")

        f_telem = staging / "mesh_ping_telemetry.json"
        f_telem.write_text('{"latency_ms": 0.54, "status": "ok"}')

        f_image = staging / "pixel_10_camera_frame.png"
        f_image.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

        f_doc = staging / "WHITE_PAPER_ARCHITECTURE.md"
        f_doc.write_text("# Whitepaper\nLauburu Sovereign Mesh\n")

        # Run auto-organization
        res = gov.auto_organize_storage(source_dir=staging)
        assert res["organized_count"] == 5

        # Verify items were moved to their respective canonical directories
        assert (temp_storage_env / "distributed_dfs/biometrics/movesense_raw_ecg_sample.csv").exists()
        assert (temp_storage_env / "distributed_dfs/lora_datasets/continuous_lora_sample.parquet").exists()
        assert (temp_storage_env / "local_flash/telemetry/mesh_ping_telemetry.json").exists()
        assert (temp_storage_env / "local_flash/edge_mounts/pixel_10_dcim/pixel_10_camera_frame.png").exists()
        assert (temp_storage_env / "distributed_dfs/obsidian_vault/WHITE_PAPER_ARCHITECTURE.md").exists()

        # Check that staging is now clean
        remaining = [f.name for f in staging.iterdir() if not f.name.startswith(".")]
        assert len(remaining) == 0

    def test_calculate_sha256_integrity(self, temp_storage_env):
        sample_file = temp_storage_env / "sample.txt"
        sample_file.write_text("Lauburu Monorepo Generation 32 Integrity Test")
        hash1 = calculate_sha256(sample_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64


class TestLiveRouterStorageSMB:
    """Tests live SMB broadcast and unified mount when router is reachable."""

    @pytest.fixture(autouse=True)
    def check_router_online(self):
        # Quick check if router port 445 is reachable
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        try:
            s.connect(("192.168.8.1", 445))
            s.close()
            self.online = True
        except Exception:
            self.online = False
            pytest.skip("Router 192.168.8.1:445 not reachable from this node")

    def test_smbutil_view_single_broadcast_share(self):
        res = subprocess.run(["smbutil", "view", "//guest@192.168.8.1"], capture_output=True, text=True)
        assert res.returncode == 0, f"smbutil failed: {res.stderr}"
        stdout = res.stdout

        # Verify lauburu_storage is the only Disk share
        assert "lauburu_storage" in stdout
        assert "seaweedfs" not in stdout
        assert "lauburu_shared" not in stdout

    def test_unified_mount_active_and_accessible(self):
        mount_path = Path.home() / "Network_Storage/Router_Unified"
        assert mount_path.exists(), f"Mount path {mount_path} does not exist"

        # Check subdirectories
        assert (mount_path / "distributed_dfs").exists(), "distributed_dfs missing"
        assert (mount_path / "local_flash").exists(), "local_flash missing"

        # Read/write test
        test_file = mount_path / ".pytest_m1_probe.txt"
        test_file.write_text("pytest probe ok")
        assert test_file.exists()
        test_file.unlink()
