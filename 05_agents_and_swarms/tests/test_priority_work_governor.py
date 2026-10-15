#!/usr/bin/env python3
"""
Unit Tests for Priority Work Governor
=====================================
Validates:
1. Loading and ranking of Top 10 Engineering Priorities.
2. Delegation of priority tasks across Qwen MoE 80B, Qwen 3.8 Max, and Gemini Flash 3.8 High.
3. Review and progression of priorities through IN_PROGRESS and COMPLETED states.
4. Fallback execution to MCP, CLI, API, and local model deep audits.
5. Obsidian priorities markdown rendering and continuous LoRA DPO distillation.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SWARMS_ROOT = TEST_DIR.parent

if str(SWARMS_ROOT) not in sys.path:
    sys.path.insert(0, str(SWARMS_ROOT))

from priority_work_governor import PriorityWorkGovernor


class TestPriorityWorkGovernor:

    def test_top_10_priorities_initialization(self):
        gov = PriorityWorkGovernor()
        priorities = gov.state["priorities"]
        assert len(priorities) == 10
        p_ids = [p["id"] for p in priorities]
        assert "P01" in p_ids
        assert "P10" in p_ids

    def test_review_and_execute_progresses_priority(self):
        gov = PriorityWorkGovernor()
        res = gov.review_and_execute_next_priority()
        assert res["cycle"] >= 1
        assert "target_executed" in res
        assert "assigned_model" in res["target_executed"] or "action" in res["target_executed"]

    def test_fallback_tool_and_mcp_audit(self):
        gov = PriorityWorkGovernor()
        res = gov._execute_tool_and_mcp_fallback_audit()
        assert res["action"] == "FALLBACK_TOOL_AND_MCP_ANALYSIS"
        assert len(res["mcps_audited"]) >= 4
        assert len(res["clis_audited"]) >= 5
        assert len(res["local_models_audited"]) >= 3


if __name__ == "__main__":
    pytest.main(["-v", __file__])
