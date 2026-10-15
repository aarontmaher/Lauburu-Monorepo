# -*- coding: utf-8 -*-
"""
Adversarial Verification Test Suite for Truth Audit & Zero-Mock Enforcement.
Tests encoding and escaping integrity, invalid input combinations, permission stress,
malformed suppression markers, and corrupt JSONL resilience.
Governed by: PROJECT.md, Rule 0, Rule 1, Rule 5.
"""
from __future__ import annotations

import os
import sys
import stat
import json
import tempfile
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    VERIFY_PROBES_PATH,
    FAKE_DATA_SCANNER_PATH,
    PROHIBITED_LITERALS,
    is_storage_healthy,
    run_cmd,
)

# Import scan_file from fake_data_scanner if available
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/truth"))
try:
    from fake_data_scanner import scan_file  # type: ignore
except ImportError:
    scan_file = None


class TestAdversarialVerification:
    """Adversarial stress and edge condition verification."""

    def test_adversarial_encoding_and_control_chars_in_scanner(self, tmp_path):
        """Verifies that scanner gracefully handles unicode, emojis, control chars, and binary noise."""
        if scan_file is None:
            pytest.skip("fake_data_scanner.py not importable")

        weird_file = tmp_path / "weird_encoding.py"
        weird_content = """# -*- coding: utf-8 -*-
# 🚀 🛰️ 💻 \x00\x01\x02\x03\x04\x1b[31mANSI_RED\x1b[0m
\"\"\"
Multiline docstring with unicode: «τα πάντα ῥεῖ» and emojis 🧠⚡
\"\"\"
def safe_function():
    return "clean_string_without_constants"
"""
        weird_file.write_text(weird_content, encoding="utf-8", errors="replace")

        findings = scan_file(weird_file)
        assert isinstance(findings, list)
        blocks = [f for f in findings if f.get("severity") == "BLOCK"]
        assert len(blocks) == 0, f"Weird encoding triggered unexpected BLOCK findings: {blocks}"

    def test_adversarial_suppression_tag_strictness(self):
        """Verifies that only valid tags ('spec-ok:', 'zero-mock-ok:') suppress BLOCK findings."""
        if scan_file is None:
            pytest.skip("fake_data_scanner.py not importable")

        probe_dir = Path("/tmp/truth_audit_adversarial")
        probe_dir.mkdir(parents=True, exist_ok=True)
        valid_suppressed = probe_dir / "valid_suppressed.py"
        invalid_suppressed = probe_dir / "invalid_suppressed.py"

        try:
            # Valid suppression with colon
            valid_suppressed.write_text("rtt = 0.27  # spec-ok: hardware specification test\n", encoding="utf-8")
            findings_valid = scan_file(valid_suppressed)
            blocks_valid = [f for f in findings_valid if f.get("severity") == "BLOCK"]
            assert len(blocks_valid) == 0, f"Valid suppression tag failed to suppress: {blocks_valid}"

            # Invalid suppression tag (missing colon or typo)
            invalid_suppressed.write_text("rtt = 0.27  # spec_ok without colon or mock_ok\n", encoding="utf-8")
            findings_invalid = scan_file(invalid_suppressed)
            blocks_invalid = [f for f in findings_invalid if f.get("severity") == "BLOCK"]
            assert len(blocks_invalid) >= 1, "Malformed suppression tag should NOT suppress BLOCK violation!"
        finally:
            if valid_suppressed.exists():
                valid_suppressed.unlink()
            if invalid_suppressed.exists():
                invalid_suppressed.unlink()
            shutil_dir = Path("/tmp/truth_audit_adversarial")
            if shutil_dir.exists():
                import shutil
                shutil.rmtree(shutil_dir, ignore_errors=True)

    def test_adversarial_probe_invalid_timeout_argument(self):
        """Verifies that verify_probes.py cleanly rejects non-numeric timeout arguments and unknown flags."""
        if not VERIFY_PROBES_PATH.exists():
            pytest.skip("verify_probes.py not present")

        # Non-numeric timeout (argparse type=float rejection)
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--timeout", "invalid_num"],
            timeout=10.0,
        )
        assert code != 0, "Non-numeric timeout should exit with non-zero error code"
        assert "invalid float value" in stderr or "error" in stderr.lower()

        # Unknown CLI flag rejection
        code2, stdout2, stderr2 = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--unrecognized-bogus-flag-123"],
            timeout=10.0,
        )
        assert code2 != 0, "Unknown flag should exit with non-zero error code"

    def test_adversarial_probe_invalid_output_directory(self):
        """Verifies that verify_probes.py cleanly handles an impossible output directory."""
        if not VERIFY_PROBES_PATH.exists():
            pytest.skip("verify_probes.py not present")

        impossible_path = "/nonexistent_root_dir_998877/invalid_sub/out.json"
        code, stdout, stderr = run_cmd(
            [sys.executable, str(VERIFY_PROBES_PATH), "--json", "--output", impossible_path],
            timeout=10.0,
        )
        assert code != 0, "Writing to impossible directory path must exit with non-zero code"

    def test_adversarial_storage_unwritable_directory(self, tmp_path):
        """Verifies that is_storage_healthy() detects when a storage directory lacks write permission."""
        mock_root = tmp_path / "ro_storage_repo"
        mock_root.mkdir()
        (mock_root / ".git").mkdir()
        (mock_root / "obsidian_vault").mkdir()
        lora_dir = mock_root / "04_data_and_memory"
        lora_dir.mkdir()

        # Valid Index.md
        index_file = mock_root / "obsidian_vault/Index.md"
        index_file.write_text(
            "[[Index]]\n[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
            encoding="utf-8",
        )

        # Baseline: writable
        healthy_baseline, _ = is_storage_healthy(mock_root)
        assert healthy_baseline is True

        # Make 04_data_and_memory read-only (chmod 0555 - read & execute, no write)
        lora_dir.chmod(0o555)
        try:
            healthy_ro, details_ro = is_storage_healthy(mock_root)
            # If lora_dir is not writable, must fail
            if not os.access(str(lora_dir), os.W_OK):
                assert healthy_ro is False, "is_storage_healthy() must fail when storage tier is not writable"
                assert details_ro["lora_writable"] is False
        finally:
            lora_dir.chmod(0o755)

    def test_adversarial_corrupted_jsonl_detection(self, tmp_path):
        """Verifies that corrupted JSONL lines trigger explicit parsing failures."""
        bad_jsonl = tmp_path / "corrupted.jsonl"
        bad_jsonl.write_text(
            '{"valid": true, "sha256": "abc123"}\n'
            '{"corrupted": true, trailing_comma: ,}\n'
            '{"valid_again": true}\n',
            encoding="utf-8",
        )

        lines = bad_jsonl.read_text(encoding="utf-8").splitlines()
        errors = []
        for idx, line in enumerate(lines, 1):
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                errors.append((idx, str(e)))

        assert len(errors) == 1, f"Expected exactly 1 syntax error, found: {errors}"
        assert errors[0][0] == 2, f"Corrupted line should be line 2, got: {errors[0][0]}"
