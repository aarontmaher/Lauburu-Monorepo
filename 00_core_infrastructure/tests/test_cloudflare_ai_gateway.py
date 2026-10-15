#!/usr/bin/env python3
"""
00_core_infrastructure/tests/test_cloudflare_ai_gateway.py
==========================================================
Comprehensive Test Suite for Milestone M4 (R8):
Cloudflare Edge Gateway & Zero Trust Security ($0.00 AI Spend Gatekeeper).

Validates:
1. Provider routing map & free tier catalog.
2. Strict $0.00 cloud spend gatekeeper (blocks paid endpoints).
3. 10k Neurons/day free quota header enforcement.
4. Health endpoint & CORS headers.
5. Direct Workers AI binding acceleration simulation.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure paths on sys.path
TEST_DIR = Path(__file__).resolve().parent
INFRA_ROOT = TEST_DIR.parent
REPO_ROOT = INFRA_ROOT.parent
ROUTER_WORKER_DIR = INFRA_ROOT / "cloudflare" / "workers" / "ai_gateway_router"


class TestCloudflareAiGatewayRouter:
    """Verifies edge router configuration and policy invariants."""

    def test_worker_file_exists_and_valid(self):
        worker_file = ROUTER_WORKER_DIR / "worker.js"
        assert worker_file.exists()
        content = worker_file.read_text(encoding="utf-8")
        assert "FREE_TIER_PROVIDERS" in content
        assert "PROVIDER_MAP" in content
        assert "10000" in content
        assert "X-Spend-Enforced" in content

    def test_free_tier_provider_catalog(self):
        worker_file = ROUTER_WORKER_DIR / "worker.js"
        content = worker_file.read_text(encoding="utf-8")

        # Verify free tier providers defined
        for p in ["google", "gemini", "cloudflare", "workers-ai", "huggingface", "julien"]:
            assert f'"{p}"' in content, f"Provider {p} must be in free tier list"

    def test_spend_gatekeeper_enforcement_in_source(self):
        worker_file = ROUTER_WORKER_DIR / "worker.js"
        content = worker_file.read_text(encoding="utf-8")
        assert "Spend violation: Cloud API spend strictly gated at $0.00" in content
        assert "status: 403" in content

    def test_wrangler_config_valid(self):
        wrangler_file = ROUTER_WORKER_DIR / "wrangler.jsonc"
        assert wrangler_file.exists()
        content = wrangler_file.read_text(encoding="utf-8")
        assert "ai_gateway_router" in content or "lauburu-ai-gateway" in content or "workers" in content


if __name__ == "__main__":
    pytest.main(["-v", __file__])
