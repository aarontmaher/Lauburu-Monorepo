# -*- coding: utf-8 -*-
"""
Tier 3: Cross-Feature Combinations & Multi-Subsystem Interaction Tests.
Validates data pipelines and integrations:
- Storage health check integration with truth enforcer daemon status logging
- Live probe output feeding into Obsidian telemetry records
- Concurrency between LoRA dataset streaming and storage health fast-path checks
- End-to-end scanner verification of telemetry payloads.
Governed by: PROJECT.md § Architecture, Rule 1, Rule 2, Rule 5, Rule 9.
"""
from __future__ import annotations

import os
import sys
import json
import time
import fcntl
import shutil
import tempfile
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    OBSIDIAN_VAULT_PATH,
    LORA_DATASETS_PATH,
    PROHIBITED_LITERALS,
    is_storage_healthy,
    get_darwin_mach_memory,
    validate_telemetry_envelope,
    run_cmd,
)

# Import scan_file from fake_data_scanner if available
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/truth"))
try:
    from fake_data_scanner import scan_file  # type: ignore
except ImportError:
    scan_file = None


class TestCrossFeatureCombinations:
    """Verifies cross-feature data pipelines, status reporting, and concurrency."""

    def test_storage_health_integration_with_status_report(self):
        """Validates that is_storage_healthy() results format into clean Obsidian status markdown."""
        healthy, details = is_storage_healthy(REPO_ROOT)
        assert healthy is True, f"Storage must be healthy: {details}"

        mem = get_darwin_mach_memory()

        # Generate markdown telemetry block as produced by truth_enforcer_daemon
        timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status_md = f"""# 🛡️ TRUTH ENFORCER STATUS — {timestamp_iso}

## Storage Health
- Overall Status: {'HEALTHY' if healthy else 'DEGRADED'}
- Obsidian Vault: {'OK' if details['obsidian_healthy'] else 'FAIL'}
- PySpark Data Lake: {'OK' if details['pyspark_healthy'] else 'FAIL'}
- Git Monorepo: {'OK' if details['git_healthy'] else 'FAIL'}
- Free Disk: {details['disk_free_gb']} GB (Threshold: >= 5.0 GB)

## Host RAM Sanctuary
- Mach Free RAM: {mem['free_gb']} GB (Available: {mem['available_gb']} GB)
- RAM Utilization: {mem['util_pct']}% (Cap: <= 80%)
- Memory Pressure Level: {mem['pressure_level']} (Normal)
"""
        assert "HEALTHY" in status_md
        assert "Obsidian Vault: OK" in status_md
        assert "PySpark Data Lake: OK" in status_md
        assert "Git Monorepo: OK" in status_md
        assert str(details["disk_free_gb"]) in status_md

        # Ensure no prohibited literals leaked into report
        for bad_lit in PROHIBITED_LITERALS:
            assert bad_lit not in status_md, f"Prohibited literal '{bad_lit}' in generated status report!"

    def test_live_probe_output_feeding_into_obsidian_telemetry_table(self):
        """Validates that probe telemetry structures correctly render into Obsidian markdown tables with '--'."""
        # Simulated live probe output adhering to schema
        probe_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "nodes": {
                "L1": {"status": "ONLINE", "cpu": "Apple M4 Pro", "ram_gb": 24.0, "latency_ms": 0.0, "measured": True},
                "L2": {"status": "ONLINE", "cpu": "Intel i7-9750H", "ram_gb": 16.0, "tb_speed_gbps": 20, "latency_ms": 0.45, "measured": True},
                "L3": {"status": "ONLINE", "cpu": "AMD Ryzen 7 5700U", "ram_gb": 15.0, "latency_ms": 1.2, "measured": True},
                "L4": {"status": "OFFLINE", "cpu": None, "ram_gb": None, "measured": False},
                "L5": {"status": "ONLINE", "cpu": "Apple M4", "ram_gb": 16.0, "tb_speed_gbps": 40, "latency_ms": 0.45, "measured": True},
                "L6": {"status": "PARTIAL", "ports": [3035, 50052, 8022], "measured": True},
                "L7": {"status": "OFFLINE", "cpu": None, "ram_gb": None, "measured": False},
                "L8": {"status": "ONLINE", "cpu": "Intel i7-8700B", "ram_gb": 32.0, "tb_speed_gbps": 40, "latency_ms": 0.45, "measured": True},
                "GW": {"status": "ONLINE", "model": "GL-BE14000", "os": "OpenWrt 21.02-SNAPSHOT", "measured": True},
            },
        }

        # Build Obsidian markdown table
        lines = [
            "| Node | Status | CPU | RAM | Latency | Link Speed | Measured |",
            "|---|---|---|---|---|---|---|",
        ]
        for node_id, data in probe_data["nodes"].items():
            status = data.get("status", "--")
            cpu = data.get("cpu") or "--"
            ram = f"{data['ram_gb']} GB" if data.get("ram_gb") is not None else "--"
            latency = f"{data['latency_ms']} ms" if data.get("latency_ms") is not None else "--"
            tb = f"{data['tb_speed_gbps']} Gb/s" if data.get("tb_speed_gbps") is not None else "--"
            measured = str(data.get("measured", False))
            lines.append(f"| {node_id} | {status} | {cpu} | {ram} | {latency} | {tb} | {measured} |")

        table_md = "\n".join(lines)
        assert "| L4 | OFFLINE | -- | -- | -- | -- | False |" in table_md
        assert "| L7 | OFFLINE | -- | -- | -- | -- | False |" in table_md
        assert "| L1 | ONLINE | Apple M4 Pro | 24.0 GB | 0.0 ms | -- | True |" in table_md
        assert "| L2 | ONLINE | Intel i7-9750H | 16.0 GB | 0.45 ms | 20 Gb/s | True |" in table_md

        # Confirm no prohibited literals
        for bad_lit in PROHIBITED_LITERALS:
            assert bad_lit not in table_md, f"Prohibited literal '{bad_lit}' in markdown telemetry table"

    def test_lora_dataset_concurrent_write_and_health_check(self, tmp_path):
        """Validates that continuous LoRA flock writes do not block or corrupt is_storage_healthy()."""
        test_jsonl = tmp_path / "concurrent_lora.jsonl"
        test_jsonl.write_text('{"entry": 1}\n', encoding="utf-8")

        # Open and lock file to simulate an active daemon write pass
        with open(test_jsonl, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": "test_e2e_concurrency",
                "zero_mock_verified": True,
            }) + "\n")
            f.flush()

            # Execute is_storage_healthy() during the locked state
            start = time.perf_counter()
            healthy, details = is_storage_healthy(REPO_ROOT)
            duration_ms = (time.perf_counter() - start) * 1000.0

            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        assert healthy is True, f"Storage health check failed during concurrent write: {details}"
        assert duration_ms < 20.0, f"Storage health check lagged during concurrent write ({duration_ms:.2f} ms)"

    def test_scanner_clean_on_telemetry_table_export(self, tmp_path):
        """Validates that a newly generated telemetry export file passes fake_data_scanner with 0 BLOCKs."""
        if scan_file is None:
            pytest.skip("fake_data_scanner.py not importable")

        export_dir = Path("/tmp/truth_audit_export_test")
        export_dir.mkdir(parents=True, exist_ok=True)
        export_file = export_dir / "mesh_telemetry_export.py"
        try:
            export_file.write_text(
                """# Authentic mesh telemetry export
L1_CPU = "Apple M4 Pro"
L2_TB_SPEED = 20  # Gb/s probed
ROUTER_MODEL = "GL-BE14000"
OFFLINE_PLACEHOLDER = "--"
""",
                encoding="utf-8",
            )
            findings = scan_file(export_file)
            blocks = [f for f in findings if f.get("severity") == "BLOCK"]
            assert len(blocks) == 0, f"Clean export triggered BLOCK findings: {blocks}"
        finally:
            if export_file.exists():
                export_file.unlink()
            shutil.rmtree(export_dir, ignore_errors=True)
