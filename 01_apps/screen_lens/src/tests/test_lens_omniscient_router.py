import pytest
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lens_omniscient_router import LensOmniscientRouter


def test_registry_initialization():
    router = LensOmniscientRouter()
    assert len(router.skill_registry) >= 23
    assert "ai-debate" in router.skill_registry
    assert "screen-lens-sovereign" in router.skill_registry


def test_domain_routing():
    router = LensOmniscientRouter()
    res = router.route_request("Mock prompt", ["ai-debate"])
    assert "ai-debate" in res
    assert router.skill_registry["ai-debate"]["invocations"] == 1


def test_l3_offload_invariant():
    router = LensOmniscientRouter()
    assert router.l3_rpc_endpoint == "http://100.101.39.98:8082"


def test_model_routing_logic():
    router = LensOmniscientRouter()
    
    # 1. Syntax/Code generation MUST route to Qwen 2.5 Coder on L3 Hub
    syntax_model = router.route_model("syntax_linting")
    assert syntax_model["id"] == "qwen2.5-coder-7b"
    assert "100.101.39.98" in syntax_model["endpoint"]

    # 2. Architectural planning MUST route to Qwen 3.8 Max Master
    arch_model = router.route_model("architecture_consensus")
    assert arch_model["id"] == "qwen_38_max"
    assert "8082" in arch_model["endpoint"]

    # 3. Red team MUST route to Abliterated Devil's Advocate
    red_team_model = router.route_model("adversarial_critique")
    assert red_team_model["id"] == "qwen_38_max_abliterated"
    assert "8083" in red_team_model["endpoint"]

    # 4. Cloud research MUST route to Gemini Flash
    cloud_model = router.route_model("cloud_deep_research")
    assert cloud_model["id"] == "gemini-3.8-flash"

    # 5. Mobile actuation MUST route to Pixel Edge
    edge_model = router.route_model("mobile_actuation")
    assert edge_model["id"] == "pixel_tensor_g5"


def test_tool_calling_mapping():
    router = LensOmniscientRouter()
    
    # Bash commands must be routed through the canonical mesh SSH executor
    bash_executor = router.route_tool("run_command", {"cmd": "echo test"})
    assert bash_executor == "mesh_ssh_executor"

    # Subagent invocations must map to the Genetic Swarm Router
    subagent_executor = router.route_tool("invoke_subagent", {"Role": "Scout"})
    assert subagent_executor == "genetic_swarm_router"


def test_inverted_orchestration_context_classification():
    """Verifies that Lens accurately infers task type from visual context and prompt."""
    router = LensOmniscientRouter()

    # Scenario A: Code syntax error in active VS Code window
    ctx_code = {"active_app": "Code", "window_title": "engine.py", "recent_ocr": ["NameError: name 'foo' is not defined"]}
    res_code = router.classify_task_and_context("Fix this typo", ctx_code)
    assert res_code["task_type"] == "syntax_linting"
    assert res_code["recommended_model"] == "syntax_worker"

    # Scenario B: Mobile UI on Pixel 10 Pro XL
    ctx_mobile = {"active_app": "com.twitter.android", "window_title": "X", "recent_ocr": ["Post your reply"]}
    res_mobile = router.classify_task_and_context("Tap on Reply button", ctx_mobile)
    assert res_mobile["task_type"] == "mobile_actuation"
    assert res_mobile["recommended_model"] == "edge_mobile"

    # Scenario C: Red team adversarial stress test
    res_red = router.classify_task_and_context("Run an uncensored red team stress test on this network", {})
    assert res_red["task_type"] == "red_team_audit"
    assert res_red["recommended_model"] == "red_team_adversary"

    # Scenario D: High-level architectural debate
    res_arch = router.classify_task_and_context("Analyze the multi-agent consensus and design system architecture", {})
    assert res_arch["task_type"] == "architecture_consensus"
    assert res_arch["recommended_model"] == "master_orchestrator"


def test_pre_grounded_payload_generation():
    """Verifies that Lens pre-synthesizes visual grounding into model prompt."""
    router = LensOmniscientRouter()
    visual_context = {
        "active_app": "Terminal",
        "window_title": "zsh — 80x24",
        "elements": ["Button 'Run'", "Input 'Prompt'"]
    }
    payload = router.pre_ground_payload("Execute tests", visual_context)
    assert "[SCREEN LENS GROUND TRUTH CONTEXT]" in payload["augmented_prompt"]
    assert "Active Application: Terminal" in payload["augmented_prompt"]
    assert "Button 'Run'" in payload["augmented_prompt"]
    assert payload["grounding_injected"] is True


def test_escalation_circuit_breaker():
    """Verifies that subordinate model failures automatically escalate to Sovereign Master."""
    router = LensOmniscientRouter()
    
    # 1 failure: No escalation
    res1 = router.escalate_model("qwen2.5-coder-7b", failure_count=1)
    assert res1["escalate"] is False

    # 2 failures: Escalates to Qwen 3.8 Max Master
    res2 = router.escalate_model("qwen2.5-coder-7b", failure_count=2)
    assert res2["escalate"] is True
    assert res2["target_model"]["id"] == "qwen_38_max"

    # Master failure: Escalates to Cloud Teacher
    res3 = router.escalate_model("qwen_38_max", failure_count=2)
    assert res3["escalate"] is True
    assert res3["target_model"]["id"] == "gemini-3.8-flash"
