#!/usr/bin/env python3
"""
Unit Tests for Sovereign 80B Agent Forge
========================================
Validates programmatic synthesis across:
1. Cloudflare Agents SDK (Durable Objects, WebSockets, RPC)
2. Google Antigravity SDK & AGY Customizations (Subagents, Skills)
3. HuggingFace SmolAgents (CodeAgent, ToolCallingAgent)
4. Teamwork Multi-Agent Swarms (Sentinel Governance, Victory Audits)
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SWARMS_ROOT = TEST_DIR.parent
REPO_ROOT = SWARMS_ROOT.parent

if str(SWARMS_ROOT) not in sys.path:
    sys.path.insert(0, str(SWARMS_ROOT))

from sovereign_80b_agent_forge import (
    Sovereign80BAgentForge,
    CloudflareAgentsSDKBuilder,
    GoogleAntigravitySDKBuilder,
    SmolAgentsBuilder,
    TeamworkSwarmBuilder,
    SUPPORTED_FRAMEWORKS
)


class TestSovereign80BAgentForge:

    def test_supported_frameworks_count(self):
        assert len(SUPPORTED_FRAMEWORKS) == 4
        assert "cloudflare_agents_sdk" in SUPPORTED_FRAMEWORKS
        assert "google_antigravity_sdk" in SUPPORTED_FRAMEWORKS
        assert "huggingface_smolagents" in SUPPORTED_FRAMEWORKS
        assert "teamwork_multiagent_swarm" in SUPPORTED_FRAMEWORKS

    def test_forge_cloudflare_agent(self):
        forge = Sovereign80BAgentForge()
        res = forge.forge_agent("cloudflare_agents_sdk", "MovesenseTelemetryAgent", {"cron": "*/5 * * * *"})
        assert res["framework"] == "cloudflare_agents_sdk"
        assert res["language"] == "typescript"
        assert "@cloudflare/agents" in res["code"]
        assert "@callable()" in res["code"]
        assert "MovesenseTelemetryAgentState" in res["code"]

    def test_forge_google_antigravity_agent(self):
        forge = Sovereign80BAgentForge()
        res = forge.forge_agent("google_antigravity_sdk", "AstAuditorAgent", {
            "role": "AST Code Auditor",
            "tools": ["write_to_file", "run_command", "invoke_subagent"]
        })
        assert res["framework"] == "google_antigravity_sdk"
        spec = res["subagent_spec"]
        assert spec["name"] == "AstAuditorAgent"
        assert spec["enable_write_tools"] is True
        assert spec["enable_subagent_tools"] is True

    def test_forge_huggingface_smolagent(self):
        forge = Sovereign80BAgentForge()
        res = forge.forge_agent("huggingface_smolagents", "CodeRefactorer", {"model_id": "Qwen-3.8-Max"})
        assert res["framework"] == "huggingface_smolagents"
        assert res["language"] == "python"
        assert "from smolagents import CodeAgent" in res["code"]
        assert "http://localhost:8083/v1" in res["code"]

    def test_forge_teamwork_swarm(self):
        forge = Sovereign80BAgentForge()
        res = forge.forge_agent("teamwork_multiagent_swarm", "BiometricsOptimizationSwarm", {
            "working_dir": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics",
            "requirements": [{"title": "512Hz GATT Stream", "description": "Stream ECG data without loss."}]
        })
        assert res["framework"] == "teamwork_multiagent_swarm"
        manifest = res["manifest"]
        assert manifest["project_name"] == "BiometricsOptimizationSwarm"
        assert manifest["sentinel_governance"]["zero_mock_enforcement"] is True
        assert len(manifest["requirements"]) == 1

    def test_invalid_framework_raises_error(self):
        forge = Sovereign80BAgentForge()
        with pytest.raises(ValueError) as exc:
            forge.forge_agent("unsupported_framework", "Dummy", {})
        assert "Unsupported framework" in str(exc.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
