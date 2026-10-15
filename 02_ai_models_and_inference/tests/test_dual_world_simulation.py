# -*- coding: utf-8 -*-
import math
import os
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
SIM_DIR = REPO_ROOT / "02_ai_models_and_inference" / "simulation"

if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentworld_driver import (
    AgentWorldDriver,
    CopyOnWriteVFS,
    AgentWorldStepResult,
    DANGEROUS_COMMAND_PATTERNS
)
from webworld_driver import (
    WebWorldDriver,
    ShadowDOM,
    ShadowDOMNode,
    WebWorldStepResult,
    calculate_contrast_ratio,
    hex_to_rgb
)
from lookahead_interceptor import (
    LookaheadInterceptor,
    AdmissionGateResult,
    MIN_SAFETY_SCORE,
    MAX_REGRESSION_PROB,
    MAX_LAYOUT_OVERFLOWS,
    MIN_SIMULATION_CONFIDENCE
)

class TestAgentWorldDriver(unittest.TestCase):
    def setUp(self):
        self.driver = AgentWorldDriver()
        self.vfs = CopyOnWriteVFS()

    def test_vfs_basic_file_lifecycle(self):
        self.assertFalse(self.vfs.exists("/workspace/app.py"))
        self.vfs.write_file("/workspace/app.py", "print('hello world')")
        self.assertTrue(self.vfs.exists("/workspace/app.py"))
        self.assertEqual(self.vfs.read_file("/workspace/app.py"), "print('hello world')")
        self.assertTrue(self.vfs.is_dir("/workspace"))
        self.assertIn("app.py", self.vfs.list_dir("/workspace"))
        removed = self.vfs.remove_file("/workspace/app.py")
        self.assertTrue(removed)
        self.assertFalse(self.vfs.exists("/workspace/app.py"))

    def test_vfs_clone_isolation(self):
        self.vfs.write_file("/test/base.txt", "original")
        cloned = self.vfs.clone()
        cloned.write_file("/test/base.txt", "modified")
        cloned.write_file("/test/new.txt", "new file")
        self.assertEqual(self.vfs.read_file("/test/base.txt"), "original")
        self.assertFalse(self.vfs.exists("/test/new.txt"))
        self.assertEqual(cloned.read_file("/test/base.txt"), "modified")
        self.assertTrue(cloned.exists("/test/new.txt"))

    def test_dangerous_command_detection(self):
        dangerous_cmds = [
            "rm -rf /",
            "rm -rf /etc/shadow",
            "rm -rf /System",
            "mkfs.ext4 /dev/sda1",
            ":(){ :|:& };:",
            "> /etc/passwd",
            "chmod -R 777 /etc",
        ]
        for cmd in dangerous_cmds:
            safe, reason = self.driver.check_command_safety(cmd)
            self.assertFalse(safe, f"Dangerous command failed to be blocked: {cmd}")
            self.assertIn("Dangerous command", reason)

    def test_safe_command_execution(self):
        res_mkdir = self.driver.simulate_shell_command("mkdir -p /workspace/src", vfs=self.vfs)
        self.assertEqual(res_mkdir.exit_code, 0)
        self.assertGreaterEqual(res_mkdir.safety_score, 0.90)
        res_touch = self.driver.simulate_shell_command("touch /workspace/src/main.py", vfs=self.vfs)
        self.assertEqual(res_touch.exit_code, 0)
        self.assertTrue(self.vfs.exists("/workspace/src/main.py"))
        res_pytest = self.driver.simulate_shell_command("pytest tests/ -v", vfs=self.vfs)
        self.assertEqual(res_pytest.exit_code, 0)
        self.assertIn("passed", res_pytest.stdout)

    def test_code_mutation_syntax_validation(self):
        valid_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        res_valid = self.driver.simulate_code_mutation("/src/math.py", valid_code, vfs=self.vfs)
        self.assertEqual(res_valid.exit_code, 0)
        self.assertGreaterEqual(res_valid.safety_score, 0.90)
        self.assertEqual(self.vfs.read_file("/src/math.py"), valid_code)
        invalid_code = "def bad_syntax(:\n    return 0"
        res_invalid = self.driver.simulate_code_mutation("/src/bad.py", invalid_code, vfs=self.vfs)
        self.assertEqual(res_invalid.exit_code, 1)
        self.assertLess(res_invalid.safety_score, 0.50)
        self.assertGreater(res_invalid.regression_probability, 0.80)

    def test_adb_device_simulation(self):
        res_dev = self.driver.simulate_shell_command("adb devices", vfs=self.vfs)
        self.assertEqual(res_dev.exit_code, 0)
        self.assertIn("Pixel_10_Pro_XL", res_dev.stdout)
        res_wake = self.driver.simulate_shell_command("adb shell termux-wake-lock", vfs=self.vfs)
        self.assertEqual(res_wake.exit_code, 0)
        self.assertIn("WakeLock Acquired", res_wake.stdout)

    def test_mcp_tool_simulation(self):
        res_w = self.driver.simulate_mcp_tool_call("write_file", {"path": "/mcp.txt", "content": "data"}, vfs=self.vfs)
        self.assertEqual(res_w.exit_code, 0)
        self.assertEqual(self.vfs.read_file("/mcp.txt"), "data")
        res_r = self.driver.simulate_mcp_tool_call("read_file", {"path": "/mcp.txt"}, vfs=self.vfs)
        self.assertEqual(res_r.exit_code, 0)
        self.assertEqual(res_r.stdout, "data")
        res_unreg = self.driver.simulate_mcp_tool_call("unknown_tool", {}, vfs=self.vfs)
        self.assertEqual(res_unreg.exit_code, 1)

class TestWebWorldDriver(unittest.TestCase):
    def setUp(self):
        self.driver = WebWorldDriver()
        self.dom = ShadowDOM(viewport_width=1280.0, viewport_height=800.0)

    def test_contrast_ratio_mathematics(self):
        ratio = calculate_contrast_ratio("#FFFFFF", "#000000")
        self.assertEqual(ratio, 21.0)
        ratio_same = calculate_contrast_ratio("#777777", "#777777")
        self.assertEqual(ratio_same, 1.0)
        ratio_cyan = calculate_contrast_ratio("#38BDF8", "#070B12")
        self.assertGreaterEqual(ratio_cyan, 4.5)

    def test_layout_overflow_detection(self):
        clean_node = ShadowDOMNode(tag="div", node_id="card", width=600.0, height=200.0)
        self.dom.add_node("root_html", clean_node)
        self.assertEqual(len(self.dom.evaluate_layout_overflows()), 0)
        overflow_node = ShadowDOMNode(tag="div", node_id="giant_table", width=1600.0, height=300.0)
        self.dom.add_node("root_html", overflow_node)
        overflows = self.dom.evaluate_layout_overflows()
        self.assertGreater(len(overflows), 0)
        self.assertEqual(overflows[0]["type"], "VIEWPORT_HORIZONTAL_OVERFLOW")

    def test_wcag_accessibility_audits(self):
        img_no_alt = ShadowDOMNode(tag="img", node_id="avatar", attributes={"src": "/pic.png"})
        btn_no_label = ShadowDOMNode(tag="button", node_id="icon_btn", text_content="")
        low_contrast_text = ShadowDOMNode(
            tag="p",
            node_id="faint_text",
            text_content="Hard to read",
            styles={"color": "#444444", "background": "#333333"}
        )
        self.dom.add_node("root_html", img_no_alt)
        self.dom.add_node("root_html", btn_no_label)
        self.dom.add_node("root_html", low_contrast_text)
        violations = self.dom.evaluate_accessibility_and_contrast()
        v_types = [v["type"] for v in violations]
        self.assertIn("MISSING_IMG_ALT", v_types)
        self.assertIn("BUTTON_MISSING_ACCESSIBLE_NAME", v_types)
        self.assertIn("WCAG_CONTRAST_VIOLATION", v_types)

    def test_route_and_link_regressions(self):
        valid_link = ShadowDOMNode(tag="a", node_id="nav_dashboard", attributes={"href": "/dashboard"})
        broken_link = ShadowDOMNode(tag="a", node_id="nav_broken", attributes={"href": "/non_existent_page"})
        self.dom.add_node("root_html", valid_link)
        self.dom.add_node("root_html", broken_link)
        regressions = self.dom.evaluate_route_and_link_regressions()
        self.assertEqual(len(regressions), 1)
        self.assertEqual(regressions[0]["unresolved_target"], "/non_existent_page")

    def test_graphql_mutation_simulation(self):
        res_valid = self.driver.simulate_graphql_mutation("ShopifyStorefront", "cartCreate", {"input": {}})
        self.assertEqual(res_valid.safety_score, 0.99)
        self.assertEqual(res_valid.regression_probability, 0.01)
        res_invalid = self.driver.simulate_graphql_mutation("ShopifyStorefront", "unknownMutation", {})
        self.assertLess(res_invalid.safety_score, 0.60)
        self.assertGreater(res_invalid.regression_probability, 0.50)

class TestLookaheadInterceptor(unittest.TestCase):
    def setUp(self):
        self.interceptor = LookaheadInterceptor()

    def test_composite_score_formula(self):
        score = self.interceptor.compute_composite_score(
            safety_score=1.0,
            regression_prob=0.0,
            layout_overflows=0,
            confidence=1.0,
        )
        self.assertEqual(score, 1.0)
        score_mid = self.interceptor.compute_composite_score(
            safety_score=0.90,
            regression_prob=0.05,
            layout_overflows=0,
            confidence=0.85,
        )
        self.assertAlmostEqual(score_mid, 0.915, places=3)

    def test_admission_gate_pass_criteria(self):
        gate_res = self.interceptor.evaluate_admission_gate(
            safety_score=0.95,
            regression_prob=0.02,
            layout_overflows=0,
            confidence=0.92,
        )
        self.assertTrue(gate_res.admitted)
        self.assertEqual(gate_res.verdict, "ADMITTED_CERTIFIED")
        self.assertEqual(len(gate_res.reasons), 0)

    def test_admission_gate_rejection_on_safety(self):
        gate_res = self.interceptor.evaluate_admission_gate(
            safety_score=0.85,
            regression_prob=0.02,
            layout_overflows=0,
            confidence=0.92,
        )
        self.assertFalse(gate_res.admitted)
        self.assertIn("Safety score", gate_res.reasons[0])

    def test_admission_gate_rejection_on_regression_probability(self):
        gate_res = self.interceptor.evaluate_admission_gate(
            safety_score=0.95,
            regression_prob=0.08,
            layout_overflows=0,
            confidence=0.92,
        )
        self.assertFalse(gate_res.admitted)
        self.assertIn("Regression probability", gate_res.reasons[0])

    def test_admission_gate_rejection_on_layout_overflow(self):
        gate_res = self.interceptor.evaluate_admission_gate(
            safety_score=0.95,
            regression_prob=0.02,
            layout_overflows=1,
            confidence=0.92,
        )
        self.assertFalse(gate_res.admitted)
        self.assertIn("Layout overflow", gate_res.reasons[0])

    def test_30_step_simulation_trajectory_agentworld(self):
        payload = {"command": "mkdir -p /workspace/test_dir"}
        admitted, score, diag = self.interceptor.simulate_trajectory(
            action_type="system_command",
            action_payload=payload,
            lookahead_steps=30,
        )
        self.assertTrue(admitted)
        self.assertGreaterEqual(score, 0.90)
        self.assertEqual(diag["lookahead_steps"], 30)
        self.assertEqual(diag["steps_completed"], 30)
        self.assertGreaterEqual(diag["safety_score"], 0.90)
        self.assertLessEqual(diag["regression_probability"], 0.05)
        self.assertEqual(diag["layout_overflows"], 0)
        self.assertGreaterEqual(diag["simulation_confidence"], 0.85)

    def test_30_step_simulation_trajectory_webworld(self):
        payload = {
            "dom_update": {
                "tag": "div",
                "classes": ["p-4", "bg-gray-900", "text-white"],
                "styles": {"color": "#FFFFFF", "background": "#111827"},
                "text_content": "Valid Telemetry Card",
                "width": 400.0,
                "height": 100.0,
            }
        }
        admitted, score, diag = self.interceptor.simulate_trajectory(
            action_type="dom_update",
            action_payload=payload,
            lookahead_steps=30,
        )
        self.assertTrue(admitted)
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(diag["steps_completed"], 30)
        self.assertEqual(diag["layout_overflows"], 0)

    def test_rejection_of_dangerous_trajectory(self):
        payload = {"command": "rm -rf /"}
        admitted, score, diag = self.interceptor.simulate_trajectory(
            action_type="system_command",
            action_payload=payload,
            lookahead_steps=30,
        )
        self.assertFalse(admitted)
        self.assertLess(score, 0.50)
        self.assertEqual(diag["verdict"], "REJECTED_GATING_BREACH")

    def test_intercept_and_execute_conditional_callback(self):
        executed = []
        def callback_good():
            executed.append("good")
            return "SUCCESS"
        def callback_bad():
            executed.append("bad")
            return "SHOULD_NOT_RUN"
        admit_1, _, diag_1, res_1 = self.interceptor.intercept_and_execute(
            action_type="system_command",
            action_payload={"command": "echo verified"},
            execution_callback=callback_good,
        )
        self.assertTrue(admit_1)
        self.assertIn("good", executed)
        self.assertEqual(res_1, "SUCCESS")
        admit_2, _, diag_2, res_2 = self.interceptor.intercept_and_execute(
            action_type="system_command",
            action_payload={"command": "rm -rf /etc"},
            execution_callback=callback_bad,
        )
        self.assertFalse(admit_2)
        self.assertNotIn("bad", executed)
        self.assertIsNone(res_2)
        self.assertEqual(diag_2["execution_status"], "BLOCKED_BY_GATING")

    def test_metrics_tracking(self):
        self.interceptor.simulate_trajectory("system_command", {"command": "echo metric_check"})
        metrics = self.interceptor.get_metrics()
        self.assertIn("total_intercepted", metrics)
        self.assertIn("admission_rate_pct", metrics)
        self.assertGreater(metrics["total_intercepted"], 0)

if __name__ == "__main__":
    unittest.main()
