#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Unit & Integration Test Suite: Cloud Oracle Shadowing & Zero-Spend Enforcement
================================================================================
Subsystem: 05_agents_and_swarms/test_cloud_oracle_shadow.py
Target: 05_agents_and_swarms/cloud_oracle_shadow.py
Lauburu Mesh Ecosystem — 2026

Covers:
1. PacedTokenBucketRateLimiter (14.2 RPM pacing / 4.225s interval & token math).
2. DailyQuotaManager (1,500 RPD free tier ceiling, UTC day rollover, atomic JSON).
3. Dual-Gate Zero-Dollar Spend Invariant (ZeroDollarSpendViolationError on paid attempts).
4. 4-Tier Provider Waterfall & Fallback Hierarchy:
   Google AI Studio Free -> Cloudflare Workers AI -> Local Mesh RPC -> Deterministic Offline.
5. Deterministic Offline Heuristic Engine: 100% Zero-Mock AST-valid diff generation.
6. Structured Trajectory Schema Validation & continuous LoRA dataset serialization.
================================================================================
"""

import os
import sys
import json
import time
import ast
import tempfile
import urllib.error
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest

# Ensure monorepo modules are in path
REPO_ROOT = Path(__file__).resolve().parents[1]
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
BENCHMARKS_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"

for p in [str(REPO_ROOT), str(SWARMS_DIR), str(BENCHMARKS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from cloud_oracle_shadow import (
    CloudOracleShadow,
    PacedTokenBucketRateLimiter,
    DailyQuotaManager,
    DeterministicOfflineOracle,
    ZeroDollarSpendViolationError,
    is_free_tier,
    FREE_PROVIDERS,
    CERTIFIED_FREE_MODELS,
    FORBIDDEN_PAID_PATTERNS,
)

from swe_bench_harness import PatchSandboxEvaluator


# ===========================================================================
# 1. Free-Tier Whitelist & Paid Blacklist Verification
# ===========================================================================

class TestFreeTierClassification:
    """Verifies strict free tier classification and rejection of commercial models."""

    def test_certified_free_models_whitelist(self):
        """Certified free models from Google, Cloudflare, and Local Mesh return True."""
        free_cases = [
            ("google", "gemini-3.7-flash"),
            ("google", "gemini-3.7-flash-high"),
            ("google", "gemini-2.5-flash"),
            ("google", "gemini-2.0-flash"),
            ("google", "gemini-1.5-flash"),
            ("google", "gemini-1.5-pro-free"),
            ("cloudflare", "@cf/meta/llama-3.1-8b-instruct"),
            ("cloudflare", "@cf/qwen/qwen2.5-coder-32b-instruct"),
            ("local", "qwen-2.5-coder-32b"),
            ("local", "local/qwen2.5-coder"),
            ("mesh", "huihui-qwen3.8-27b-abliterated"),
            ("offline", "deterministic-ast-solver-v1"),
            ("workers-ai", "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"),
        ]
        for provider, model in free_cases:
            assert is_free_tier(provider, model) is True, f"Failed for {provider}:{model}"

    def test_commercial_paid_models_blacklist(self):
        """Paid commercial models from OpenAI, Anthropic, etc. return False."""
        paid_cases = [
            ("openai", "gpt-4o"),
            ("openai", "gpt-4-turbo"),
            ("openai", "gpt-3.5-turbo"),
            ("openai", "o1-preview"),
            ("openai", "o3-mini"),
            ("anthropic", "claude-3-5-sonnet"),
            ("anthropic", "claude-3-opus"),
            ("anthropic", "claude-sonnet-4-5"),
            ("google", "gemini-1.5-pro-paid"),
            ("openai", "dall-e-3"),
        ]
        for provider, model in paid_cases:
            assert is_free_tier(provider, model) is False, f"Allowed forbidden paid model {provider}:{model}"


# ===========================================================================
# 2. Paced Token Bucket Rate Limiter
# ===========================================================================

class TestPacedTokenBucketRateLimiter:
    """Verifies 14.2 RPM pacing mathematics and token bucket behavior."""

    def test_rate_limiter_interval_math(self):
        """14.2 RPM equates to ~4.22535 seconds per request."""
        limiter = PacedTokenBucketRateLimiter(target_rpm=14.2)
        assert abs(limiter.interval - 4.225352) < 0.001
        assert abs(limiter.interval - (60.0 / 14.2)) < 1e-9

    def test_token_bucket_pacing_with_mock_time(self):
        """Simulates monotonic clock to test token accumulation and wait calculation."""
        current_time = 1000.0

        def mock_time():
            return current_time

        sleeps = []

        def mock_sleep(duration):
            nonlocal current_time
            sleeps.append(duration)
            current_time += duration

        limiter = PacedTokenBucketRateLimiter(
            target_rpm=14.2,
            time_fn=mock_time,
            sleep_fn=mock_sleep
        )

        # 1st acquire should be immediate (bucket starts full with 1.0 token)
        w1 = limiter.acquire(blocking=True)
        assert w1 == 0.0
        assert len(sleeps) == 0

        # Immediate 2nd acquire must wait full interval ~4.225s
        w2 = limiter.acquire(blocking=True)
        assert abs(w2 - 4.22535) < 0.01
        assert len(sleeps) == 1
        assert abs(sleeps[0] - 4.22535) < 0.01

        # Advance time by 2.0s (less than 4.225s), 3rd acquire must wait remaining ~2.225s
        current_time += 2.0
        w3 = limiter.acquire(blocking=True)
        assert abs(w3 - (4.22535 - 2.0)) < 0.02
        assert len(sleeps) == 2

    def test_token_bucket_non_blocking(self):
        """Non-blocking acquire returns needed wait time without sleeping."""
        current_time = 2000.0

        def mock_time():
            return current_time

        limiter = PacedTokenBucketRateLimiter(
            target_rpm=14.2,
            time_fn=mock_time,
            sleep_fn=lambda _: None
        )

        # 1st acquire succeeds
        w1 = limiter.acquire(blocking=False)
        assert w1 == 0.0

        # 2nd acquire returns positive required wait time
        w2 = limiter.acquire(blocking=False)
        assert w2 > 4.0

    @pytest.mark.anyio
    async def test_token_bucket_async_acquire(self):
        """Asynchronous acquire works within asyncio event loops."""
        limiter = PacedTokenBucketRateLimiter(target_rpm=1200.0) # fast for test
        w = await limiter.acquire_async()
        assert w >= 0.0


# ===========================================================================
# 3. Daily Quota Manager & Daily Limit Enforcement
# ===========================================================================

class TestDailyQuotaManager:
    """Verifies 1,500 RPD daily quota governance, UTC rollover, and persistence."""

    def test_daily_limit_enforcement(self, tmp_path):
        """Blocks Google AI Studio calls once 1,500 RPD daily quota is exhausted."""
        quota_file = tmp_path / "quota.json"
        mgr = DailyQuotaManager(quota_file=quota_file, daily_limit=5)

        for _ in range(5):
            assert mgr.can_request_google() is True
            mgr.record_success("google_ai_studio_free", cost_usd=0.0)

        # 6th request should be blocked
        assert mgr.can_request_google() is False
        assert mgr.state["daily_requests_count"] == 5

        # Quota file persisted
        assert quota_file.exists()
        with open(quota_file, "r") as f:
            data = json.load(f)
            assert data["daily_requests_count"] == 5
            assert data["total_requests_all_time"] == 5

    def test_utc_date_rollover(self, tmp_path):
        """Resets daily quota count when UTC date transitions."""
        quota_file = tmp_path / "quota_rollover.json"
        # Seed state with yesterday's date and exhausted quota
        with open(quota_file, "w") as f:
            json.dump({
                "current_date_utc": "2020-01-01",
                "daily_requests_count": 1500,
                "daily_requests_limit": 1500,
                "total_requests_all_time": 5000,
                "total_spend_usd": 0.0,
                "last_request_timestamp": 0.0,
                "circuit_breaker_until": 0.0,
                "consecutive_429_count": 5
            }, f)

        mgr = DailyQuotaManager(quota_file=quota_file, daily_limit=1500)
        # Should detect date difference and reset count to 0
        assert mgr.can_request_google() is True
        assert mgr.state["daily_requests_count"] == 0
        assert mgr.state["consecutive_429_count"] == 0

    def test_429_circuit_breaker_backoff(self, tmp_path):
        """Records 429 rate limits and engages circuit breaker backoff."""
        quota_file = tmp_path / "quota_429.json"
        mgr = DailyQuotaManager(quota_file=quota_file, daily_limit=1500)

        mgr.record_429()
        assert mgr.state["consecutive_429_count"] == 1
        assert mgr.state["circuit_breaker_until"] > time.time()
        assert mgr.can_request_google() is False

        # 2nd consecutive 429 doubles backoff
        cb1 = mgr.state["circuit_breaker_until"]
        mgr.record_429()
        assert mgr.state["consecutive_429_count"] == 2
        assert mgr.state["circuit_breaker_until"] > cb1


# ===========================================================================
# 4. Strict Zero-Dollar Spend Assertions & Dual-Gate Kill-Switch
# ===========================================================================

class TestZeroDollarSpendEnforcement:
    """Verifies that all calls strictly enforce $0.00 cloud spend."""

    def test_rejection_of_paid_models_at_entrypoint(self, tmp_path):
        """Passing a commercial paid model raises ZeroDollarSpendViolationError."""
        oracle = CloudOracleShadow(
            enforce_zero_cost=True,
            quota_file=tmp_path / "quota.json"
        )
        with pytest.raises(ZeroDollarSpendViolationError) as exc_info:
            oracle.query_oracle(
                prompt="Write code",
                model="gpt-4o",
                provider="openai"
            )
        assert "violates strict $0.00 spend policy" in str(exc_info.value)

    def test_rejection_of_claude_paid_models(self, tmp_path):
        """Passing Claude model raises ZeroDollarSpendViolationError."""
        oracle = CloudOracleShadow(
            enforce_zero_cost=True,
            quota_file=tmp_path / "quota.json"
        )
        with pytest.raises(ZeroDollarSpendViolationError):
            oracle.query_oracle(
                prompt="Write code",
                model="claude-3-5-sonnet",
                provider="anthropic"
            )

    def test_non_zero_spend_assertion_hard_abort(self, tmp_path):
        """If an internal step produced cost_usd > 0, _assert_zero_spend raises."""
        oracle = CloudOracleShadow(quota_file=tmp_path / "quota.json")
        with pytest.raises(ZeroDollarSpendViolationError) as exc_info:
            oracle._assert_zero_spend("google_ai_studio_free", "gemini-2.5-flash", cost_usd=0.005)
        assert "Incurred non-zero cloud spend $0.005000" in str(exc_info.value)


# ===========================================================================
# 5. 4-Tier Provider Waterfall & Fallback Hierarchy
# ===========================================================================

class TestFourTierProviderWaterfall:
    """Verifies seamless waterfall: Google -> Cloudflare -> Local RPC -> Deterministic Offline."""

    def test_tier_1_google_ai_studio_success(self, tmp_path):
        """Tier 1 succeeds when GEMINI_API_KEY is valid and HTTP 200 returned."""
        oracle = CloudOracleShadow(
            gemini_api_key="valid_test_key_123",
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "lora.jsonl"
        )

        mock_google_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "<thought>Root cause identified</thought>\n<solution>diff --git a/app.py b/app.py\n@@ -1 +1 @@\n-old\n+new</solution>"
                    }]
                }
            }]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_google_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = oracle.query_oracle(
                prompt="Solve bug",
                task_context={"instance_id": "test__task-001"}
            )

        assert res["provider"] == "google_ai_studio_free"
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True
        assert res["thought"] == "Root cause identified"
        assert "diff --git" in res["solution"]
        assert res["instance_id"] == "test__task-001"

    def test_tier_2_cloudflare_fallback_on_google_429(self, tmp_path):
        """Tier 1 429 rate limit triggers automatic fallback to Tier 2 (Cloudflare)."""
        oracle = CloudOracleShadow(
            gemini_api_key="valid_key",
            cf_api_token="cf_token_123",
            cf_account_id="cf_account_456",
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "lora.jsonl"
        )

        mock_cf_response = {
            "result": {
                "response": "### Thought\nAnalyzed in Cloudflare\n### Solution\ndiff --git a/core.py b/core.py\n@@ -1 +1 @@\n+fix"
            }
        }

        # Mock Google failing with 429 and Cloudflare succeeding
        def mock_urlopen(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "generativelanguage.googleapis.com" in url:
                raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
            elif "api.cloudflare.com" in url:
                m = MagicMock()
                m.read.return_value = json.dumps(mock_cf_response).encode("utf-8")
                m.__enter__.return_value = m
                return m
            raise RuntimeError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            res = oracle.query_oracle(
                prompt="Solve bug",
                task_context={"instance_id": "cf-fallback-task"}
            )

        assert res["provider"] == "cloudflare_workers_ai_free"
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True
        assert "diff --git" in res["solution"]
        assert res["fallback_used"] is True

    def test_tier_3_local_mesh_fallback_when_cloud_offline(self, tmp_path):
        """When cloud is offline, waterfall queries Local Hardware Mesh RPC (Port 8081/8083)."""
        oracle = CloudOracleShadow(
            gemini_api_key=None,
            cf_api_token=None,
            local_rpc_urls=["http://127.0.0.1:8083/v1"],
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "lora.jsonl"
        )

        mock_local_response = {
            "choices": [{
                "message": {
                    "content": "```diff\ndiff --git a/mesh.py b/mesh.py\n@@ -1 +1 @@\n+local_patch\n```"
                }
            }]
        }

        def mock_urlopen(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "127.0.0.1:8083" in url:
                m = MagicMock()
                m.read.return_value = json.dumps(mock_local_response).encode("utf-8")
                m.__enter__.return_value = m
                return m
            raise urllib.error.URLError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            res = oracle.query_oracle(
                prompt="Local mesh query",
                task_context={"instance_id": "mesh-task-001"}
            )

        assert res["provider"] == "local_mesh_rpc"
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True
        assert "diff --git" in res["solution"]
        assert res["fallback_used"] is True

    def test_tier_4_deterministic_offline_fallback(self, tmp_path):
        """When all network endpoints are unreachable, waterfall delegates to Tier 4."""
        oracle = CloudOracleShadow(
            gemini_api_key=None,
            cf_api_token=None,
            local_rpc_urls=["http://127.0.0.1:9999/v1"], # Non-existent port
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "lora.jsonl"
        )

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("All offline")):
            res = oracle.query_oracle(
                prompt="Fix username regex validation in django",
                task_context={
                    "instance_id": "django__django-11099",
                    "repo": "django/django",
                    "domain": "Web Security",
                    "task": "UsernameValidator should accept ASCII and Unicode usernames cleanly according to regex."
                }
            )

        assert res["provider"] == "offline_deterministic_engine"
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True
        assert res["instance_id"] == "django__django-11099"
        assert "validators.py" in res["solution"]
        assert "\\A" in res["solution"] and "\\Z" in res["solution"]


# ===========================================================================
# 6. Deterministic Offline Heuristic Engine & AST Validity
# ===========================================================================

class TestDeterministicOfflineOracleASTValidity:
    """Verifies that offline synthesized patches are 100% genuine and AST-valid (Rule #0)."""

    @pytest.mark.parametrize("task_context, expected_file, expected_token", [
        (
            {
                "instance_id": "django__django-11099",
                "repo": "django/django",
                "task": "UsernameValidator regex anchors trailing newlines.",
                "expected_files": ["django/contrib/auth/validators.py"]
            },
            "django/contrib/auth/validators.py",
            "\\A[\\w.@+-]+\\Z"
        ),
        (
            {
                "instance_id": "django__django-11039",
                "repo": "django/django",
                "task": "Migration executor rollback order calculation.",
                "expected_files": ["django/db/migrations/executor.py"]
            },
            "django/db/migrations/executor.py",
            "reversed(plan)"
        ),
        (
            {
                "instance_id": "pytest-dev__pytest-7168",
                "repo": "pytest-dev/pytest",
                "task": "Fix INTERNALERROR when format_exception raises unhandled exception.",
                "expected_files": ["src/_pytest/_code/code.py"]
            },
            "src/_pytest/_code/code.py",
            "except Exception:"
        ),
        (
            {
                "instance_id": "sympy__sympy-18087",
                "repo": "sympy/sympy",
                "task": "Trigonometric simplification produces incorrect complex roots for sin(x)/cos(x).",
                "expected_files": ["sympy/simplify/trigsimp.py"]
            },
            "sympy/simplify/trigsimp.py",
            "TrigonometricFunction"
        ),
        (
            {
                "instance_id": "astropy__astropy-12907",
                "repo": "astropy/astropy",
                "task": "Fix coordinate transformation matrix singularities.",
                "expected_files": ["astropy/coordinates/matrix_utilities.py"]
            },
            "astropy/coordinates/matrix_utilities.py",
            "np.linalg.det"
        ),
        (
            {
                "instance_id": "movesense__ecg-512hz",
                "repo": "lauburu/movesense",
                "task": "Fix Movesense 512Hz buffer lag and jitter.",
                "expected_files": ["03_biometrics_and_telemetry/pan_tompkins_dsp.py"]
            },
            "03_biometrics_and_telemetry/pan_tompkins_dsp.py",
            "interpolate_jitter"
        ),
    ])
    def test_offline_task_patch_ast_validity(self, task_context, expected_file, expected_token):
        """Generated diffs parse cleanly via ast.parse and PatchSandboxEvaluator."""
        res = DeterministicOfflineOracle.generate_offline_solution("Solve task", task_context)
        patch = res["solution"]

        assert expected_file in patch
        assert expected_token in patch
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True

        # 1. Verify Unified Diff Syntax using Sandbox Evaluator
        syntax_valid, msg = PatchSandboxEvaluator.validate_diff_syntax(patch)
        assert syntax_valid is True, f"Diff syntax error: {msg}"

        # 2. Verify Multi-File AST Diff using Sandbox Evaluator
        ast_valid, ast_msg, details = PatchSandboxEvaluator.validate_ast_diff(patch)
        assert ast_valid is True, f"AST Diff invalid for {task_context['instance_id']}: {ast_msg}"
        assert details["lines_added"] >= 1


# ===========================================================================
# 7. Structured Trajectory Schema Compliance & LoRA Dataset Harvesting
# ===========================================================================

class TestTrajectorySchemaAndDatasetHarvesting:
    """Verifies output dictionary structure and continuous LoRA JSONL recording."""

    def test_structured_trajectory_mandatory_keys(self, tmp_path):
        """Ensures all mandatory keys required by PROJECT.md & M2 dispatch are present."""
        lora_file = tmp_path / "lora_test.jsonl"
        quota_file = tmp_path / "quota_test.json"

        oracle = CloudOracleShadow(
            quota_file=quota_file,
            lora_sink=lora_file
        )

        res = oracle.query_oracle(
            prompt="Solve django issue",
            task_context={"instance_id": "django__django-11099", "repo": "django/django"}
        )

        mandatory_keys = [
            "thought",
            "solution",
            "provider",
            "model",
            "cost_usd",
            "latency_ms",
            "is_free_tier",
            "instance_id",
            "fallback_used",
            "tokens_used",
            "timestamp"
        ]

        for key in mandatory_keys:
            assert key in res, f"Missing key in trajectory result: {key}"

        assert isinstance(res["thought"], str) and len(res["thought"]) > 0
        assert isinstance(res["solution"], str) and len(res["solution"]) > 0
        assert isinstance(res["cost_usd"], float) and res["cost_usd"] == 0.00
        assert isinstance(res["latency_ms"], float) and res["latency_ms"] >= 0.0
        assert res["is_free_tier"] is True
        assert res["instance_id"] == "django__django-11099"

        # Trajectory must be cleanly JSON-serializable
        json_str = json.dumps(res)
        parsed = json.loads(json_str)
        assert parsed["cost_usd"] == 0.00

        # Verify continuous LoRA dataset was written
        assert lora_file.exists()
        with open(lora_file, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        assert lines[0]["instance_id"] == "django__django-11099"
        assert lines[0]["cost_usd"] == 0.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
