#!/usr/bin/env python3
"""
Unit tests for NpuMicroSyntaxValidator (02_ai_models_and_inference)
Compliant with Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), Rule 3 (RAM Sanctuary).
"""

import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from npu_micro_syntax_validator import NpuMicroSyntaxValidator, default_syntax_validator


class TestNpuMicroSyntaxValidator:
    def setup_method(self):
        self.validator = NpuMicroSyntaxValidator()

    def test_valid_python_syntax(self):
        code = "def compute_hash(data: str) -> str:\n    return data.strip().lower()"
        res = self.validator.validate_code(code, "python")
        assert res.is_valid is True
        assert res.bracket_balanced is True
        assert res.error_message is None
        assert res.latency_us < 2000.0  # < 2ms
        assert res.host_ram_mb == 0.0

    def test_invalid_python_syntax(self):
        code = "def broken(data\n    return data"
        res = self.validator.validate_code(code, "python")
        assert res.is_valid is False
        assert res.error_message is not None

    def test_unmatched_bracket_detection(self):
        code = "var_a = [1, 2, 3, (4 + 5]"
        res = self.validator.validate_code(code, "python")
        assert res.is_valid is False
        assert res.bracket_balanced is False
        assert "Mismatched bracket" in res.error_message

    def test_c_rust_brace_validation(self):
        valid_c = "int main() { printf(\"hello\"); return 0; }"
        res_valid = self.validator.validate_code(valid_c, "c")
        assert res_valid.is_valid is True

        invalid_c = "int main() { printf(\"hello\"); return 0; "
        res_invalid = self.validator.validate_code(invalid_c, "c")
        assert res_invalid.is_valid is False

    def test_speed_benchmark(self):
        bench = self.validator.benchmark_token_speed(iterations=50)
        assert bench["tok_per_sec"] > 250.0
        assert bench["host_ram_mb"] == 0.0

    def test_metrics_tracking(self):
        self.validator.validate_code("def a(): pass")
        self.validator.validate_code("def b(: pass")
        metrics = self.validator.get_metrics()
        assert metrics["total_validations"] >= 2
        assert metrics["valid_count"] >= 1
        assert metrics["invalid_count"] >= 1
        assert metrics["host_ram_footprint_mb"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
