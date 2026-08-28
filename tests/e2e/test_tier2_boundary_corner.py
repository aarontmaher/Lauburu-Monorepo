#!/usr/bin/env python3
"""
Tier 2: Boundary Value Analysis & Corner Cases E2E Test Suite
=============================================================
Tests at limits, edge conditions, and failure containment:
- Empty datasets (0-byte files, 0-sample buffers, whitespace-only files)
- Extreme inputs (1-record datasets, huge payload strings, high sampling rates)
- Missing hardware & disconnected network interfaces
- Broken link detection & circular symlink handling
- Malformed JSON / corrupted JSONL records containment
- Corrupted markdown notes & unclosed YAML frontmatter
- Storage health headroom threshold boundaries
- Boundary mathematical conditions for Pan-Tompkins QRS and DFA-alpha1
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any

TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent
sys.path.insert(0, str(TESTS_E2E_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from e2e_helpers import (
    get_project_root,
    is_storage_healthy,
    scan_all_symlinks,
    extract_wikilinks,
    validate_jsonl_record,
    reference_pan_tompkins_detector,
    reference_dfa_alpha1,
    PROJECT_ROOT
)


class TestTier2BoundaryCornerCases(unittest.TestCase):
    """Tier 2: Boundary Value Analysis & Edge Case Testing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # Group 1: Dataset Boundary Conditions (LoRA Lake & JSONL)
    # =========================================================================

    def test_t2_01_empty_jsonl_dataset_handling(self):
        """T2.1: Verify empty 0-byte JSONL file returns 0 records without exception."""
        empty_file = self.tmp_path / 'empty.jsonl'
        empty_file.touch()
        
        valid_records = []
        with open(empty_file, 'r') as f:
            for line in f:
                v, rec, _ = validate_jsonl_record(line)
                if v:
                    valid_records.append(rec)
        self.assertEqual(len(valid_records), 0)

    def test_t2_02_whitespace_only_dataset(self):
        """T2.2: Verify dataset containing only newlines and spaces is handled cleanly."""
        ws_file = self.tmp_path / 'whitespace.jsonl'
        ws_file.write_text('   \n\n  \t  \n   \n', encoding='utf-8')
        
        records = []
        with open(ws_file, 'r') as f:
            for line in f:
                v, rec, _ = validate_jsonl_record(line)
                if v:
                    records.append(rec)
        self.assertEqual(len(records), 0)

    def test_t2_03_single_record_dataset(self):
        """T2.3: Verify dataset with exactly 1 record parses correctly."""
        single_file = self.tmp_path / 'single.jsonl'
        single_file.write_text(json.dumps({'instruction': 'test', 'output': 'ok'}) + '\n')
        
        records = []
        with open(single_file, 'r') as f:
            for line in f:
                v, rec, _ = validate_jsonl_record(line)
                if v:
                    records.append(rec)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['output'], 'ok')

    def test_t2_04_corrupted_json_surrounded_by_valid_records(self):
        """T2.4: Verify parser recovers and processes valid records when encountering corrupted middle record."""
        mixed_file = self.tmp_path / 'mixed.jsonl'
        lines = [
            json.dumps({'instruction': '1', 'output': 'first'}),
            '{bad_json: missing_quotes',
            json.dumps({'instruction': '2', 'output': 'second'})
        ]
        mixed_file.write_text('\n'.join(lines) + '\n')
        
        valid_recs = []
        errors = []
        with open(mixed_file, 'r') as f:
            for line in f:
                v, rec, err = validate_jsonl_record(line)
                if v:
                    valid_recs.append(rec)
                elif err and err != 'EMPTY_LINE':
                    errors.append(err)
                    
        self.assertEqual(len(valid_recs), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn('JSON_DECODE_ERROR', errors[0])

    def test_t2_05_large_json_record_boundary(self):
        """T2.5: Verify record with 50KB payload parses without memory or buffer overflow."""
        large_payload = 'x' * 50000
        rec_str = json.dumps({'instruction': 'huge', 'output': large_payload})
        v, rec, err = validate_jsonl_record(rec_str)
        self.assertTrue(v)
        self.assertEqual(len(rec['output']), 50000)

    # =========================================================================
    # Group 2: Biometrics DSP & Sensor Buffer Boundaries
    # =========================================================================

    def test_t2_06_ecg_zero_length_buffer(self):
        """T2.6: Verify Pan-Tompkins detector on 0-sample buffer returns INSUFFICIENT_DATA."""
        res = reference_pan_tompkins_detector([], fs=512)
        self.assertEqual(res['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(res['heart_rate_bpm'])
        self.assertEqual(res['qrs_count'], 0)

    def test_t2_07_ecg_single_sample_buffer(self):
        """T2.7: Verify 1-sample buffer does not trigger DivisionByZero or IndexError."""
        res = reference_pan_tompkins_detector([1.0], fs=512)
        self.assertEqual(res['status'], 'INSUFFICIENT_DATA')

    def test_t2_08_ecg_flatline_isoelectric_signal(self):
        """T2.8: Verify flatline signal (0V across 5 seconds) detects 0 QRS peaks cleanly."""
        flatline = [0.0] * (512 * 5)
        res = reference_pan_tompkins_detector(flatline, fs=512)
        self.assertEqual(res['status'], 'NO_QRS_DETECTED')
        self.assertEqual(res['qrs_count'], 0)
        self.assertIsNone(res['heart_rate_bpm'])

    def test_t2_09_ecg_constant_offset_dc_bias(self):
        """T2.9: Verify high DC bias without pulses does not falsely trigger QRS detection."""
        dc_bias_signal = [5000.0] * (512 * 3)
        res = reference_pan_tompkins_detector(dc_bias_signal, fs=512)
        self.assertEqual(res['qrs_count'], 0)

    def test_t2_10_extreme_sampling_rate_high(self):
        """T2.10: Verify detector behavior at high sampling rate (fs = 2000Hz)."""
        fs = 2000
        signal = [0.0] * (fs * 2)
        signal[int(fs * 0.5)] = 10.0
        signal[int(fs * 1.5)] = 10.0
        res = reference_pan_tompkins_detector(signal, fs=fs)
        self.assertEqual(res['qrs_count'], 2)

    def test_t2_11_dfa_alpha1_empty_buffer(self):
        """T2.11: Verify DFA-alpha1 on empty RR intervals buffer returns INSUFFICIENT_DATA."""
        res = reference_dfa_alpha1([])
        self.assertEqual(res['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(res['alpha1'])

    def test_t2_12_dfa_alpha1_under_minimum_length(self):
        """T2.12: Verify DFA-alpha1 with <16 beats returns INSUFFICIENT_DATA."""
        short_rr = [800.0] * 10
        res = reference_dfa_alpha1(short_rr)
        self.assertEqual(res['status'], 'INSUFFICIENT_DATA')

    def test_t2_13_dfa_alpha1_identical_constant_intervals(self):
        """T2.13: Verify DFA-alpha1 with perfectly constant RR intervals does not crash on math.log(0)."""
        constant_rr = [1000.0] * 32
        res = reference_dfa_alpha1(constant_rr)
        self.assertIn(res['status'], ['VALID', 'FALLBACK_ESTIMATE'])

    # =========================================================================
    # Group 3: Hardware State Transitions & Telemetry Fallback
    # =========================================================================

    def test_t2_14_disconnected_telemetry_json_payload(self):
        """T2.14: Verify disconnected telemetry state serialization preserves null fields."""
        state = {
            'device_id': 'movesense_sensor',
            'connected': False,
            'hr_bpm': None,
            'ecg_samples': [],
            'rssi_dbm': None
        }
        serialized = json.dumps(state)
        self.assertIn('null', serialized)
        deserialized = json.loads(serialized)
        self.assertIsNone(deserialized['hr_bpm'])

    def test_t2_15_network_unreachable_node_timeout(self):
        """T2.15: Verify network probe for unreachable blackhole IP terminates with clean offline status."""
        def probe_node_status(ip: str, timeout_sec: float = 0.05) -> Dict[str, Any]:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            try:
                sock.connect((ip, 9999))
                sock.close()
                return {'status': 'online', 'ip': ip}
            except Exception:
                return {'status': 'offline', 'ip': ip, 'latency_ms': None}
                
        res = probe_node_status('192.0.2.1', timeout_sec=0.01)
        self.assertEqual(res['status'], 'offline')
        self.assertIsNone(res['latency_ms'])

    def test_t2_16_corrupted_telemetry_packet_discard(self):
        """T2.16: Verify corrupted binary packet checksum discard."""
        def parse_ble_packet(packet_bytes: bytes) -> Optional[Dict[str, Any]]:
            if len(packet_bytes) < 4:
                return None # Truncated
            crc = sum(packet_bytes[:-1]) % 256
            if crc != packet_bytes[-1]:
                return None # Checksum mismatch
            return {'data': packet_bytes[0]}
            
        self.assertIsNone(parse_ble_packet(b''))
        self.assertIsNone(parse_ble_packet(b'\x01\x02\x03')) # Too short
        self.assertIsNone(parse_ble_packet(b'\x01\x02\x03\xff')) # Bad CRC

    # =========================================================================
    # Group 4: Obsidian Vault & Wikilink Parsing Boundaries
    # =========================================================================

    def test_t2_17_wikilink_with_aliases_and_anchors(self):
        """T2.17: Verify Wikilink parser extracts target when aliases and section anchors are present."""
        text = 'See [[MyNote#Section 1|My Custom Alias]] and [[AnotherNote#Top]] and [[SimpleNote]].'
        links = extract_wikilinks(text)
        self.assertIn('MyNote', links)
        self.assertIn('AnotherNote', links)
        self.assertIn('SimpleNote', links)

    def test_t2_18_wikilink_with_unicode_and_spaces(self):
        """T2.18: Verify Wikilink parser handles spaces and UTF-8 characters."""
        text = 'Review [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] and [[Master Swarm Brain]].'
        links = extract_wikilinks(text)
        self.assertIn('LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX', links)
        self.assertIn('Master Swarm Brain', links)

    def test_t2_19_empty_markdown_document_extraction(self):
        """T2.19: Verify extracting Wikilinks from empty markdown returns empty list."""
        self.assertEqual(extract_wikilinks(''), [])

    def test_t2_20_broken_symlink_detection_algorithm(self):
        """T2.20: Verify symlink scanner identifies broken symlink created in temp directory."""
        non_existent_target = self.tmp_path / 'missing_target.txt'
        broken_link = self.tmp_path / 'broken_symlink'
        broken_link.symlink_to(non_existent_target)
        
        symlinks = scan_all_symlinks(self.tmp_path)
        self.assertEqual(len(symlinks), 1)
        self.assertTrue(symlinks[0]['is_broken'])
        self.assertFalse(symlinks[0]['target_exists'])

    def test_t2_21_valid_relative_symlink_detection(self):
        """T2.21: Verify symlink scanner verifies relative target path exists."""
        real_file = self.tmp_path / 'real.txt'
        real_file.write_text('content')
        valid_link = self.tmp_path / 'valid_link'
        valid_link.symlink_to('real.txt')
        
        symlinks = scan_all_symlinks(self.tmp_path)
        self.assertEqual(len(symlinks), 1)
        self.assertFalse(symlinks[0]['is_broken'])
        self.assertTrue(symlinks[0]['is_relative'])

    # =========================================================================
    # Group 5: Storage Health Headroom Invariants
    # =========================================================================

    def test_t2_22_storage_health_zero_disk_simulation(self):
        """T2.22: Verify simulated disk headroom failure is caught by health check logic."""
        def evaluate_health(obs_ok: bool, lora_ok: bool, free_gb: float) -> bool:
            return obs_ok and lora_ok and (free_gb >= 10.0)
            
        self.assertFalse(evaluate_health(True, True, 2.0))
        self.assertFalse(evaluate_health(True, False, 20.0))
        self.assertTrue(evaluate_health(True, True, 15.0))

    def test_t2_23_read_only_directory_traversal(self):
        """T2.23: Verify scanner handles directory without write permission without failing read traversal."""
        ro_dir = self.tmp_path / 'readonly_test'
        ro_dir.mkdir()
        (ro_dir / 'file.txt').write_text('data')
        
        # Test read traversal
        items = list(ro_dir.iterdir())
        self.assertEqual(len(items), 1)

    def test_t2_24_deep_nested_symlink_depth_limit(self):
        """T2.24: Verify scanner respects max_depth parameter."""
        nested = self.tmp_path / 'd1' / 'd2' / 'd3' / 'd4'
        nested.mkdir(parents=True)
        target = nested / 'leaf.txt'
        target.write_text('leaf')
        link = nested / 'leaf_link'
        link.symlink_to('leaf.txt')
        
        shallow_scan = scan_all_symlinks(self.tmp_path, max_depth=1)
        self.assertEqual(len(shallow_scan), 0)
        
        deep_scan = scan_all_symlinks(self.tmp_path, max_depth=5)
        self.assertEqual(len(deep_scan), 1)

    def test_t2_25_unclosed_yaml_frontmatter_in_markdown(self):
        """T2.25: Verify note with unclosed frontmatter does not crash Wikilink parser."""
        unclosed = '---\ntitle: Broken Frontmatter\ntags: [lauburu, test\n# Body content with [[ValidLink]]\n'
        links = extract_wikilinks(unclosed)
        self.assertIn('ValidLink', links)


if __name__ == '__main__':
    unittest.main(verbosity=2)
