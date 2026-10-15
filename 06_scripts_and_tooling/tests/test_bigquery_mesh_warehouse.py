#!/usr/bin/env python3
"""
Unit tests for BigQuery Always Free Telemetry & Data Warehouse
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "04_data_and_memory"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

from bigquery_mesh_warehouse import BigQueryMeshWarehouse, TABLE_SCHEMAS


class TestBigQueryMeshWarehouse(unittest.TestCase):
    def setUp(self):
        self.mock_breaker = MagicMock()
        self.mock_breaker.can_run_bigquery_query.return_value = (True, "OK")
        self.warehouse = BigQueryMeshWarehouse(
            project_id="test-project",
            dataset_id="test_dataset",
            circuit_breaker=self.mock_breaker,
        )

    def test_table_schemas_defined(self):
        expected_tables = ["mesh_node_telemetry", "ecg_biometrics", "ai_debate_ledger", "lora_training_metrics"]
        for tbl in expected_tables:
            self.assertIn(tbl, TABLE_SCHEMAS)
            schema = TABLE_SCHEMAS[tbl]
            field_names = [f["name"] for f in schema]
            self.assertIn("timestamp", field_names)

    @patch("subprocess.run")
    def test_dry_run_query_parsing(self, mock_sub):
        mock_sub.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="Query will process 1048576 bytes."
        )
        ok, bytes_proc, msg = self.warehouse.dry_run_query("SELECT 1;")
        self.assertTrue(ok)
        self.assertEqual(bytes_proc, 1048576)

    @patch("subprocess.run")
    def test_execute_query_circuit_breaker_blocking(self, mock_sub):
        # Mock dry run succeeding
        mock_sub.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="Query will process 500000 bytes."
        )
        # But circuit breaker blocks it
        self.mock_breaker.can_run_bigquery_query.return_value = (False, "Monthly budget reached")

        ok, results, msg = self.warehouse.execute_query("SELECT * FROM test;")
        self.assertFalse(ok)
        self.assertIn("Circuit breaker blocked query", msg)
        self.assertEqual(results, [])

    @patch("subprocess.run")
    def test_execute_query_success(self, mock_sub):
        # 1st call for dry-run, 2nd call for actual query execution
        dry_run_mock = MagicMock(returncode=0, stdout="", stderr="Query will process 100 bytes.")
        exec_mock = MagicMock(returncode=0, stdout='[{"status": "HEALTHY", "count": 1}]', stderr="")
        mock_sub.side_effect = [dry_run_mock, exec_mock]

        ok, records, msg = self.warehouse.execute_query("SELECT status, count FROM test;")
        self.assertTrue(ok)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "HEALTHY")
        self.mock_breaker.record_bigquery_query.assert_called_once_with(100)


if __name__ == "__main__":
    unittest.main()
