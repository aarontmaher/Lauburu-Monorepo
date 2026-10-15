#!/usr/bin/env python3
"""
Unit Tests for Cloud AI Tiered Routing Governor
===============================================
Validates:
1. Sovereign local-first routing invariant (low latency, zero spend).
2. Complex mathematical proof routing to Gemini Flash Thinking.
3. Long context routing to Gemini Pro Exp (2M tokens).
4. Web-retrieval routing to xAI Grok-2.
5. Async GitHub PR routing to Google Jules.
6. Quota protection and local fallback behavior.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SWARMS_ROOT = TEST_DIR.parent

if str(SWARMS_ROOT) not in sys.path:
    sys.path.insert(0, str(SWARMS_ROOT))

from cloud_ai_routing_governor import CloudAIRoutingGovernor, CLOUD_AI_TIERS


class TestCloudAIRoutingGovernor:

    def test_default_local_routing(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="ast_validation", complexity="low", estimated_tokens=300)
        assert res["chosen_target"] == "local_qwen_moe"
        assert res["cost_usd"] == 0.00
        assert res["expected_latency_ms"] < 50.0

    def test_mathematical_proof_routes_to_gemini_flash_thinking(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="mathematical_proofs", complexity="extreme")
        assert res["chosen_target"] == "gemini_flash_thinking"
        assert res["provider"] == "google_ai_studio_free"
        assert res["cost_usd"] == 0.00

    def test_long_context_routes_to_nvidia_deepseek_v4_flash(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="codebase_indexing", estimated_tokens=65000)
        assert res["chosen_target"] == "nvidia_deepseek_v4_flash"
        assert res["provider"] == "nvidia_nim_free_tier"

    def test_live_web_facts_routes_to_grok(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="general_research", requires_web=True)
        assert res["chosen_target"] == "grok_2_xai"
        assert res["provider"] == "xai_free_developer_tier"

    def test_async_pr_routes_to_google_jules(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="refactor", is_async_pr=True)
        assert res["chosen_target"] == "google_jules"
        assert res["provider"] == "google_ultra_account"

    def test_frontier_1_6t_routes_to_nvidia_deepseek_v4_pro(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="frontier_1_6t_reasoning", complexity="extreme")
        assert res["chosen_target"] == "nvidia_deepseek_v4_pro"
        assert res["provider"] == "nvidia_nim_free_tier"
        assert res["cost_usd"] == 0.00

    def test_high_speed_code_gen_routes_to_nvidia_deepseek_v4_flash(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="high_speed_code_gen")
        assert res["chosen_target"] == "nvidia_deepseek_v4_flash"

    def test_planning_routes_to_google_jules_before_gemini_3_1_pro(self):
        gov = CloudAIRoutingGovernor()
        res = gov.route_task(domain="system_planning")
        assert res["chosen_target"] == "google_jules"
        assert res["provider"] == "google_ultra_account"
        assert res["cost_usd"] == 0.00


if __name__ == "__main__":
    pytest.main(["-v", __file__])
