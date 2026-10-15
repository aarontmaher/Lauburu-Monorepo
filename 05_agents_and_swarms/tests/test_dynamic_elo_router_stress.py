#!/usr/bin/env python3
"""Adversarial Stress Test Suite for Dynamic ELO Router.
Governed by:
- Rule 0: Canonical Hardware & Port Truth
- Rule 1: Zero-Mock & Truth Verification Rule
- Rule 15: Dynamic ELO Default Model Governance

Objectives tested:
1. Valid domain routing ("deep-research", "oss-scout", "reverse-engineering", "screen-lens")
2. Casing and delimiter variants ("DEEP-RESEARCH", "Deep_Research", "oss_scout", etc.)
3. Invalid and boundary inputs ("unknown-domain", "", whitespace, symbols, long strings)
4. CLI format conformance: `[ROUTED] Domain: ... -> Model: ... (Base Public ELO: ...)` and exit code 0
5. LMSYS base public ELO score correspondence with `gemini_free_tier_mapping.json`
6. Microsecond-level empirical timing benchmarks
"""

import sys
import os
import re
import json
import time
import subprocess
from pathlib import Path
import pytest

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent
SWARMS_DIR = TEST_DIR.parent

if str(SWARMS_DIR) not in sys.path:
    sys.path.insert(0, str(SWARMS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dynamic_elo_router import DynamicELORouter

CLI_REGEX = re.compile(
    r"^\[ROUTED\] Domain: (?P<domain>[a-z0-9_-]+) -> Model: (?P<model>[a-z0-9_.:-]+) \(Base Public ELO: (?P<elo>[0-9.]+)(?:, Utility: [0-9.]+)?\)",
    re.MULTILINE
)


@pytest.fixture(scope="module")
def router():
    return DynamicELORouter()


@pytest.fixture(scope="module")
def mapping_data():
    mapping_path = REPO_ROOT / "gemini_free_tier_mapping.json"
    with open(mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestValidDomainRouting:
    """Tests all standard valid domains specified in acceptance criteria."""

    @pytest.mark.parametrize("domain,expected_model,expected_elo", [
        ("deep-research", "gemini-2.5-pro", 1457.0),
        ("oss-scout", "gemini-2.5-flash", 1420.0),
        ("reverse-engineering", "gemini-2.0-flash-thinking-exp-01-21", 1397.0),
        ("screen-lens", "gemini-2.5-flash", 1420.0),
    ])
    def test_engine_valid_domains(self, router, domain, expected_model, expected_elo):
        res = router.route(domain)
        assert res["domain"] == domain
        assert res["routed_model"] == expected_model
        assert abs(res["base_public_elo"] - expected_elo) < 1e-3
        assert res["computed_utility_score"] > 0.80
        assert "fallback_model" in res
        assert "alternate_free_api" in res
        assert "local_mesh_fallback" in res


class TestCasingAndDelimiterVariants:
    """Stress tests case insensitivity and delimiter variations."""

    @pytest.mark.parametrize("raw_input,expected_domain,expected_model", [
        ("DEEP-RESEARCH", "deep-research", "gemini-2.5-pro"),
        ("Deep_Research", "deep-research", "gemini-2.5-pro"),
        ("deep_research", "deep-research", "gemini-2.5-pro"),
        ("DEEP_RESEARCH", "deep-research", "gemini-2.5-pro"),
        ("oss_scout", "oss-scout", "gemini-2.5-flash"),
        ("OSS-SCOUT", "oss-scout", "gemini-2.5-flash"),
        ("Oss_Scout", "oss-scout", "gemini-2.5-flash"),
        ("OSS_SCOUT", "oss-scout", "gemini-2.5-flash"),
        ("REVERSE-ENGINEERING", "reverse-engineering", "gemini-2.0-flash-thinking-exp-01-21"),
        ("Reverse_Engineering", "reverse-engineering", "gemini-2.0-flash-thinking-exp-01-21"),
        ("reverse_engineering", "reverse-engineering", "gemini-2.0-flash-thinking-exp-01-21"),
        ("SCREEN-LENS", "screen-lens", "gemini-2.5-flash"),
        ("Screen_Lens", "screen-lens", "gemini-2.5-flash"),
        ("screen_lens", "screen-lens", "gemini-2.5-flash"),
    ])
    def test_normalization_variants(self, router, raw_input, expected_domain, expected_model):
        res = router.route(raw_input)
        assert res["domain"] == expected_domain
        assert res["routed_model"] == expected_model


class TestInvalidAndEdgeCases:
    """Tests robustness against invalid, empty, or adversarial inputs."""

    @pytest.mark.parametrize("invalid_input", [
        "unknown-domain",
        "",
        "   ",
        "random_gibberish_xyz_999",
        "42",
        "!@#$%^&*()_+",
        "null",
        "None",
    ])
    def test_graceful_fallback_for_unknown(self, router, invalid_input):
        # Should gracefully fallback to default domain ('deep-research') without raising exceptions
        res = router.route(invalid_input)
        assert res["domain"] == "deep-research"
        assert res["routed_model"] == "gemini-2.5-pro"
        assert res["base_public_elo"] == 1457.0

    def test_extremely_long_input(self, router):
        long_prompt = "deep-research " + ("word " * 5000)
        t0 = time.perf_counter()
        res = router.route(long_prompt)
        dt = (time.perf_counter() - t0) * 1000
        assert res["domain"] == "deep-research"
        assert res["routed_model"] == "gemini-2.5-pro"
        assert dt < 50.0, f"Long string processing took too long: {dt:.2f}ms"


class TestNaturalLanguageKeywords:
    """Tests semantic keyword mapping within natural queries."""

    @pytest.mark.parametrize("query,expected_domain", [
        ("Please synthesize a comprehensive literature survey on quantum error correction", "deep-research"),
        ("Scan this github repository for cargo dependency license violations", "oss-scout"),
        ("Disassemble this firmware binary hex packet and extract the protocol struct", "reverse-engineering"),
        ("Ground UI bounding box coordinates for desktop actuation on macOS", "screen-lens"),
    ])
    def test_keyword_matching(self, router, query, expected_domain):
        res = router.route(query)
        assert res["domain"] == expected_domain


class TestLMSYSScoreCorrespondence:
    """Validates 100% adherence to documented LMSYS records in mapping JSON."""

    def test_all_catalog_models_match(self, router, mapping_data):
        catalog = mapping_data.get("models_catalog", {})
        for model_id, meta in catalog.items():
            expected = float(meta["public_elo_lmsys"])
            actual = router.get_effective_elo(model_id)
            assert actual == expected, f"Mismatch for {model_id}: expected {expected}, got {actual}"

    def test_all_alternate_apis_match(self, router, mapping_data):
        alt = mapping_data.get("alternate_free_apis", {})
        for model_id, meta in alt.items():
            expected = float(meta["public_elo_lmsys"])
            actual = router.get_effective_elo(model_id)
            assert actual == expected, f"Mismatch for alt {model_id}: expected {expected}, got {actual}"

    def test_assigned_domain_scores_match(self, router, mapping_data):
        domain_cfg = mapping_data.get("domain_routing", {})
        for domain, meta in domain_cfg.items():
            assigned = meta["assigned_model"]
            expected_elo = float(meta["assigned_model_elo"])
            res = router.route(domain)
            assert res["routed_model"] == assigned
            assert res["base_public_elo"] == expected_elo


class TestCLIExecutionAndFormat:
    """Directly invokes test_router.py via subprocess to test acceptance criteria."""

    @pytest.mark.parametrize("cli_arg,expected_domain,expected_model,expected_elo", [
        ("deep-research", "deep-research", "gemini-2.5-pro", "1457.0"),
        ("oss-scout", "oss-scout", "gemini-2.5-flash", "1420.0"),
        ("reverse-engineering", "reverse-engineering", "gemini-2.0-flash-thinking-exp-01-21", "1397.0"),
        ("screen-lens", "screen-lens", "gemini-2.5-flash", "1420.0"),
        ("DEEP-RESEARCH", "deep-research", "gemini-2.5-pro", "1457.0"),
        ("Deep_Research", "deep-research", "gemini-2.5-pro", "1457.0"),
        ("oss_scout", "oss-scout", "gemini-2.5-flash", "1420.0"),
        ("unknown-domain", "deep-research", "gemini-2.5-pro", "1457.0"),
        ("", "deep-research", "gemini-2.5-pro", "1457.0"),
    ])
    def test_cli_invocation_format_and_exit_code(self, cli_arg, expected_domain, expected_model, expected_elo):
        cmd = [sys.executable, str(REPO_ROOT / "test_router.py")]
        if cli_arg:
            cmd.append(cli_arg)

        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert proc.returncode == 0, f"CLI exited with {proc.returncode}. Stderr: {proc.stderr}"
        match = CLI_REGEX.search(proc.stdout)
        assert match is not None, f"CLI output did not match format. Stdout was: {repr(proc.stdout)}"
        assert match.group("domain") == expected_domain
        assert match.group("model") == expected_model
        assert match.group("elo") == expected_elo
        assert elapsed_ms < 500.0, f"CLI execution exceeded 500ms limit: {elapsed_ms:.2f}ms"

    def test_cli_all_flag(self):
        cmd = [sys.executable, str(REPO_ROOT / "test_router.py"), "--all"]
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        assert proc.returncode == 0
        matches = CLI_REGEX.findall(proc.stdout)
        assert len(matches) == 4
        domains_found = [m[0] for m in matches]
        assert domains_found == ["deep-research", "oss-scout", "reverse-engineering", "screen-lens"]


class TestThroughputAndLatency:
    """Benchmarks execution performance to ensure high-speed routing."""

    def test_batch_routing_latency(self, router):
        domains = ["deep-research", "oss-scout", "reverse-engineering", "screen-lens"]
        iterations = 500
        t0 = time.perf_counter()
        for i in range(iterations):
            d = domains[i % 4]
            router.route(d)
        total_time_ms = (time.perf_counter() - t0) * 1000
        avg_us = (total_time_ms / iterations) * 1000
        print(f"\n[BENCHMARK] {iterations} routes completed in {total_time_ms:.2f}ms (Avg: {avg_us:.2f} us/route)")
        # Routing should be < 500 microseconds per call once loaded in memory
        assert avg_us < 500.0, f"Average route time too slow: {avg_us:.2f} us"
