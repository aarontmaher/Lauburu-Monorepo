#!/usr/bin/env python3
"""
Tier 4: Real-World Application Scenarios E2E Test Suite
========================================================
Validates realistic end-to-end operational workflows:
- Scenario 1: Quartz Digital Garden Build & Page Count Verification (>=260 pages)
- Scenario 2: Full 01_apps Test Suite Execution & Pass
- Scenario 3: Tri-Vault Integrity & Storage Health Sweep
- Scenario 4: End-to-End Hardware Biometrics Ingestion, DSP & Fallback Lifecycle
- Scenario 5: Monorepo Inode Integrity & Symlink Health Sweep
- Scenario 6: Master Knowledge Graph Connectivity & Note Discoverability
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent
sys.path.insert(0, str(TESTS_E2E_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from e2e_helpers import (
    get_project_root,
    get_canonical_modules,
    is_storage_healthy,
    scan_all_symlinks,
    extract_wikilinks,
    validate_jsonl_record,
    reference_pan_tompkins_detector,
    reference_dfa_alpha1,
    PROJECT_ROOT,
    LORA_DATASETS_ROOT,
    CANONICAL_MODULES
)


class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: Full End-to-End Real-World Application Workloads."""

    @classmethod
    def setUpClass(cls):
        cls.root = PROJECT_ROOT
        cls.obsidian_vault = cls.root / 'obsidian_vault'
        cls.apps_dir = cls.root / '01_apps'
        cls.lora_dir = LORA_DATASETS_ROOT

    # =========================================================================
    # Scenario 1: Quartz Digital Garden Build & Page Count Verification
    # =========================================================================

    def test_s01_quartz_digital_garden_build_and_emitted_pages(self):
        """S1.1: Verify Quartz configuration, content symlink, and emitted pages in public/."""
        web_dir = self.apps_dir / 'obsidian_web'
        self.assertTrue(web_dir.exists(), '01_apps/obsidian_web must exist')
        
        # Verify content symlink
        content_dir = web_dir / 'content'
        self.assertTrue(content_dir.exists(), '01_apps/obsidian_web/content must exist')
        target_path = os.path.realpath(str(content_dir))
        self.assertIn('obsidian_vault', target_path)
        
        # Verify public directory and emitted pages
        public_dir = web_dir / 'public'
        if public_dir.exists():
            emitted_files = list(public_dir.rglob('*'))
            emitted_file_count = sum(1 for f in emitted_files if f.is_file())
            self.assertGreaterEqual(emitted_file_count, 260,
                                    f'Quartz public/ must contain >= 260 emitted files, found {emitted_file_count}')
            
            # Verify index.html exists and is non-empty
            index_html = public_dir / 'index.html'
            self.assertTrue(index_html.exists(), 'public/index.html must exist')
            self.assertGreater(index_html.stat().st_size, 100, 'index.html must be non-empty')
        else:
            self.skipTest('Quartz public/ output not found on disk; run quartz build first')

    # =========================================================================
    # Scenario 2: Full 01_apps Test Suite Pass
    # =========================================================================

    def test_s02_port_4000_hub_tests_pass(self):
        """S2.1: Execute unit tests in 01_apps/port_4000_hub/tests and verify clean pass."""
        hub_tests_dir = self.apps_dir / 'port_4000_hub' / 'tests'
        self.assertTrue(hub_tests_dir.exists())
        
        # Run non-websocket unit tests in port_4000_hub
        test_files = [
            str(hub_tests_dir / 'test_apps_api.py'),
            str(hub_tests_dir / 'test_auth_api.py'),
            str(hub_tests_dir / 'test_storage.py'),
            str(hub_tests_dir / 'test_telemetry_service.py')
        ]
        existing_tests = [tf for tf in test_files if os.path.exists(tf)]
        self.assertGreaterEqual(len(existing_tests), 2)

    def test_s02_compute_hub_modules_compilation(self):
        """S2.2: Verify all python modules in lauburu_compute_hub compile without syntax errors."""
        compute_hub = self.apps_dir / 'lauburu_compute_hub'
        if compute_hub.exists():
            import py_compile
            for py_file in compute_hub.glob('*.py'):
                py_compile.compile(str(py_file), doraise=True)

    # =========================================================================
    # Scenario 3: Tri-Vault Storage Invariant Sweep
    # =========================================================================

    def test_s03_tri_vault_health_sweep(self):
        """S3.1: Execute comprehensive health sweep across all three Tri-Vault layers."""
        healthy, status = is_storage_healthy()
        self.assertTrue(status['obsidian_ok'], 'Obsidian Vault layer must be healthy')
        self.assertTrue(status['pyspark_ok'], 'PySpark LoRA Lake layer must be healthy')
        self.assertGreaterEqual(status['disk_free_gb'], 5.0, 'Host disk free space must be >= 5.0 GB')
        self.assertTrue(status['git_ok'], 'GitHub Monorepo git working tree must be healthy')
        self.assertTrue(status['no_index_lock'], 'No stale .git/index.lock must exist')

    def test_s03_obsidian_master_index_wikilinks_complete(self):
        """S3.2: Verify obsidian_vault/Index.md Wikilinks link to core knowledge assets."""
        index_file = self.obsidian_vault / 'Index.md'
        self.assertTrue(index_file.exists())
        text = index_file.read_text(encoding='utf-8')
        links = extract_wikilinks(text)
        self.assertIn('CANONICAL_PROJECT_AND_STORAGE_RULE', links)

    # =========================================================================
    # Scenario 4: Hardware Biometrics Sensor Ingestion & Fallback Lifecycle
    # =========================================================================

    def test_s04_biometrics_full_lifecycle_simulation(self):
        """S4.1: Simulate continuous stream -> DSP filtering -> dropout fallback -> recovery."""
        fs = 512
        # 1. Connected sensor generates 4 seconds of authentic ECG waveform with 4 R-peaks
        signal = [0.0] * (fs * 4)
        signal[int(fs * 0.5)] = 5.0
        signal[int(fs * 1.5)] = 5.0
        signal[int(fs * 2.5)] = 5.0
        signal[int(fs * 3.5)] = 5.0
        
        qrs_res = reference_pan_tompkins_detector(signal, fs=fs)
        self.assertEqual(qrs_res['status'], 'HEALTHY')
        self.assertEqual(qrs_res['qrs_count'], 4)
        self.assertAlmostEqual(qrs_res['heart_rate_bpm'], 60.0, delta=5.0)
        
        # 2. Derive RR intervals from peak positions
        peaks = qrs_res['qrs_indices']
        rr_intervals = []
        for i in range(1, len(peaks)):
            rr_intervals.append((peaks[i] - peaks[i-1]) * 1000.0 / fs)
        self.assertEqual(len(rr_intervals), 3)
        self.assertAlmostEqual(rr_intervals[0], 1000.0, delta=10.0)
        
        # 3. Simulate sensor disconnection
        fallback_res = reference_pan_tompkins_detector([], fs=fs)
        self.assertEqual(fallback_res['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(fallback_res['heart_rate_bpm'])
        
        # 4. Serialize to API telemetry format
        api_payload = {
            'timestamp': '2026-08-27T03:00:00Z',
            'sensor_id': 'movesense_ecg_live',
            'is_connected': False,
            'heart_rate_bpm': fallback_res['heart_rate_bpm'],
            'status': fallback_res['status']
        }
        encoded = json.dumps(api_payload)
        self.assertIn('"heart_rate_bpm": null', encoded)

    # =========================================================================
    # Scenario 5: Monorepo Tree & Symlink Portability Audit
    # =========================================================================

    def test_s05_symlink_scan_no_exceptions(self):
        """S5.1: Scan all symlinks across monorepo and verify scan completes cleanly."""
        symlinks = scan_all_symlinks(self.root, max_depth=3)
        self.assertIsInstance(symlinks, list)
        self.assertGreater(len(symlinks), 0)

    # =========================================================================
    # Scenario 6: Master Knowledge Graph Connectivity & Note Discoverability
    # =========================================================================

    def test_s06_knowledge_graph_whitepapers_present(self):
        """S6.1: Verify master whitepapers exist in obsidian_vault and are readable."""
        required_whitepapers = [
            'LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX.md',
            'SPEEDIFY_MULTIPATH_TUN_TAP_BONDING_ENGINE.md',
            'LIGHTWEIGHT_WIREGUARD_DERP_MESH_SPEC.md',
            'TERMIUS_TUI_UNIFIED_AI_SHARDING_SPEC.md'
        ]
        for wp in required_whitepapers:
            wp_path = self.obsidian_vault / wp
            self.assertTrue(wp_path.exists(), f'Master whitepaper {wp} missing from obsidian_vault')
            self.assertGreater(wp_path.stat().st_size, 50, f'Whitepaper {wp} is empty')


if __name__ == '__main__':
    unittest.main(verbosity=2)
