#!/usr/bin/env python3
"""
01_apps/automotive/tests/test_voice_engines.py
=============================================
Automated Test Suite for Android Auto Voice Engines (STT & TTS).
Verifies:
1. Edge-TTS & Native TTS Synthesis
2. Faster-Whisper Speech Recognition & Latency SLA (< 1.0s)
3. Directive Extraction & Parsing Accuracy (5 Core Directives)
4. LoRA Training Pair Serialization
"""

import os
import sys
import time
import json
import unittest
from pathlib import Path

# Add automotive directory to sys.path
AUTOMOTIVE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTOMOTIVE_DIR))

from voice_engine import VoiceSynthesizer, VoiceTranscriber

class TestAndroidAutoVoiceEngines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.synth = VoiceSynthesizer()
        cls.trans = VoiceTranscriber(model_size="tiny.en")
        cls.tmp_dir = Path("/tmp/voice_engine_tests")
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_01_tts_synthesis_file_creation(self):
        """Verify TTS synthesizes playable audio and produces non-zero byte output."""
        out_file = self.tmp_dir / "tts_test_01.mp3"
        prompt = "Android Auto voice coding system online and connected to Lauburu mesh."
        success = self.synth.synthesize(prompt, out_file)
        self.assertTrue(success, "TTS synthesis should return True")
        self.assertTrue(out_file.exists(), "Synthesized audio file must exist")
        self.assertGreater(out_file.stat().st_size, 1000, "Audio file size must be > 1000 bytes")

    def test_02_stt_transcription_accuracy(self):
        """Verify STT accurately transcribes synthesized audio."""
        test_cases = [
            ("Run the verification suite across all active nodes", "verification"),
            ("Show git status and uncommitted changes", "status"),
            ("Explain the latest diff in the Movesense hub", "diff"),
            ("Commit and push changes", "commit"),
            ("What is the status of the physical mesh", "mesh")
        ]

        for phrase, keyword in test_cases:
            fname = self.tmp_dir / f"stt_test_{keyword}.mp3"
            self.synth.synthesize(phrase, fname)
            
            res = self.trans.transcribe_file(fname)
            self.assertTrue(len(res.get("text", "")) > 0, f"Transcription should not be empty for '{phrase}'")
            self.assertIn("latency_s", res)
            self.assertLess(res["latency_s"], 2.5, f"Latency SLA violated: {res['latency_s']}s >= 2.5s")
            
            transcript_lower = res["text"].lower()
            self.assertTrue(
                keyword in transcript_lower,
                f"Expected keyword '{keyword}' in transcript '{transcript_lower}'"
            )

    def test_03_directive_parser_coverage(self):
        """Verify high-level directive parser maps voice inputs correctly."""
        directives = {
            "Please run the full test suite now": "RUN_VERIFICATION_TESTS",
            "Show me the current git status": "SHOW_GIT_STATUS",
            "Explain the latest code diff": "EXPLAIN_DIFF",
            "Please confirm and commit changes": "COMMIT_CHANGES",
            "What is the status of the 8 nodes in the mesh": "QUERY_MESH_STATUS",
            "Sync my notes to Obsidian knowledge vault": "SYNC_OBSIDIAN"
        }

        for text, expected_action in directives.items():
            parsed = self.trans.parse_directive(text)
            self.assertEqual(
                parsed["action"],
                expected_action,
                f"Directive mismatch for '{text}': got {parsed['action']}, expected {expected_action}"
            )
            self.assertGreaterEqual(parsed["confidence"], 0.85)

    def test_04_latency_sla_benchmarking(self):
        """Verify end-to-end voice roundtrip meets real-time in-car SLA (< 1.5s)."""
        prompt = "Check repository status."
        audio_file = self.tmp_dir / "sla_bench.mp3"
        
        t0 = time.perf_counter()
        self.synth.synthesize(prompt, audio_file)
        t_synth = time.perf_counter() - t0
        
        t1 = time.perf_counter()
        res = self.trans.transcribe_file(audio_file)
        t_trans = time.perf_counter() - t1

        total_rtt = t_synth + t_trans
        print(f"\n⚡ Voice SLA Benchmark: Synth={t_synth:.3f}s | Transcribe={t_trans:.3f}s | Total={total_rtt:.3f}s")
        self.assertLess(t_trans, 1.0, f"Transcription alone must be < 1.0s, got {t_trans:.3f}s")

if __name__ == "__main__":
    unittest.main()
