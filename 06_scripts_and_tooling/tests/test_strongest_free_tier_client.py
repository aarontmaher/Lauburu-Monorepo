#!/usr/bin/env python3
"""
Unit tests for Strongest-First Free-Tier Client & Quality Gate
"""

import ast
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

from strongest_free_tier_client import (
    StrongestFreeTierClient,
    QualityGate,
    QualityResult,
    FallbackResponse,
    FREE_TIER_WATERFALL,
)


class TestQualityGate(unittest.TestCase):
    def setUp(self):
        self.gate = QualityGate(min_length=50, expect_code=True, strict_zero_mock=True)

    def test_valid_code_passes(self):
        text = """Here is the Pan-Tompkins derivative filter:
```python
def derivative_filter(x: list[float]) -> list[float]:
    \"\"\"5-point derivative: y[n] = (2*x[n] + x[n-1] - x[n-3] - 2*x[n-4]) / 8\"\"\"
    y = [0.0] * len(x)
    for n in range(4, len(x)):
        y[n] = (2 * x[n] + x[n - 1] - x[n - 3] - 2 * x[n - 4]) / 8.0
    return y
```
This is fully validated for 512Hz ECG streams.
"""
        res = self.gate.evaluate(text)
        self.assertTrue(res.passed)
        self.assertGreaterEqual(res.score, 0.8)
        self.assertTrue(res.code_syntactically_valid)
        self.assertEqual(res.code_blocks_found, 1)

    def test_syntax_error_in_code_fails(self):
        bad_text = """Here is the broken code:
```python
def bad_function(x
    return x * 2
```
This has a broken paren.
"""
        res = self.gate.evaluate(bad_text)
        self.assertFalse(res.passed)
        self.assertFalse(res.code_syntactically_valid)
        self.assertTrue(any("syntax error" in r.lower() for r in res.reasons))

    def test_missing_code_when_expected_fails(self):
        no_code_text = "This is a detailed explanation of ECG without any code blocks at all, which violates expect_code."
        res = self.gate.evaluate(no_code_text)
        self.assertFalse(res.passed)
        self.assertFalse(res.code_syntactically_valid)

    def test_empty_response_fails(self):
        res = self.gate.evaluate("")
        self.assertFalse(res.passed)
        self.assertEqual(res.score, 0.0)

    def test_length_below_threshold_fails(self):
        res = self.gate.evaluate("Short.")
        self.assertFalse(res.passed)
        self.assertTrue(any("Length below threshold" in r for r in res.reasons))

    def test_degenerate_repetition_fails(self):
        repeated_sentence = "The Pan-Tompkins algorithm is an essential algorithm for 512Hz ECG."
        rep_text = f"{repeated_sentence} {repeated_sentence} {repeated_sentence} And some extra text."
        gate_no_code = QualityGate(min_length=50, expect_code=False)
        res = gate_no_code.evaluate(rep_text)
        self.assertFalse(res.passed)
        self.assertTrue(any("repetition" in r.lower() for r in res.reasons))

    def test_rule_zero_mock_prohibition(self):
        mock_text = """Here is the filter:
```python
def qrs_filter(signal):
    # TODO: implement real filtering
    pass  # mock
```
"""
        res = self.gate.evaluate(mock_text)
        self.assertFalse(res.passed)
        self.assertTrue(any("Rule #0 Violation" in r for r in res.reasons))


class TestStrongestFreeTierClient(unittest.TestCase):
    def setUp(self):
        self.mock_cb = MagicMock()
        self.mock_cb.can_call_ai_studio.return_value = (True, "OK")

        self.waterfall = [
            {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash", "tier": 1, "type": "cloud"},
            {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash", "tier": 2, "type": "cloud"},
            {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash", "tier": 3, "type": "cloud"},
            {"id": "qwen_38_max", "name": "Qwen 3.8 Max", "tier": 7, "type": "local", "endpoint": "http://127.0.0.1:8082/v1/chat/completions"},
        ]

        self.client = StrongestFreeTierClient(
            api_key="test-unbilled-key",
            waterfall=self.waterfall,
            min_interval_seconds=0.01,
            circuit_breaker=self.mock_cb,
            enable_local_fallback=True,
        )

    @patch("google.genai.Client")
    def test_tier1_success_no_stepdown(self, mock_genai_cls):
        mock_client = MagicMock()
        mock_genai_cls.return_value = mock_client
        mock_resp = MagicMock(text="Pan-Tompkins QRS detection isolates R-peaks using bandpass filtering and window integration.")
        mock_client.models.generate_content.return_value = mock_resp

        gate = QualityGate(min_length=30, expect_code=False)
        resp = self.client.generate("Explain Pan-Tompkins", quality_gate=gate)

        self.assertTrue(resp.success)
        self.assertEqual(resp.model_used, "gemini-3.8-flash")
        self.assertEqual(resp.model_tier, 1)
        self.assertEqual(len(resp.fallback_path), 1)
        self.assertEqual(resp.fallback_path[0]["status"], "SUCCESS")
        self.assertEqual(resp.cost_usd, 0.00)

    @patch("google.genai.Client")
    def test_waterfall_stepdown_on_503_unavailable(self, mock_genai_cls):
        mock_client = MagicMock()
        mock_genai_cls.return_value = mock_client

        # Tier 1 fails with 503 high demand, Tier 2 succeeds
        def side_effect(model, contents, config):
            if model == "gemini-3.8-flash":
                raise Exception("503 UNAVAILABLE: This model is currently experiencing high demand")
            return MagicMock(text="Gemini 3.7 Flash: High quality biometrics response for 512Hz ECG streams.")

        mock_client.models.generate_content.side_effect = side_effect

        gate = QualityGate(min_length=30, expect_code=False)
        resp = self.client.generate("Explain Pan-Tompkins", quality_gate=gate)

        self.assertTrue(resp.success)
        self.assertEqual(resp.model_used, "gemini-3.7-flash")
        self.assertEqual(resp.model_tier, 2)
        self.assertEqual(len(resp.fallback_path), 2)
        self.assertEqual(resp.fallback_path[0]["status"], "ERROR")
        self.assertIn("503", resp.fallback_path[0]["error"])
        self.assertEqual(resp.fallback_path[1]["status"], "SUCCESS")

    @patch("google.genai.Client")
    def test_waterfall_stepdown_on_quality_gate_failure(self, mock_genai_cls):
        mock_client = MagicMock()
        mock_genai_cls.return_value = mock_client

        # Tier 1 returns broken Python syntax, Tier 2 returns valid Python
        def side_effect(model, contents, config):
            if model == "gemini-3.8-flash":
                return MagicMock(text="```python\ndef bad(: pass\n```")
            return MagicMock(text="Here is valid code:\n```python\ndef good(): return True\n```\nAccurate.")

        mock_client.models.generate_content.side_effect = side_effect

        gate = QualityGate(min_length=30, expect_code=True)
        resp = self.client.generate("Write Python code", quality_gate=gate)

        self.assertTrue(resp.success)
        self.assertEqual(resp.model_used, "gemini-3.7-flash")
        self.assertEqual(resp.model_tier, 2)
        self.assertEqual(resp.fallback_path[0]["status"], "QUALITY_FAILED")
        self.assertEqual(resp.fallback_path[1]["status"], "SUCCESS")

    @patch("urllib.request.urlopen")
    @patch("google.genai.Client")
    def test_local_fallback_when_all_cloud_fail(self, mock_genai_cls, mock_urlopen):
        mock_client = MagicMock()
        mock_genai_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("503 High Demand")

        # Mock local Qwen 3.8 Max on port 8082
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Qwen 3.8 Max sovereign local reasoning for Pan-Tompkins 512Hz ECG."}}]
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        gate = QualityGate(min_length=30, expect_code=False)
        resp = self.client.generate("Explain Pan-Tompkins", quality_gate=gate)

        self.assertTrue(resp.success)
        self.assertEqual(resp.model_used, "qwen_38_max")
        self.assertEqual(resp.model_tier, 7)
        self.assertTrue(resp.is_local)
        self.assertEqual(resp.fallback_path[-1]["status"], "SUCCESS_LOCAL")

    @patch("google.genai.Client")
    def test_domain_routing_multimodal_vla(self, mock_genai_cls):
        mock_client = MagicMock()
        mock_genai_cls.return_value = mock_client
        mock_resp = MagicMock(text="UI Element detected at bounding box [120, 340, 160, 480] with high confidence.")
        mock_client.models.generate_content.return_value = mock_resp

        resp = self.client.generate_vla("Detect UI bounding box on screen")
        self.assertTrue(resp.success)
        self.assertEqual(resp.model_used, "gemini-3.8-flash")
        self.assertEqual(resp.model_tier, 1)

    @patch("google.genai.Client")
    def test_domain_routing_reverse_engineering(self, mock_genai_cls):
        mock_client = MagicMock()
        mock_genai_cls.return_value = mock_client
        mock_resp = MagicMock(text="Disassembly shows ARM64 PAC sign instructions; reconstructed C11 framing header.")
        mock_client.models.generate_content.return_value = mock_resp

        resp = self.client.generate_reverse_engineering("Analyze binary assembly")
        self.assertTrue(resp.success)
        self.assertEqual(resp.model_used, "gemini-3.8-flash")

    def test_prevent_quality_drop_excludes_low_tier_models(self):
        # Client with low tier models
        client_with_lite = StrongestFreeTierClient(
            api_key="test-key",
            waterfall=[
                {"id": "gemini-3.8-flash", "tier": 1, "type": "cloud", "name": "Tier 1"},
                {"id": "gemini-3.5-flash-lite", "tier": 6, "type": "cloud", "name": "Tier 6 Lite"},
                {"id": "qwen_38_max", "tier": 7, "type": "local", "name": "Local"},
            ]
        )
        with patch.object(client_with_lite, "_rate_limit_pace"):
            with patch("google.genai.Client") as mock_cls:
                mock_cls.return_value.models.generate_content.side_effect = Exception("503")
                with patch("urllib.request.urlopen") as mock_url:
                    mock_resp = MagicMock()
                    mock_resp.read.return_value = json.dumps({
                        "choices": [{"message": {"content": "Local reasoning output satisfying length threshold for high-quality response verification."}}]
                    }).encode("utf-8")
                    mock_resp.__enter__.return_value = mock_resp
                    mock_url.return_value = mock_resp

                    # When prevent_quality_drop=True, gemini-3.5-flash-lite should be skipped entirely
                    resp = client_with_lite.generate("Test prompt", prevent_quality_drop=True)
                    attempted_models = [step["model"] for step in resp.fallback_path]
                    self.assertNotIn("gemini-3.5-flash-lite", attempted_models)
                    self.assertEqual(resp.model_used, "qwen_38_max")


if __name__ == "__main__":
    unittest.main()
