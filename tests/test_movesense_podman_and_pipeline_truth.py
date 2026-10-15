#!/usr/bin/env python3
"""
Test Suite: Zero-Mock Truth Verification for Movesense Ingestion & Podman Suites.
Strictly follows Rule 1 (Zero-Mock Empirical Truth) and Rule 0 (Port Allocation Truth).
"""

import os
import sys
import json
import hashlib
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")

class TestMovesensePodmanAndPipelineTruth(unittest.TestCase):

    def test_01_movesense_showcase_pipeline_and_parquet_fidelity(self):
        """Proof 2: Verify authentic 1-second resolution without microsecond divisor collapse."""
        parquet_path = REPO_ROOT / "04_data_and_memory/movesense_parquet/movesense_training_dataset.parquet"
        self.assertTrue(parquet_path.exists(), "movesense_training_dataset.parquet must exist")

        # Read parquet via system python if current venv lacks pyarrow
        verify_cmd = (
            f"python3 -c \""
            f"import pandas as pd; "
            f"df = pd.read_parquet('{parquet_path}'); "
            f"print(len(df)); "
            f"valid_hr = df['cardiac_bpm_mean'].dropna(); "
            f"print(len(valid_hr)); "
            f"print(float(valid_hr.min())); "
            f"print(float(valid_hr.max()))"
            f"\""
        )
        res = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Failed to read parquet: {res.stderr}")

        lines = res.stdout.strip().split("\n")
        total_rows = int(lines[0])
        valid_hr_count = int(lines[1])
        min_bpm = float(lines[2])
        max_bpm = float(lines[3])

        # Prior buggy implementation collapsed 28,403 seconds to 35 rows.
        self.assertGreater(total_rows, 25000, f"Dataset collapsed! Expected >25k rows, got {total_rows}")
        self.assertEqual(total_rows, 28403, f"Exact second count mismatch: {total_rows}")

        # Verify authentic cardiac join
        self.assertGreater(valid_hr_count, 25000, f"Expected >25k authentic synchronized cardiac epochs, got {valid_hr_count}")
        self.assertGreaterEqual(min_bpm, 35.0, "Physiological min BPM out of bounds")
        self.assertLessEqual(max_bpm, 220.0, "Physiological max BPM out of bounds")

    def test_02_movesense_model_zero_mock_weights_and_metrics(self):
        """Proof 1 & 2: Verify physical silicon neural network artifact and metrics."""
        model_path = REPO_ROOT / "04_data_and_memory/models/movesense_kinematic_cardiac_net.pt"
        metrics_path = REPO_ROOT / "04_data_and_memory/models/movesense_model_metrics.json"

        self.assertTrue(model_path.exists(), "Model weights file must exist")
        self.assertTrue(metrics_path.exists(), "Model metrics file must exist")

        with open(metrics_path, "r") as f:
            metrics = json.load(f)

        self.assertEqual(metrics["device"], "mps", "Must execute on Apple Silicon Metal MPS")
        self.assertEqual(metrics["epochs"], 5)
        self.assertGreater(metrics["final_val_acc_pct"], 70.0)
        self.assertLess(metrics["history"][-1]["train_hr_mse"], metrics["history"][0]["train_hr_mse"], "Loss must decrease")

        # Cryptographic checksum verification
        with open(model_path, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(metrics["artifact_sha256"], actual_sha, "Checksum mismatch on model weights")

    def test_03_podman_container_configurations_and_ports(self):
        """Proof 2: Verify Podman multi-configuration suite and conflict-free port allocations."""
        compose_path = REPO_ROOT / "06_scripts_and_tooling/containers/movesense_ingestion/podman-compose.movesense.yml"
        self.assertTrue(compose_path.exists(), "podman-compose.movesense.yml must exist")

        content = compose_path.read_text()

        # Must NOT allocate port 8085 (reserved for SeaweedFS DFS / nginx)
        self.assertNotIn("8085", content, "Port 8085 collision detected! Must use port 8089 for RFCOMM.")
        self.assertIn("PORT=8089", content, "RFCOMM must be assigned to port 8089")

        # Verify all 3 configurations are defined
        self.assertIn("chromium-web-bluetooth", content)
        self.assertIn("go-gatt-browser", content)
        self.assertIn("bluetooth-serial-rfcomm", content)

        # Verify host D-Bus socket mount for BlueZ access
        self.assertIn("/run/dbus/system_bus_socket", content)

    def test_04_go_gatt_browser_compilation_and_endpoints(self):
        """Proof 1: Compile Go GATT browser and verify REST/SSE endpoints."""
        go_dir = REPO_ROOT / "06_scripts_and_tooling/containers/movesense_ingestion/go_gatt_browser"
        res = subprocess.run(
            ["go", "build", "-o", "/tmp/movesense_go_test_bin", "main.go"],
            cwd=go_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Go build failed: {res.stderr}")
        if os.path.exists("/tmp/movesense_go_test_bin"):
            os.remove("/tmp/movesense_go_test_bin")

        source = (go_dir / "main.go").read_text()
        self.assertIn("/api/devices", source)
        self.assertIn("/api/scan", source)
        self.assertIn("/api/connect", source)
        self.assertIn("/api/ingest", source)
        self.assertIn("/events", source)

if __name__ == "__main__":
    unittest.main()
