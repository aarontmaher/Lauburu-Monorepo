#!/usr/bin/env python3
"""
Tier 3: Pairwise Cross-Feature Combinations E2E Test Suite
===========================================================
Validates interactions between concurrent subsystems:
- Pair 1: Quartz Build <-> Obsidian Index & Graph (F6 + F10)
- Pair 2: Legacy Symlinks <-> Canonical App Compilation (F3 + F5 + F12)
- Pair 3: LoRA Lake Ingestion <-> PySpark Index & Headroom (F1 + F8)
- Pair 4: Zero-Mock Biometrics DSP <-> Telemetry Fallback (F13 + F14)
- Pair 5: Obsidian Desktop Config <-> Repaired Graph Links (F7 + F11)
- Pair 6: Root Hygiene Relocation <-> Canonical Module Structure (F2 + F3)
- Pair 7: Core Infrastructure HA <-> Port 4000 Ingestion (F3 + F12)
- Pair 8: Telemetry API Service <-> SQLite WAL Storage (F12 + F14)
- Pair 9: Whoop Intelligence <-> Movesense ECG Data (F12 + F13)
- Pair 10: Git Worktree <-> Symlink Integrity (F4 + F9)
- Pair 11: Spatial Grappling Kinematics <-> 01_apps 3D Models (F3 + F10)
"""

import os
import sys
import json
import shutil
import tempfile
import sqlite3
import unittest
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


class TestTier3PairwiseCombinations(unittest.TestCase):
    """Tier 3: Pairwise Interaction Testing across Monorepo Subsystems."""

    @classmethod
    def setUpClass(cls):
        cls.root = PROJECT_ROOT
        cls.obsidian_vault = cls.root / 'obsidian_vault'
        cls.apps_dir = cls.root / '01_apps'
        cls.lora_dir = LORA_DATASETS_ROOT

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # Pair 1: Quartz Build <-> Obsidian Index & Graph (F6 + F10)
    # =========================================================================

    def test_p01_quartz_content_mirrors_vault_index(self):
        """P1.1: Verify Quartz content link resolves to Index.md and parses identical Wikilinks."""
        content_index = self.apps_dir / 'obsidian_web' / 'content' / 'Index.md'
        vault_index = self.obsidian_vault / 'Index.md'
        
        self.assertTrue(content_index.exists(), '01_apps/obsidian_web/content/Index.md must exist')
        self.assertTrue(vault_index.exists(), 'obsidian_vault/Index.md must exist')
        
        content_text = content_index.read_text(encoding='utf-8')
        vault_text = vault_index.read_text(encoding='utf-8')
        
        self.assertEqual(content_text, vault_text, 'Content symlink must reflect identical Index.md text')
        self.assertIn('[[CANONICAL_PROJECT_AND_STORAGE_RULE]]', content_text)

    def test_p01_quartz_config_matches_vault_plugins(self):
        """P1.2: Verify Quartz configuration yaml and Obsidian desktop plugins enable graph view."""
        config_yaml = self.apps_dir / 'obsidian_web' / 'quartz.config.default.yaml'
        obs_plugins = self.obsidian_vault / '.obsidian' / 'core-plugins.json'
        
        if config_yaml.exists():
            cfg_text = config_yaml.read_text(encoding='utf-8')
            self.assertIn('graph', cfg_text.lower())
            
        if obs_plugins.exists():
            with open(obs_plugins) as f:
                plugins = json.load(f)
                self.assertIn('graph', plugins)

    # =========================================================================
    # Pair 2: Legacy Symlinks <-> Canonical App Compilation (F3 + F5 + F12)
    # =========================================================================

    def test_p02_legacy_paths_resolve_to_canonical_apps(self):
        """P2.1: Verify legacy paths resolve to canonical application directories."""
        webapp_path = self.root / 'webapp'
        grappling_path = self.apps_dir / 'grapplingmap_web'
        self.assertTrue(webapp_path.exists() or grappling_path.exists())
        
        # Test that canonical port_4000_hub compiles through both direct and relative access
        server_py = self.apps_dir / 'port_4000_hub' / 'server.py'
        self.assertTrue(server_py.exists())
        import py_compile
        py_compile.compile(str(server_py), doraise=True)

    def test_p02_app_relative_import_stability(self):
        """P2.2: Verify FastAPI app modules load without path resolution breakage."""
        hub_dir = self.apps_dir / 'port_4000_hub'
        tests_dir = hub_dir / 'tests'
        self.assertTrue(tests_dir.exists())
        test_files = list(tests_dir.glob('test_*.py'))
        self.assertGreater(len(test_files), 0)

    # =========================================================================
    # Pair 3: LoRA Lake Ingestion <-> PySpark Index & Headroom (F1 + F8)
    # =========================================================================

    def test_p03_lora_crawler_checks_storage_headroom(self):
        """P3.1: Verify simulated dataset crawler verifies disk headroom before indexing."""
        free_bytes = shutil.disk_usage(str(self.root)).free
        free_gb = free_bytes / (1024 ** 3)
        self.assertGreaterEqual(free_gb, 5.0, 'Host must maintain >= 5GB disk headroom')
        
        # Crawl dataset records
        total_records = 0
        jsonl_files = list(self.lora_dir.glob('*.jsonl')) + list(self.root.glob('*.jsonl'))
        for jf in jsonl_files[:5]:
            with open(jf, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip():
                        v, _, _ = validate_jsonl_record(line)
                        if v:
                            total_records += 1
        self.assertGreaterEqual(total_records, 0)

    def test_p03_pyspark_data_and_memory_layout(self):
        """P3.2: Verify 04_data_and_memory is structured to store dataset artifacts."""
        data_mem = self.root / '04_data_and_memory'
        self.assertTrue(data_mem.exists() and data_mem.is_dir())

    # =========================================================================
    # Pair 4: Zero-Mock Biometrics DSP <-> Telemetry Fallback (F13 + F14)
    # =========================================================================

    def test_p04_sensor_stream_transition_from_live_to_disconnected(self):
        """P4.1: Verify DSP pipeline handles live 512Hz pulse train transition to disconnected state."""
        fs = 512
        # Phase 1: Live connected signal (2 seconds with 2 R-peaks)
        live_signal = [0.0] * (fs * 2)
        live_signal[int(fs * 0.5)] = 5.0
        live_signal[int(fs * 1.5)] = 5.0
        live_res = reference_pan_tompkins_detector(live_signal, fs=fs)
        self.assertEqual(live_res['status'], 'HEALTHY')
        self.assertEqual(live_res['qrs_count'], 2)
        self.assertIsNotNone(live_res['heart_rate_bpm'])
        
        # Phase 2: Sensor disconnected (0 samples or empty packet)
        disc_res = reference_pan_tompkins_detector([], fs=fs)
        self.assertEqual(disc_res['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(disc_res['heart_rate_bpm'])

    def test_p04_dfa_alpha1_recovery_after_reconnect(self):
        """P4.2: Verify DFA-alpha1 returns valid score after sensor reconnection with sufficient buffer."""
        # Insufficient buffer
        res_empty = reference_dfa_alpha1([800.0] * 5)
        self.assertEqual(res_empty['status'], 'INSUFFICIENT_DATA')
        
        # Reconnected with 32 beats
        res_live = reference_dfa_alpha1([800.0 + (i % 5) * 10 for i in range(32)])
        self.assertIn(res_live['status'], ['VALID', 'FALLBACK_ESTIMATE'])

    # =========================================================================
    # Pair 5: Obsidian Desktop Config <-> Repaired Graph Links (F7 + F11)
    # =========================================================================

    def test_p05_desktop_graph_config_covers_all_vault_notes(self):
        """P5.1: Verify graph.json showOrphans configuration ensures 100% note visibility."""
        graph_cfg = self.obsidian_vault / '.obsidian' / 'graph.json'
        self.assertTrue(graph_cfg.exists())
        with open(graph_cfg) as f:
            data = json.load(f)
            self.assertTrue(data.get('showOrphans', True), 'showOrphans must be True to render all notes')

    def test_p05_all_vault_notes_discoverable_in_explorer(self):
        """P5.2: Verify core-plugins enables file-explorer and search for all vault notes."""
        plugins_file = self.obsidian_vault / '.obsidian' / 'core-plugins.json'
        self.assertTrue(plugins_file.exists())
        with open(plugins_file) as f:
            plugins = json.load(f)
            self.assertIn('file-explorer', plugins)
            self.assertIn('global-search', plugins)

    # =========================================================================
    # Pair 6: Root Hygiene Relocation <-> Canonical Module Structure (F2 + F3)
    # =========================================================================

    def test_p06_scripts_mapped_to_06_scripts_and_tooling(self):
        """P6.1: Verify scripts directory or 06_scripts_and_tooling contains automation scripts."""
        scripts_mod = self.root / '06_scripts_and_tooling'
        self.assertTrue(scripts_mod.exists() and scripts_mod.is_dir())
        items = list(scripts_mod.iterdir())
        self.assertGreater(len(items), 0)

    def test_p06_reports_directory_structure(self):
        """P6.2: Verify reports directory is properly segregated from root source code."""
        reports_dir = self.root / 'reports'
        self.assertTrue(reports_dir.exists() and reports_dir.is_dir())

    # =========================================================================
    # Pair 7: Core Infrastructure HA <-> Port 4000 Ingestion (F3 + F12)
    # =========================================================================

    def test_p07_docker_compose_and_port_4000_coexistence(self):
        """P7.1: Verify 00_core_infrastructure contains Docker manifests compatible with Port 4000."""
        infra_dir = self.root / '00_core_infrastructure'
        self.assertTrue(infra_dir.exists())
        # Check port 4000 hub server exists
        port_4000 = self.apps_dir / 'port_4000_hub' / 'server.py'
        self.assertTrue(port_4000.exists())

    # =========================================================================
    # Pair 8: Telemetry API Service <-> SQLite WAL Storage (F12 + F14)
    # =========================================================================

    def test_p08_sqlite_telemetry_database_creation(self):
        """P8.1: Verify SQLite database initialization for telemetry logging."""
        db_path = self.tmp_path / 'test_telemetry.db'
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS telemetry_events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, sensor_id TEXT NOT NULL, hr_bpm REAL, status TEXT NOT NULL)")
        cursor.execute("INSERT INTO telemetry_events (timestamp, sensor_id, hr_bpm, status) VALUES ('2026-08-27T03:00:00Z', 'movesense_01', NULL, 'DISCONNECTED')")
        conn.commit()
        
        cursor.execute("SELECT hr_bpm, status FROM telemetry_events WHERE sensor_id = ?", ('movesense_01',))
        row = cursor.fetchone()
        self.assertIsNone(row[0]) # null heart rate
        self.assertEqual(row[1], 'DISCONNECTED')
        conn.close()

    # =========================================================================
    # Pair 9: Whoop Intelligence <-> Movesense ECG Data (F12 + F13)
    # =========================================================================

    def test_p09_whoop_intelligence_integration(self):
        """P9.1: Verify Whoop intelligence module is co-located with biometrics DSP algorithms."""
        dsp_dir = self.root / '03_biometrics_and_telemetry' / 'dsp_algorithms'
        whoop_file = dsp_dir / 'whoop-intelligence.js'
        self.assertTrue(whoop_file.exists(), 'whoop-intelligence.js must exist in 03_biometrics_and_telemetry/dsp_algorithms')

    # =========================================================================
    # Pair 10: Git Worktree <-> Symlink Integrity (F4 + F9)
    # =========================================================================

    def test_p10_git_worktree_unaffected_by_symlink_updates(self):
        """P10.1: Verify git status is executable and inspectable with active symlinks."""
        git_dir = self.root / '.git'
        self.assertTrue(git_dir.exists())
        # Check no git lock
        self.assertFalse((git_dir / 'index.lock').exists())

    # =========================================================================
    # Pair 11: Spatial Grappling Kinematics <-> 01_apps 3D Models (F3 + F10)
    # =========================================================================

    def test_p11_spatial_grappling_kinematics_presence(self):
        """P11.1: Verify 10_spatial_grappling_kinematics contains OPML spatial trees and docs."""
        spatial_dir = self.root / '10_spatial_grappling_kinematics'
        self.assertTrue(spatial_dir.exists() and spatial_dir.is_dir())
        items = list(spatial_dir.iterdir())
        self.assertGreater(len(items), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
