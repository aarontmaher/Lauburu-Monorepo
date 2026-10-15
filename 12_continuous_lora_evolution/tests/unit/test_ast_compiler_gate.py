"""
Unit tests for AST Compiler Gate & Rule #0 Zero-Mock Validator (F10).
"""

import os
import tempfile
import unittest

from src.distillation.ast_compiler_gate import ASTCompilerGate


class TestASTCompilerGate(unittest.TestCase):

    def test_valid_python_code(self):
        code = """
def compute_moving_average(signal: list[float], window_size: int = 5) -> list[float]:
    result = []
    for i in range(len(signal) - window_size + 1):
        window = signal[i : i + window_size]
        result.append(sum(window) / float(window_size))
    return result
"""
        is_valid, reason = ASTCompilerGate.validate_code_snippet(code)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "VALID_AST")

    def test_syntax_error_detection(self):
        bad_code = """
def broken_syntax(
    x = [1, 2, 3
    return x
"""
        is_valid, reason = ASTCompilerGate.validate_code_snippet(bad_code)
        self.assertFalse(is_valid)
        self.assertIn("SYNTAX_ERROR", reason)

    def test_diff_patch_handling(self):
        diff_code = """
 def process_batch(items):
-    items = items[:10]
+    items = items[:20]
     return len(items)
"""
        is_valid, reason = ASTCompilerGate.validate_code_snippet(diff_code)
        self.assertTrue(is_valid)

    def test_rule_0_mock_data_patterns(self):
        mock_snippets = [
            "mock_data = {'id': 1, 'name': 'test'}",
            "from unittest.mock import MagicMock\nm = MagicMock()",
            "import unittest.mock\nm = unittest.mock.Mock()",
            "fake_ecg = [0.1, 0.2, 0.3, 0.4]",
            "def test():\n    simulate_telemetry(port=8080)",
            "dummy_payload = {'status': 'ok'}",
            "from pytest.mock import mocker",
        ]

        for snippet in mock_snippets:
            is_valid, reason = ASTCompilerGate.validate_code_snippet(snippet)
            self.assertFalse(is_valid, f"Snippet should have failed Rule #0: {snippet}")
            self.assertIn("RULE_0_MOCK_DETECTED", reason)

    def test_rule_0_empty_stub_detection(self):
        stub_snippets = [
            "def restart_router():\n    pass",
            "def calculate_metrics():\n    '''Compute metrics.'''\n    pass",
            "def send_packet():\n    ...",
        ]

        for snippet in stub_snippets:
            is_valid, reason = ASTCompilerGate.validate_code_snippet(snippet)
            self.assertFalse(is_valid, f"Stub should have failed: {snippet}")
            self.assertIn("RULE_0_EMPTY_STUB", reason)

    def test_validate_record_with_markdown(self):
        record_good = {
            "instruction": "Write a Python function to clamp values.",
            "output": """Here is the implementation:
```python
def clamp_value(val: float, min_val: float, max_val: float) -> float:
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val
```
It handles edge boundaries.""",
        }
        is_valid, reason = ASTCompilerGate.validate_record(record_good)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "ALL_BLOCKS_VALID")

        record_bad = {
            "instruction": "Generate fake telemetry.",
            "output": """```python
def get_stream():
    return simulate_telemetry()
```""",
        }
        is_valid, reason = ASTCompilerGate.validate_record(record_bad)
        self.assertFalse(is_valid)
        self.assertIn("RULE_0_MOCK_DETECTED", reason)

    def test_filter_and_quarantine(self):
        records = [
            {"id": "r1", "output": "```python\ndef add(a, b):\n    return a + b\n```"},
            {"id": "r2", "output": "```python\nfake_ecg = [1, 2, 3]\n```"},
            {"id": "r3", "output": "Pure text with no code."},
        ]

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            valid, quarantined = ASTCompilerGate.filter_and_quarantine(
                records, quarantine_path=tmp_path
            )
            self.assertEqual(len(valid), 2)
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0]["id"], "r2")
            self.assertIn("RULE_0_MOCK_DETECTED", quarantined[0]["_quarantine_reason"])

            # Verify file was written
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
