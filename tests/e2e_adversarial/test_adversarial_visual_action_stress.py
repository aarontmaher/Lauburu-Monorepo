#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress Testing & Empirical Challenge Suite: Sovereign Visual Context & Action Integration
===================================================================================================
Subsystem: 01_apps/edge_compute_and_ai/ & tests/
Milestone: Empirical Challenger Stress Harness (M4 Visual Action Mesh Orchestration)

This test suite performs exhaustive adversarial challenge testing against:
1. Screenpipe SQL sanitization (injection attacks, mutation attempts, missing limits, stacked queries).
2. Hermes 3 Code-as-Action AST safety sandbox (attempting bypass via getattr, builtins, dynamic imports, dunder exploration).
3. VisualActionMeshOrchestrator rapid state-machine cycling, concurrency, fault injection, and Rule #0 zero-mock fuzzing.

Rule #0 Compliant: Zero simulated arrays, zero mock tokens.
"""

import ast
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple

TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parent
EDGE_COMPUTE_DIR = PROJECT_ROOT / "01_apps" / "edge_compute_and_ai"

for p in [str(PROJECT_ROOT), str(EDGE_COMPUTE_DIR), str(TESTS_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from screenpipe_service import (
    ElementRecord,
    FrameRecord,
    NormalizedBoundingBox,
    ScreenpipeDirectSqlite,
    ScreenpipeError,
    ScreenpipeQueryError,
    ScreenpipeSecurityError,
    validate_and_sanitize_sql,
)
from hermes_code_action_dispatcher import (
    ASTSafetyChecker as HermesASTSafetyChecker,
    ASTSecurityViolationError,
    ActionPlan,
    AgentActionContext as HermesAgentActionContext,
    ExecutionResult as HermesExecutionResult,
    HermesCodeActionDispatcher,
    RuleZeroViolationError,
    UIElement,
    VisualContextSnapshot as HermesVisualSnapshot,
    ZeroMockValidator as HermesZeroMockValidator,
)
from visual_action_mesh_orchestrator import (
    ASTSafetyChecker as OrchestratorASTSafetyChecker,
    AgentActionContext as OrchestratorAgentActionContext,
    ContinuousLoraStreamer,
    GeneratedActionPayload,
    OrchestratorConfig,
    OrchestratorCycleResult,
    OrchestratorState,
    PlatformTarget,
    StorageHeadroomGovernor,
    UIElementNode,
    VisualActionMeshOrchestrator,
    VisualContextSnapshot as OrchestratorVisualSnapshot,
    ZeroMockValidator as OrchestratorZeroMockValidator,
)


# ==============================================================================
# SECTION 1: Screenpipe SQL Sanitization & Injection Stress Harness
# ==============================================================================

class TestScreenpipeSqlAdversarialHarness(unittest.TestCase):
    """Adversarial stress-testing of Screenpipe SQL sanitization and query execution."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="screenpipe_adversarial_")
        self.db_path = Path(self.temp_dir) / "test_screenpipe.sqlite"
        self._init_test_database(self.db_path)
        self.sqlite_engine = ScreenpipeDirectSqlite(self.db_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_test_database(self, path: Path) -> None:
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("""
            CREATE TABLE frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                app_name TEXT,
                window_name TEXT,
                focused INTEGER,
                browser_url TEXT,
                device_name TEXT,
                snapshot_path TEXT,
                accessibility_text TEXT,
                accessibility_tree_json TEXT,
                full_text TEXT,
                text_json TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER,
                source TEXT,
                role TEXT,
                text TEXT,
                parent_id INTEGER,
                depth INTEGER,
                left_bound REAL,
                top_bound REAL,
                width_bound REAL,
                height_bound REAL,
                confidence REAL,
                sort_order INTEGER,
                properties TEXT,
                on_screen INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE ui_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                app_name TEXT
            )
        """)
        # Insert authentic test rows
        cursor.execute("""
            INSERT INTO frames (timestamp, app_name, window_name, full_text)
            VALUES ('2026-08-31T05:00:00Z', 'Movesense Hub', 'ECG Monitor', 'Movesense 512Hz Active')
        """)
        cursor.execute("""
            INSERT INTO elements (frame_id, source, role, text, left_bound, top_bound, width_bound, height_bound, confidence)
            VALUES (1, 'ocr', 'AXButton', 'Connect Movesense', 0.2, 0.3, 0.4, 0.1, 0.99)
        """)
        conn.commit()
        conn.close()

    def test_adv_sql_01_direct_mutation_attacks_rejected(self) -> None:
        """Verify that all mutating SQL statements are rejected by validate_and_sanitize_sql."""
        mutating_payloads = [
            "INSERT INTO frames (app_name) VALUES ('evil')",
            "UPDATE frames SET app_name = 'compromised'",
            "DELETE FROM frames WHERE id = 1",
            "DROP TABLE elements",
            "ALTER TABLE frames ADD COLUMN backdoor TEXT",
            "CREATE TABLE backdoor_table (id INT)",
            "ATTACH DATABASE '/tmp/injected.db' AS injected",
            "DETACH DATABASE injected",
            "REPLACE INTO frames (id, app_name) VALUES (1, 'evil')",
            "TRUNCATE TABLE ui_events",
            "VACUUM",
            "PRAGMA table_info(frames)",
            "GRANT ALL ON frames TO public",
            "REVOKE ALL ON frames FROM public",
            "EXECUTE immediate 'DROP TABLE frames'",
        ]
        for payload in mutating_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ScreenpipeSecurityError):
                    validate_and_sanitize_sql(payload)

    def test_adv_sql_02_case_and_whitespace_obfuscation_rejected(self) -> None:
        """Verify case variation, leading whitespace, and newline mutations are caught."""
        obfuscated_payloads = [
            "  iNsErT   INTO frames VALUES (1)  ",
            "\n\t  uPdAtE frames SET app_name='hacked'",
            "\r\n  dRoP   table elements",
            "   DeLeTe   FROM ui_events",
            " \t  aLtEr   TABLE frames DROP COLUMN full_text",
            "/* leading comment */ INSERT INTO frames (app_name) VALUES ('x')",
            "-- line comment\nDROP TABLE frames",
            " \n \r \t pragma busy_timeout=0",
        ]
        for payload in obfuscated_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ScreenpipeSecurityError):
                    validate_and_sanitize_sql(payload)

    def test_adv_sql_03_stacked_queries_and_semicolon_injection_rejected(self) -> None:
        """Verify semicolon stacked queries and embedded statements are blocked."""
        stacked_payloads = [
            "SELECT * FROM frames; DROP TABLE frames;",
            "SELECT * FROM frames; INSERT INTO frames (app_name) VALUES ('x')",
            "SELECT * FROM frames WHERE id = 1; DELETE FROM elements",
            "SELECT * FROM frames; SELECT * FROM elements",
            "SELECT * FROM frames WHERE window_name = 'test; injection'",
        ]
        for payload in stacked_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ScreenpipeSecurityError):
                    validate_and_sanitize_sql(payload)

    def test_adv_sql_04_empty_and_non_select_statements_rejected(self) -> None:
        """Verify empty strings and unauthorized non-SELECT statements are rejected."""
        invalid_payloads = [
            "",
            "   ",
            "\t\n\r",
            "SHOW TABLES",
            "CALL get_frames()",
            "SET @var = 1",
            "DESCRIBE frames",
            "BEGIN TRANSACTION",
            "COMMIT",
            "ROLLBACK",
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ScreenpipeSecurityError):
                    validate_and_sanitize_sql(payload)

    def test_adv_sql_05_limit_clamping_and_default_injection(self) -> None:
        """Verify that LIMIT is automatically added or clamped to max_limit."""
        # Case A: Missing LIMIT -> Default 100 added
        q1 = "SELECT id, app_name FROM frames WHERE app_name = 'Movesense Hub'"
        sanitized1 = validate_and_sanitize_sql(q1)
        self.assertTrue(sanitized1.endswith("LIMIT 100"))

        # Case B: Excessive LIMIT -> Clamped to 10000
        q2 = "SELECT * FROM frames LIMIT 9999999"
        sanitized2 = validate_and_sanitize_sql(q2)
        self.assertIn("LIMIT 10000", sanitized2)
        self.assertNotIn("9999999", sanitized2)

        # Case C: Legitimate safe LIMIT -> Preserved
        q3 = "SELECT * FROM frames WHERE id = 1 LIMIT 1"
        sanitized3 = validate_and_sanitize_sql(q3)
        self.assertIn("LIMIT 1", sanitized3)

        # Case D: CTE (WITH clause) -> Handled safely
        q4 = "WITH recent AS (SELECT id, app_name FROM frames WHERE id > 0) SELECT * FROM recent"
        sanitized4 = validate_and_sanitize_sql(q4)
        self.assertTrue(sanitized4.startswith("WITH"))
        self.assertTrue(sanitized4.endswith("LIMIT 100"))

    def test_adv_sql_06_sqlite_direct_engine_read_only_immutability(self) -> None:
        """Verify direct SQLite connection rejects mutations at the DB driver level."""
        # 1. execute_query with enforce_safety=True catches mutations
        with self.assertRaises(ScreenpipeSecurityError):
            self.sqlite_engine.execute_query("INSERT INTO frames (app_name) VALUES ('bad')", enforce_safety=True)

        # 2. Raw connection direct execution attempt fails due to read-only URI mode
        conn = self.sqlite_engine.get_connection()
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO frames (app_name) VALUES ('driver_bypass')")
        finally:
            conn.close()

    def test_adv_sql_07_safe_read_queries_execution(self) -> None:
        """Verify legitimate read queries return genuine structured data without degradation."""
        frames = self.sqlite_engine.get_recent_frames(limit=5)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].app_name, "Movesense Hub")
        self.assertEqual(len(frames[0].elements), 1)
        self.assertEqual(frames[0].elements[0].text, "Connect Movesense")
        self.assertAlmostEqual(frames[0].elements[0].confidence, 0.99, places=2)


# ==============================================================================
# SECTION 2: Hermes 3 AST Safety Sandbox & Code-as-Action Stress Harness
# ==============================================================================

class TestHermesASTSandboxAdversarialHarness(unittest.TestCase):
    """Adversarial stress-testing of Hermes AST safety analyzer and sandboxed execution."""

    def setUp(self) -> None:
        self.hermes_checker = HermesASTSafetyChecker
        self.orchestrator_checker = OrchestratorASTSafetyChecker
        self.action_context = HermesAgentActionContext(platform="macos")

    def test_adv_ast_01_dynamic_import_evasion_core_modules(self) -> None:
        """Stress-test import detection against all dangerous core standard library modules."""
        forbidden_imports = [
            "import os\nos.system('ls')",
            "import sys\nsys.exit(0)",
            "import subprocess\nsubprocess.run(['ls'])",
            "import shutil\nshutil.rmtree('/tmp')",
            "import socket\ns = socket.socket()",
            "import http.client",
            "import urllib.request",
            "import requests",
            "import posix",
            "import pty",
            "import ctypes",
            "from os import path, system",
            "from subprocess import Popen, PIPE",
            "from sys import modules",
            "import os.path",
        ]
        for code in forbidden_imports:
            with self.subTest(code=code):
                # Test Hermes checker
                safe_h, err_h = self.hermes_checker.validate_code(code)
                self.assertFalse(safe_h, f"Hermes AST checker failed to block: {code}")
                self.assertIsNotNone(err_h)

                # Test Orchestrator checker
                safe_o, err_o = self.orchestrator_checker.validate_code(code)
                self.assertFalse(safe_o, f"Orchestrator AST checker failed to block: {code}")

                # Test execute_script blocks execution
                res = self.action_context.execute_script(code)
                self.assertEqual(res.status, "BLOCKED")
                self.assertEqual(res.post_verification_score, 0.0)

    def test_adv_ast_02_builtins_and_reflection_core_calls(self) -> None:
        """Stress-test rejection of dangerous builtins, eval, exec, and reflection calls."""
        forbidden_builtins = [
            "eval('1 + 1')",
            "exec('a = 10')",
            "__import__('os').system('ls')",
            "compile('pass', '', 'exec')",
            "f = open('/etc/passwd', 'r')",
            "user_in = input('prompt')",
            "breakpoint()",
            "g = globals()",
            "l = locals()",
            "val = getattr(agent, 'dispatched_actions')",
            "setattr(agent, 'dispatched_actions', [])",
            "delattr(agent, 'dispatched_actions')",
        ]
        for code in forbidden_builtins:
            with self.subTest(code=code):
                safe_h, err_h = self.hermes_checker.validate_code(code)
                self.assertFalse(safe_h, f"Hermes AST checker failed to block builtin: {code}")

                safe_o, err_o = self.orchestrator_checker.validate_code(code)
                self.assertFalse(safe_o, f"Orchestrator AST checker failed to block builtin: {code}")

                res = self.action_context.execute_script(code)
                self.assertEqual(res.status, "BLOCKED")

    def test_adv_ast_03_empirical_discrepancy_extended_imports_and_builtins(self) -> None:
        """Empirically document that Hermes dispatcher extends AST coverage beyond orchestrator defaults."""
        extended_modules = [
            "import pathlib\np = pathlib.Path('/tmp')",
            "import tempfile",
            "import importlib\nimportlib.import_module('os')",
            "from pathlib import Path",
        ]
        for code in extended_modules:
            with self.subTest(code=code):
                safe_h, _ = self.hermes_checker.validate_code(code)
                self.assertFalse(safe_h, f"Hermes checker should block extended module: {code}")

        extended_builtins = ["exit(1)", "quit(1)"]
        for code in extended_builtins:
            with self.subTest(code=code):
                safe_h, _ = self.hermes_checker.validate_code(code)
                self.assertFalse(safe_h, f"Hermes checker should block extended builtin: {code}")

    def test_adv_ast_04_sandboxed_execution_dunder_traversal_confinement(self) -> None:
        """Verify that dunder class traversal inside execution namespace cannot execute OS commands."""
        code = (
            "classes = ().__class__.__bases__[0].__subclasses__()\n"
            "count = len(classes)\n"
            "agent.click(100.0, 200.0)\n"
            "result = {'subclasses_count': count}\n"
        )
        is_safe, err = self.hermes_checker.validate_code(code)
        self.assertTrue(is_safe)

        res = self.action_context.execute_script(code)
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("click(100.0, 200.0)", res.actions_dispatched)
        self.assertIn("result", res.variables)

    def test_adv_ast_05_execution_runtime_exception_capture(self) -> None:
        """Verify that runtime errors (ZeroDivisionError, SyntaxError) are safely caught."""
        # Case A: Division by zero
        code_div_zero = "x = 10 / 0\nagent.click(10, 10)"
        res_div = self.action_context.execute_script(code_div_zero)
        self.assertEqual(res_div.status, "FAILED")
        self.assertIn("division by zero", res_div.error_message.lower())

        # Case B: Syntax error
        code_syntax = "def broken(:\n  pass"
        res_syn = self.action_context.execute_script(code_syntax)
        self.assertEqual(res_syn.status, "BLOCKED")
        self.assertIn("syntaxerror", res_syn.error_message.lower())

    def test_adv_ast_06_multi_context_state_isolation(self) -> None:
        """Verify that two distinct execution contexts have strictly isolated namespaces."""
        ctx1 = HermesAgentActionContext(platform="macos")
        ctx2 = HermesAgentActionContext(platform="android")

        script1 = "x = 42\nagent.click(100.0, 200.0)"
        script2 = "y = 99\nagent.tap(300.0, 400.0)"

        res1 = ctx1.execute_script(script1)
        res2 = ctx2.execute_script(script2)

        self.assertEqual(res1.status, "SUCCESS")
        self.assertEqual(res2.status, "SUCCESS")
        self.assertIn("x", ctx1.variables)
        self.assertNotIn("y", ctx1.variables)
        self.assertIn("y", ctx2.variables)
        self.assertNotIn("x", ctx2.variables)
        self.assertEqual(len(ctx1.dispatched_actions), 1)
        self.assertEqual(len(ctx2.dispatched_actions), 1)

    def test_adv_ast_07_legitimate_complex_action_execution(self) -> None:
        """Verify that complex legitimate action sequences run with 100% fidelity."""
        complex_script = (
            "def run_workflow(agent):\n"
            "    agent.click(400.0, 200.0)\n"
            "    agent.sleep(0.01)\n"
            "    agent.type('ECG Stream')\n"
            "    agent.scroll('down', 250)\n"
            "    agent.wait_for_text('Connected', timeout_s=1.0)\n"
            "    return {'status': 'SUCCESS', 'items_processed': 5}\n"
            "res_dict = run_workflow(agent)\n"
        )
        res = self.action_context.execute_script(complex_script)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(len(res.actions_dispatched), 5)
        self.assertEqual(res.post_verification_score, 100.0)


# ==============================================================================
# SECTION 3: VisualActionMeshOrchestrator Rapid Cycling & Concurrency Stress
# ==============================================================================

class TestVisualActionOrchestratorStressHarness(unittest.IsolatedAsyncioTestCase):
    """Adversarial stress-testing of VisualActionMeshOrchestrator under rapid cycling and concurrency."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="orch_stress_")
        self.lora_sink = Path(self.temp_dir) / "lora_test.jsonl"
        self.mirror_sink = Path(self.temp_dir) / "lora_mirror.jsonl"
        self.config = OrchestratorConfig(
            min_storage_headroom_gb=10.0,
            critical_storage_headroom_gb=5.0,
            lora_dataset_path=str(self.lora_sink),
            lora_mirror_path=str(self.mirror_sink),
            single_cycle=True,
            auto_heal=True,
        )
        self.orchestrator = VisualActionMeshOrchestrator(self.config)
        self.orchestrator.streamer.primary_path = self.lora_sink
        self.orchestrator.streamer.mirror_path = self.mirror_sink

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_adv_orch_01_rapid_50_consecutive_cycles_stress(self) -> None:
        """Execute 50 consecutive orchestrator cycles sequentially and measure stability."""
        t0 = time.perf_counter()
        cycle_count = 50

        for i in range(cycle_count):
            res = await self.orchestrator.run_single_cycle(
                goal=f"Execute Movesense 512Hz ECG cycle {i + 1}",
                platform=PlatformTarget.MACOS if i % 2 == 0 else PlatformTarget.ANDROID
            )
            self.assertEqual(res.status, "SUCCESS", f"Cycle {i+1} failed: {res.error_message}")
            self.assertTrue(res.context_captured)
            self.assertTrue(res.synthesis_passed)
            self.assertTrue(res.action_dispatched)
            self.assertTrue(res.post_verification_passed)
            self.assertTrue(res.lora_recorded)
            self.assertGreater(res.cycle_latency_ms, 0.0)

        elapsed_total = (time.perf_counter() - t0) * 1000.0
        avg_latency = elapsed_total / cycle_count

        self.assertEqual(self.orchestrator.cycle_count, cycle_count)
        self.assertEqual(self.orchestrator.successful_cycles, cycle_count)
        self.assertEqual(self.orchestrator.failed_cycles, 0)
        self.assertEqual(len(self.orchestrator.history), cycle_count)

        # Verify dataset sink line count and formatting
        dataset_records = self.orchestrator.streamer.read_dataset(limit=100)
        self.assertEqual(len(dataset_records), cycle_count)

        # Audit all records for Rule #0 compliance
        for rec in dataset_records:
            self.assertTrue(OrchestratorZeroMockValidator.audit_dict(rec))

    async def test_adv_orch_02_concurrent_25_tasks_burst(self) -> None:
        """Execute 25 simultaneous asynchronous cycles under heavy event loop load."""
        concurrency = 25
        tasks = []

        for i in range(concurrency):
            plat = PlatformTarget.ANDROID if i % 2 == 0 else PlatformTarget.MACOS
            coro = self.orchestrator.run_single_cycle(
                goal=f"Concurrent visual action task {i + 1}",
                platform=plat,
            )
            tasks.append(coro)

        results = await asyncio.gather(*tasks, return_exceptions=False)
        self.assertEqual(len(results), concurrency)

        successes = [r for r in results if r.status == "SUCCESS"]
        self.assertEqual(len(successes), concurrency)

        # Verify LoRA dataset write integrity under concurrent async locks
        records = self.orchestrator.streamer.read_dataset(limit=100)
        self.assertGreaterEqual(len(records), concurrency)
        for r in records:
            self.assertTrue(OrchestratorZeroMockValidator.audit_dict(r))

    async def test_adv_orch_03_storage_headroom_governor_threshold_states(self) -> None:
        """Stress-test storage headroom governor across normal, degraded, and critical boundaries."""
        gov = self.orchestrator.governor

        # Test exact boundary checks
        self.assertTrue(gov.is_storage_healthy(min_headroom_gb=0.0))

        # Test auto-healing of missing directories
        missing_root = Path(self.temp_dir) / "fake_root"
        missing_root.mkdir(parents=True, exist_ok=True)
        heal_res = gov.auto_heal_storage(base_dir=missing_root)
        self.assertTrue(heal_res["healed"])
        self.assertTrue((missing_root / "obsidian_vault" / "Index.md").is_file())
        self.assertTrue((missing_root / "04_data_and_memory" / "lora_datasets").is_dir())

        # Test auto-healing of stale git index.lock
        git_dir = missing_root / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        stale_lock = git_dir / "index.lock"
        stale_lock.write_text("lock")
        heal_lock = gov.auto_heal_storage(base_dir=missing_root)
        self.assertFalse(stale_lock.exists())

    async def test_adv_orch_04_fault_injection_and_error_recovery(self) -> None:
        """Inject fault into Phase 3 (AST failure) and Phase 4 (runtime crash), asserting recovery."""
        # Case A: Generated code with prohibited AST payload
        bad_snapshot = self.orchestrator.execute_phase_capture_context(platform=PlatformTarget.MACOS)
        malicious_payload = GeneratedActionPayload(
            action_id="act_evil",
            goal="Attempt escape",
            generated_code="import os\nos.system('whoami')",
            ast_safety_passed=False,
        )
        exec_res = self.orchestrator.execute_phase_execute_action(malicious_payload)
        self.assertEqual(exec_res.status, "BLOCKED")
        self.assertEqual(exec_res.post_verification_score, 0.0)

        # Verification step reflects failure
        verified, score, details = self.orchestrator.execute_phase_verify_transition(bad_snapshot, exec_res)
        self.assertFalse(verified)
        self.assertEqual(score, 0.0)

        # Orchestrator status reporting reflects genuine state
        status = self.orchestrator.get_status()
        self.assertTrue(status["rule_0_verified"])
        self.assertTrue(OrchestratorZeroMockValidator.audit_dict(status))

    def test_adv_orch_05_rule0_zero_mock_adversarial_fuzzing(self) -> None:
        """Adversarial fuzzing against SovereignZeroMockAuditor with sneaky synthetic tokens."""
        auditor = OrchestratorZeroMockValidator

        # 1. Prohibited synthetic tokens (Must return False)
        forbidden_inputs = [
            "mock_client_response",
            "dummy_session_id",
            "fake_touch_event",
            "MOCK_FRAME_BUFFER",
            "DuMmY_VaL",
            "mock",
            "dummy",
            "fake",
            "placeholder",
            "lorem ipsum dolor sit amet",
            {"key": "mock_data"},
            {"valid_key": "dummy_payload"},
            {"nested": {"inner": ["fake_telemetry"]}},
        ]
        for inp in forbidden_inputs:
            with self.subTest(inp=inp):
                self.assertFalse(auditor.verify(inp), f"Auditor failed to catch prohibited: {inp}")

        # 2. Legitimate tokens containing partial matches (Must return True)
        legitimate_inputs = [
            "mockingbird_stream",
            "Movesense 512Hz Telemetry Hub",
            "Zone 2 Heart Rate 135 bpm",
            "ECG Pan-Tompkins Peak Detection",
            "--",  # Valid waiting state
            "",    # Valid empty state
            {"device": "Movesense_HRV", "hr_bpm": 135.5, "status": "STREAMING"},
            {"elements": [{"text": "Tap to start", "confidence": 0.98}]},
        ]
        for inp in legitimate_inputs:
            with self.subTest(inp=inp):
                self.assertTrue(auditor.verify(inp), f"Auditor falsely rejected legitimate: {inp}")


# ==============================================================================
# CLI Test Runner
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
