#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite for Hermes 3 Code-as-Action Dispatcher & Sandbox Runtime
=======================================================================================
Validates Features F7, F8, F9:
- F7_HERMES_CODE_ACTION: Multimodal prompt assembly, markdown code block extraction, VLM routing (8084/8085),
  Kimi-VL thinking escalation, ActionPlan data contracts, fallback handling, context truncation.
- F8_SANDBOXED_ACTION_CONTEXT: AgentActionContext high-level primitives (click, tap, scroll, type, swipe,
  wait_for_text, focus_window, press_key, sleep, find_element), AST static security checks forbidding dangerous
  modules/builtins (os, sys, subprocess, eval, open, __import__), script execution error trapping, state isolation.
- F9_RULE0_ZERO_MOCK_VALIDATOR: SovereignZeroMockAuditor / ZeroMockValidator enforcing Rule #0 zero-mock assertion,
  detecting mock/dummy/fake/placeholder tokens across strings and nested structures, word boundary precision,
  LoRA dataset sample auditing, frame hash verification.

Rule #0: Zero-Mock & Zero-Simulated Data.
"""

import asyncio
import base64
import hashlib
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

# Path setup
MODULE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MODULE_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from hermes_code_action_dispatcher import (
    HermesCodeActionDispatcher,
    HermesActionDispatcher,
    AgentActionContext,
    ActionPlan,
    ExecutionResult,
    UIElement,
    UIElementNode,
    MotionEvent,
    VisualContextSnapshot,
    ZeroMockValidator,
    SovereignZeroMockAuditor,
    ASTSafetyChecker,
    ASTStaticValidator,
    HermesDispatcherError,
    ASTSecurityViolationError,
    RuleZeroViolationError
)


class TestF7HermesCodeAction(unittest.TestCase):
    """Test suite for F7_HERMES_CODE_ACTION: Synthesis, routing, extraction, and contracts."""

    def setUp(self):
        self.dispatcher = HermesCodeActionDispatcher(
            vlm_host="127.0.0.1",
            vlm_port=8084,
            kimi_port=8085,
            timeout_s=0.5,
            max_context_chars=50000
        )

    def test_multimodal_prompt_formatting_standard(self):
        """Verify standard multimodal prompt assembly with elements and goal."""
        elem = UIElement(
            id=1, frame_id=100, source="ocr", role="AXButton", text="Connect Movesense",
            left_bound=0.2, top_bound=0.3, width_bound=0.4, height_bound=0.1
        )
        payload = self.dispatcher.assemble_multimodal_prompt(
            goal="Click Connect Movesense",
            elements=[elem],
            active_app="Movesense Hub",
            window_title="Sensor Monitor"
        )
        self.assertIn("messages", payload)
        user_content = payload["messages"][1]["content"]
        self.assertIn("Goal: Click Connect Movesense", user_content)
        self.assertIn("Connect Movesense", user_content)
        self.assertIn("Movesense Hub", user_content)

    def test_multimodal_prompt_with_valid_base64_image(self):
        """Verify prompt payload includes image_url when valid base64 is provided."""
        dummy_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        b64_str = base64.b64encode(dummy_png).decode("utf-8")
        payload = self.dispatcher.assemble_multimodal_prompt(
            goal="Analyze screen",
            elements=[],
            image_b64=b64_str
        )
        user_content = payload["messages"][1]["content"]
        self.assertIsInstance(user_content, list)
        self.assertEqual(user_content[1]["type"], "image_url")
        self.assertIn("data:image/png;base64,", user_content[1]["image_url"]["url"])

    def test_multimodal_prompt_with_corrupted_base64_rejection(self):
        """Verify corrupted base64 is cleanly omitted without crashing."""
        corrupted_b64 = "Corrupted@#$Base64!NotValid"
        payload = self.dispatcher.assemble_multimodal_prompt(
            goal="Analyze screen",
            elements=[],
            image_b64=corrupted_b64
        )
        user_content = payload["messages"][1]["content"]
        self.assertIsInstance(user_content, str)
        self.assertNotIn("data:image/png;base64,", user_content)

    def test_context_truncation_boundary(self):
        """Verify large context exceeding max_context_chars is safely truncated."""
        dispatcher_small = HermesCodeActionDispatcher(max_context_chars=500)
        large_elements = [
            UIElement(id=i, frame_id=1, source="ocr", role="Button", text=f"Button_{i}_" * 10,
                      left_bound=0.1, top_bound=0.1, width_bound=0.1, height_bound=0.1)
            for i in range(50)
        ]
        payload = dispatcher_small.assemble_multimodal_prompt(
            goal="Locate target",
            elements=large_elements
        )
        user_content = payload["messages"][1]["content"]
        self.assertLessEqual(len(user_content), 1200)

    def test_vlm_port_8084_routing_default(self):
        """Verify standard visual queries route to Port 8084."""
        goal = "Click on the Search bar"
        self.assertFalse(self.dispatcher.should_escalate_to_tier1(goal))

    def test_tier1_escalation_flag_3d_spatial(self):
        """Verify 3D spatial grappling and tatami kinematics escalate to Port 8085."""
        goals_requiring_escalation = [
            "Verify 3D spatial grappling kinematics tree node 450",
            "Calculate tatami joint torque in 3D space",
            "Perform complex reasoning across multi-step planning"
        ]
        for goal in goals_requiring_escalation:
            self.assertTrue(self.dispatcher.should_escalate_to_tier1(goal), f"Goal should escalate: {goal}")

    def test_action_code_markdown_extraction_fenced(self):
        """Verify Python code extraction from ```python ... ``` fences."""
        raw = (
            "Thought: Need to click sensor button.\n"
            "```python\n"
            "agent.click(450.0, 600.0)\n"
            "agent.sleep(0.3)\n"
            "```\n"
            "Done."
        )
        code = self.dispatcher.extract_code_from_markdown(raw)
        self.assertEqual(code, "agent.click(450.0, 600.0)\nagent.sleep(0.3)")

    def test_action_code_markdown_extraction_unfenced_valid(self):
        """Verify recovery of unfenced valid Python statements."""
        raw = "agent.click(300, 400)\nagent.wait_for_text('OK', 2.0)"
        code = self.dispatcher.extract_code_from_markdown(raw)
        self.assertEqual(code, raw)

    def test_action_code_markdown_extraction_empty_or_whitespace(self):
        """Verify empty or whitespace string extraction returns empty string."""
        self.assertEqual(self.dispatcher.extract_code_from_markdown("   \n\t  "), "")
        self.assertEqual(self.dispatcher.extract_code_from_markdown(""), "")

    def test_synthesize_actions_fallback_on_vlm_offline(self):
        """Verify fallback to local MPS synthesis when VLM is offline."""
        ctx = {"elements": [UIElement(1, 1, "ocr", "Button", "Start Stream", 0.3, 0.4, 0.2, 0.1)]}
        plan = self.dispatcher.synthesize_actions(ctx, "Click Start Stream", fallback_to_local_mps=True)
        self.assertIsInstance(plan, ActionPlan)
        self.assertTrue(plan.ast_safety_passed)
        self.assertIn("agent.click", plan.generated_code)
        self.assertIn("MPSFallback", plan.model_name)

    def test_action_plan_serialization(self):
        """Verify ActionPlan to_dict and from_dict roundtrip."""
        plan = ActionPlan(
            action_id="act_test_001",
            goal="Launch App",
            generated_code="agent.click(100, 200)",
            model_name="Hermes-3-Llama-3.1-8B",
            inference_port=8084,
            ast_safety_passed=True,
            estimated_latency_ms=1.5
        )
        d = plan.to_dict()
        reconstructed = ActionPlan.from_dict(d)
        self.assertEqual(plan.action_id, reconstructed.action_id)
        self.assertEqual(plan.generated_code, reconstructed.generated_code)
        self.assertEqual(plan.inference_port, reconstructed.inference_port)


class TestF8SandboxedActionContext(unittest.TestCase):
    """Test suite for F8_SANDBOXED_ACTION_CONTEXT: Execution primitives and AST security."""

    def test_agent_click_and_tap_primitives(self):
        """Verify agent.click(x, y) and agent.tap(x, y) dispatching."""
        ctx = AgentActionContext(platform="macos")
        res = ctx.execute_script("agent.click(450.0, 720.0)\nagent.tap(100.0, 200.0)")
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("click(450.0, 720.0)", res.actions_dispatched)
        self.assertIn("tap(100.0, 200.0)", res.actions_dispatched)

    def test_agent_scroll_primitive_directions(self):
        """Verify agent.scroll(direction, distance) and agent.scroll(dx, dy)."""
        ctx = AgentActionContext()
        res1 = ctx.execute_script("agent.scroll('down', 500)")
        self.assertEqual(res1.status, "SUCCESS")
        self.assertIn("scroll(down, 500)", res1.actions_dispatched)

        ctx2 = AgentActionContext()
        res2 = ctx2.execute_script("agent.scroll(0, -300)")
        self.assertEqual(res2.status, "SUCCESS")
        self.assertIn("scroll(up, 300)", res2.actions_dispatched)

    def test_agent_type_and_type_text(self):
        """Verify agent.type(text) and agent.type_text(text)."""
        ctx = AgentActionContext()
        res = ctx.execute_script("agent.type('Movesense 512Hz')\nagent.type_text(' ECG')")
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("type(Movesense 512Hz)", res.actions_dispatched)
        self.assertIn("type( ECG)", res.actions_dispatched)

    def test_agent_swipe_primitive(self):
        """Verify agent.swipe(x1, y1, x2, y2, duration_ms)."""
        ctx = AgentActionContext()
        res = ctx.execute_script("agent.swipe(100.0, 500.0, 100.0, 1000.0, duration_ms=250)")
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("swipe(100.0, 500.0, 100.0, 1000.0, duration_ms=250)", res.actions_dispatched)

    def test_agent_wait_for_text_and_focus_window(self):
        """Verify agent.wait_for_text and agent.focus_window."""
        ctx = AgentActionContext()
        res = ctx.execute_script("agent.focus_window('Port 4000')\nagent.wait_for_text('Connected', timeout_s=3.0)")
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("focus_window(Port 4000)", res.actions_dispatched)
        self.assertIn("wait_for_text(Connected, timeout=3.0)", res.actions_dispatched)

    def test_agent_find_element(self):
        """Verify agent.find_element finds matching elements."""
        elem = UIElement(1, 1, "ocr", "AXButton", "Start Recording", 0.1, 0.2, 0.3, 0.4)
        ctx = AgentActionContext(elements=[elem])
        found = ctx.find_element(text="Start")
        self.assertIsNotNone(found)
        self.assertEqual(found.text, "Start Recording")
        self.assertIsNone(ctx.find_element(text="NonExistent"))

    def test_ast_security_rejects_import_os(self):
        """Verify AST validator strictly rejects 'import os'."""
        is_safe, err = ASTSafetyChecker.validate_code("import os\nos.system('ls')")
        self.assertFalse(is_safe)
        self.assertIn("Disallowed import: os", err)

    def test_ast_security_rejects_import_subprocess(self):
        """Verify AST validator strictly rejects 'import subprocess'."""
        is_safe, err = ASTSafetyChecker.validate_code("import subprocess\nsubprocess.Popen(['ls'])")
        self.assertFalse(is_safe)
        self.assertIn("Disallowed import: subprocess", err)

    def test_ast_security_rejects_from_shutil_import(self):
        """Verify AST validator strictly rejects 'from shutil import rmtree'."""
        is_safe, err = ASTSafetyChecker.validate_code("from shutil import rmtree\nrmtree('.')")
        self.assertFalse(is_safe)
        self.assertIn("Disallowed import from: shutil", err)

    def test_ast_security_rejects_builtin_eval_call(self):
        """Verify AST validator strictly rejects 'eval(...)'."""
        is_safe, err = ASTSafetyChecker.validate_code("x = eval('1 + 1')")
        self.assertFalse(is_safe)
        self.assertIn("Disallowed builtin call: eval", err)

    def test_ast_security_rejects_builtin_exec_call(self):
        """Verify AST validator strictly rejects nested 'exec(...)' call."""
        is_safe, err = ASTSafetyChecker.validate_code("exec('print(1)')")
        self.assertFalse(is_safe)
        self.assertIn("Disallowed builtin call: exec", err)

    def test_ast_security_rejects_builtin_open_call(self):
        """Verify AST validator strictly rejects 'open(...)'."""
        is_safe, err = ASTSafetyChecker.validate_code("f = open('/tmp/test', 'w')")
        self.assertFalse(is_safe)
        self.assertIn("Disallowed builtin call: open", err)

    def test_ast_security_rejects_dunder_class_hierarchy_traversal(self):
        """Verify AST validator strictly rejects class hierarchy dunder traversal."""
        payload = "().__class__.__bases__[0].__subclasses__()"
        is_safe, err = ASTSafetyChecker.validate_code(payload)
        self.assertFalse(is_safe)
        self.assertIn("Disallowed dunder attribute access", err)

    def test_ast_security_rejects_dangerous_dunder_attributes(self):
        """Verify AST validator blocks specific dangerous reflection dunders."""
        dangerous_dunders = [
            "f = (lambda: None).__globals__",
            "c = (lambda: None).__code__",
            "d = (lambda: None).__dict__",
            "b = int.__bases__",
            "m = int.__mro__",
            "s = int.__subclasses__()",
            "g = (lambda: None).__getattribute__('__globals__')",
            "q = (lambda: None).__qualname__",
        ]
        for code in dangerous_dunders:
            is_safe, err = ASTSafetyChecker.validate_code(code)
            self.assertFalse(is_safe, f"Should reject dangerous dunder in: {code}")
            self.assertIn("Disallowed dunder attribute access", err)

    def test_ast_security_blocks_rce_popen_exploit_execution(self):
        """Verify end-to-end sandbox execution blocks CPython Popen exploit payload."""
        exploit_payload = (
            "popen = [c for c in ().__class__.__bases__[0].__subclasses__() if c.__name__ == 'Popen'][0]\n"
            "p = popen(['echo', 'escape'])\n"
        )
        is_safe, err = ASTSafetyChecker.validate_code(exploit_payload)
        self.assertFalse(is_safe)
        self.assertIn("Disallowed dunder attribute access", err)

        ctx = AgentActionContext()
        res = ctx.execute_script(exploit_payload)
        self.assertEqual(res.status, "BLOCKED")
        self.assertEqual(res.post_verification_score, 0.0)
        self.assertIn("Disallowed dunder attribute access", res.error_message)

    def test_agent_scroll_polymorphic_signatures(self):
        """Verify agent.scroll accepts all supported calling conventions."""
        ctx = AgentActionContext()
        # Keyword direction and distance_px
        ctx.scroll(direction="down", distance_px=150)
        self.assertIn("scroll(down, 150)", ctx.dispatched_actions)

        # Keyword dx and dy
        ctx.scroll(dx=0, dy=400)
        self.assertIn("scroll(down, 400)", ctx.dispatched_actions)

        # Keyword dx and dy with upward direction
        ctx.scroll(dx=0, dy=-250)
        self.assertIn("scroll(up, 250)", ctx.dispatched_actions)

        # Positional coordinate scroll
        ctx.scroll(0, 350)
        self.assertIn("scroll(down, 350)", ctx.dispatched_actions)

    def test_runtime_exception_capture(self):
        """Verify runtime errors inside sandbox return status=FAILED without crashing process."""
        ctx = AgentActionContext()
        res = ctx.execute_script("x = 1 / 0")
        self.assertEqual(res.status, "FAILED")
        self.assertEqual(res.post_verification_score, 0.0)
        self.assertIn("division by zero", res.error_message)

    def test_state_isolation_between_contexts(self):
        """Verify separate AgentActionContext instances do not leak dispatched action history."""
        ctx1 = AgentActionContext()
        ctx1.click(100, 200)
        ctx2 = AgentActionContext()
        self.assertEqual(len(ctx2.dispatched_actions), 0)


class TestF9RuleZeroMockValidator(unittest.TestCase):
    """Test suite for F9_RULE0_ZERO_MOCK_VALIDATOR: Sovereign Rule #0 enforcement."""

    def test_forbidden_mock_tokens_rejected(self):
        """Verify detection and rejection of various mock token formats."""
        invalid_strings = [
            "mock_payload_123",
            "This is a mock response",
            "my_test_mock",
            "dummy_user_id",
            "fake_sensor_stream",
            "test_fake_metric",
            "placeholder value",
            "lorem ipsum dolor sit amet"
        ]
        for s in invalid_strings:
            self.assertFalse(ZeroMockValidator.audit_string(s), f"String should be rejected: {s}")

    def test_authentic_telemetry_approved(self):
        """Verify authentic sensor telemetry and indicators are approved."""
        valid_strings = [
            "Movesense 512Hz ECG Active (HR: 138 bpm)",
            "Screenpipe frame offset 482 indexed to SQLite",
            "Shizuku IInputManager touch event injected with 0.28ms latency",
            "",
            "--"
        ]
        for s in valid_strings:
            self.assertTrue(ZeroMockValidator.audit_string(s), f"String should be approved: {s}")

    def test_word_boundary_precision(self):
        """Verify legitimate words containing 'mock' or 'fake' substrings are not falsely flagged."""
        self.assertTrue(ZeroMockValidator.audit_string("The mockingbird sings in spring"))
        self.assertTrue(ZeroMockValidator.audit_string("Shamrock hotel in Dublin"))

    def test_nested_dictionary_mock_detection(self):
        """Verify deep recursive detection of forbidden tokens in nested dict/list structures."""
        nested = {
            "meta": {
                "tags": ["ecg", "telemetry"],
                "details": {
                    "sub_item": "contains mock_token here"
                }
            }
        }
        self.assertFalse(ZeroMockValidator.audit_dict(nested))

    def test_lora_training_sample_audit(self):
        """Verify complete LoRA sample audit."""
        valid_sample = {
            "instruction": "Click Movesense Sensor",
            "thought": "Located button at [0.5, 0.5]",
            "output": {"code": "agent.click(500, 500)", "status": "SUCCESS"},
            "metadata": {"rule_0_verified": True}
        }
        self.assertTrue(ZeroMockValidator.audit_lora_sample(valid_sample))

        invalid_sample = {
            "instruction": "Test action",
            "thought": "Using fake_response for testing",
            "output": {"status": "SUCCESS"}
        }
        self.assertFalse(ZeroMockValidator.audit_lora_sample(invalid_sample))

    def test_frame_hash_verification(self):
        """Verify frame hash computation and minimum size assertion."""
        # >10KB valid frame
        valid_frame = b"\x89PNG\r\n\x1a\n" + os.urandom(11000)
        expected_hash = hashlib.md5(valid_frame).hexdigest()
        is_valid, computed_h, err = ZeroMockValidator.verify_frame_hash(valid_frame, expected_hash)
        self.assertTrue(is_valid)
        self.assertEqual(computed_h, expected_hash)
        self.assertIsNone(err)

        # Undersized frame <= 10240 bytes
        small_frame = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        is_valid_small, _, err_small = ZeroMockValidator.verify_frame_hash(small_frame)
        self.assertFalse(is_valid_small)
        self.assertIn("min required", err_small)

    def test_assert_zero_mock_raises_exception(self):
        """Verify assert_zero_mock raises RuleZeroViolationError on mock token."""
        with self.assertRaises(RuleZeroViolationError):
            ZeroMockValidator.assert_zero_mock("mock_data_test", "test_context")


class TestAsyncAndIntegration(unittest.IsolatedAsyncioTestCase):
    """Async API and end-to-end plan execution tests."""

    async def test_async_synthesis_and_execution(self):
        dispatcher = HermesCodeActionDispatcher(timeout_s=0.2)
        ctx = {"elements": [UIElement(1, 1, "ocr", "AXButton", "Zone 2", 0.4, 0.4, 0.2, 0.2)]}
        plan = await dispatcher.synthesize_actions_async(ctx, "Click Zone 2", fallback_to_local_mps=True)
        self.assertTrue(plan.ast_safety_passed)

        action_ctx = AgentActionContext()
        res = await dispatcher.execute_action_plan_async(plan, action_ctx)
        self.assertEqual(res.status, "SUCCESS")
        self.assertGreater(len(res.actions_dispatched), 0)

    async def test_async_health_check(self):
        dispatcher = HermesCodeActionDispatcher()
        health = await dispatcher.health_check_async()
        self.assertIn("status", health)
        self.assertTrue(health["rule_0_verified"])


if __name__ == "__main__":
    unittest.main()
