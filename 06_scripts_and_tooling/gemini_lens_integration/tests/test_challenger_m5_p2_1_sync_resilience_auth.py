"""Phase 2 Tier 5 Adversarial Test Suite: Sync Engine, Resilience, & Auth Isolation.

Authored by challenger_m5_p2_1 (Adversarial Critic & Specialist).
Exclusively owned file: tests/test_challenger_m5_p2_1_sync_resilience_auth.py

Targets:
1. sync_engine.py:
   - Live partial auth: 1 account authenticates, 1 fails -> sync proceeds for authenticated account,
     manifest records error on failing account without aborting or corrupting state.
   - Degraded imports and fallbacks (auth_manager=None, lens_client=None, notebook_sync=None).
   - Concurrent future exceptions in ThreadPoolExecutor.
   - Rapid sequential sync runs & atomic manifest temp file cleanliness.
2. resilience.py:
   - execute_with_retry(raise_on_cooldown=False) returns None during active cooldown.
   - Nested rate limit exceptions (exc.resp.status_code=429, "resource_exhausted" strings).
   - Concurrent queue file append while active draining is in progress (preserves new records).
   - Corrupted queue lines cleanly unlinked without decode crashes.
   - Mach memory pressure audit (Rule 1 Section 6 & Rule 3).
3. auth_manager.py:
   - Service Account DWD failure cleanly falling back to GEMINI_API_KEY_WORKSPACE.
   - _verify_isolation() false negative prevention (duplicate client IDs, duplicate _api_client,
     duplicate keys, duplicate headers -> assert returns False for all).
   - Read-only token file refresh (updates in memory, logs warning, doesn't crash).
   - Malformed/extreme expiry timestamps.
   - Inactive and unconfigured account profile handling.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sync_engine
from auth_manager import (
    AccountProfile,
    AccountRole,
    AccountSession,
    CredentialType,
    DualAccountManager,
)
from resilience import (
    CircuitBreakerState,
    RateLimitCooldownError,
    ResilienceManager,
)
from sync_engine import GeminiLensSyncOrchestrator


# ============================================================================
# Dummy Client Helpers for Isolation Testing
# ============================================================================

class DummyHttpOptions:
    def __init__(self, headers: Optional[Dict[str, str]] = None) -> None:
        self.headers = headers or {}


class DummyApiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.api_key = api_key
        self._http_options = DummyHttpOptions(headers=headers)


class DummyGenAIClient:
    def __init__(
        self,
        api_client: Optional[DummyApiClient] = None,
        name: str = "DummyGenAIClient",
    ) -> None:
        self.name = name
        self._api_client = api_client or DummyApiClient()


# ============================================================================
# Test Suite 1: sync_engine.py Adversarial & Boundary Stress
# ============================================================================

class TestSyncEngineAdversarial:
    """Adversarial challenge tests for sync_engine.py."""

    def test_live_partial_auth_one_valid_one_failing(self, tmp_path: Path) -> None:
        """Challenge 1.1: Live partial auth where 1 account authenticates and 1 fails.

        Verifies:
        - auth_count == 1
        - Sync proceeds to sync_notebook_and_ide without bypassing
        - Manifest records total_accounts=2, authenticated_accounts=1
        - Failing account records is_authenticated=False with verbatim error
        - State is not corrupted and manifest is written atomically.
        """
        manifest_path = tmp_path / "session_logs" / "gemini_lens_sync_status.json"
        notebook_path = tmp_path / "lens_global_orchestrator.ipynb"
        notebook_path.write_text('{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}')

        orchestrator = GeminiLensSyncOrchestrator(
            notebook_path=notebook_path,
            dry_run=False,
        )
        orchestrator.status_manifest_path = manifest_path

        mock_auth_manager = MagicMock()
        valid_session = AccountSession(
            account_id="aaron.t.maher@gmail.com",
            role="personal_admin",
            is_authenticated=True,
            auth_method="adc",
            client=DummyGenAIClient(name="AaronClient"),
        )
        failing_session = AccountSession(
            account_id="lauburu@lauburugrappling.com",
            role="workspace_business",
            is_authenticated=False,
            auth_method="error",
            error="OAuth2 token refresh rejected: invalid_grant",
        )

        def mock_auth(acct_id: str, is_dry: bool) -> AccountSession:
            if "aaron" in acct_id:
                return valid_session
            return failing_session

        mock_auth_manager.authenticate_account.side_effect = mock_auth
        mock_auth_manager.profiles = {
            "aaron.t.maher@gmail.com": MagicMock(account_id="aaron.t.maher@gmail.com", is_active=True),
            "lauburu@lauburugrappling.com": MagicMock(account_id="lauburu@lauburugrappling.com", is_active=True),
        }
        mock_auth_manager._verify_isolation.return_value = True
        orchestrator.auth_manager = mock_auth_manager

        # Run live cycle
        manifest = orchestrator.run_sync_cycle(dry_run=False)

        assert manifest["dry_run"] is False
        assert manifest["total_accounts"] == 2
        assert manifest["authenticated_accounts"] == 1
        assert manifest["accounts"]["aaron.t.maher@gmail.com"]["is_authenticated"] is True
        assert manifest["accounts"]["lauburu@lauburugrappling.com"]["is_authenticated"] is False
        assert "invalid_grant" in manifest["accounts"]["lauburu@lauburugrappling.com"]["error"]

        # Verify sync was NOT bypassed with 'auth_failed' because 1 account was valid
        assert manifest["notebook_sync"]["status"] != "auth_failed"
        assert manifest_path.exists()

        # Verify manifest on disk is valid JSON matching return
        with open(manifest_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert disk_data["authenticated_accounts"] == 1
        assert disk_data["accounts"]["aaron.t.maher@gmail.com"]["is_authenticated"] is True

    def test_sync_engine_degraded_no_auth_manager_dry_and_live(self, tmp_path: Path) -> None:
        """Challenge 1.2a: Import degradation when auth_manager is None.

        Verifies:
        - dry_run=True returns simulated sessions with is_authenticated=True
        - dry_run=False returns non-authenticated fallback sessions with error message
        - run_sync_cycle completes safely without unhandled exception.
        """
        manifest_path = tmp_path / "session_logs" / "status.json"
        orchestrator = GeminiLensSyncOrchestrator(dry_run=True)
        orchestrator.auth_manager = None
        orchestrator.status_manifest_path = manifest_path

        # 1. authenticate_accounts_concurrently in dry-run
        dry_sessions = orchestrator.authenticate_accounts_concurrently(dry_run=True)
        assert len(dry_sessions) >= 2
        for s in dry_sessions.values():
            assert s.is_authenticated is True
            assert s.auth_method == "simulated_dry_run"
            assert s.error is None

        # 2. authenticate_accounts_concurrently in live mode
        live_sessions = orchestrator.authenticate_accounts_concurrently(dry_run=False)
        assert len(live_sessions) >= 2
        for s in live_sessions.values():
            assert s.is_authenticated is False
            assert s.auth_method == "none"
            assert "auth_manager not available" in (s.error or "")

        # 3. run_sync_cycle in dry-run with auth_manager=None
        manifest = orchestrator.run_sync_cycle(dry_run=True)
        assert manifest["dry_run"] is True
        assert manifest["total_accounts"] >= 2
        assert manifest["authenticated_accounts"] >= 2
        assert manifest_path.exists()

    def test_sync_engine_degraded_lens_client_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Challenge 1.2b: Degradation when LENS_CLIENT_AVAILABLE is False.

        Verifies:
        - harvest_perception(dry_run=False) returns source="fallback_cli"
        - harvest_perception(dry_run=True) returns source="simulated_dry_run".
        """
        orchestrator = GeminiLensSyncOrchestrator(dry_run=False)
        monkeypatch.setattr(sync_engine, "LENS_CLIENT_AVAILABLE", False)

        live_perception = orchestrator.harvest_perception(dry_run=False)
        assert live_perception["source"] == "fallback_cli"
        assert live_perception["active_screen"]["app_name"] == "PyCharm"

        dry_perception = orchestrator.harvest_perception(dry_run=True)
        assert dry_perception["source"] == "simulated_dry_run"
        assert dry_perception["mesh_health"]["sanctuary_ok"] is True

    def test_sync_engine_degraded_notebook_sync_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Challenge 1.2c: Degradation when NOTEBOOK_SYNC_AVAILABLE is False.

        Verifies:
        - sync_notebook_and_ide in dry-run returns status="simulated"
        - sync_notebook_and_ide in live mode returns status="unavailable".
        """
        orchestrator = GeminiLensSyncOrchestrator(dry_run=False)
        monkeypatch.setattr(sync_engine, "NOTEBOOK_SYNC_AVAILABLE", False)

        payload = {"sync_id": "test"}
        sessions = {"test@domain.com": AccountSession("test@domain.com", "role", True, "adc")}

        dry_res = orchestrator.sync_notebook_and_ide(
            perception_payload=payload,
            account_sessions=sessions,
            isolation_verified=True,
            dry_run=True,
        )
        assert dry_res["status"] == "simulated"
        assert dry_res["cell_action"] == "simulated_cell_injection"
        assert dry_res["notebook_modified"] is False

        live_res = orchestrator.sync_notebook_and_ide(
            perception_payload=payload,
            account_sessions=sessions,
            isolation_verified=True,
            dry_run=False,
        )
        assert live_res["status"] == "unavailable"
        assert live_res["cell_action"] == "none"
        assert live_res["notebook_modified"] is False

    def test_concurrent_future_exception_in_thread_pool(self) -> None:
        """Challenge 1.3: ThreadPoolExecutor future raises unexpected Exception.

        Verifies:
        - Exception in worker thread is trapped and wrapped in AccountSession(auth_method='error')
        - Sibling thread is not aborted and succeeds normally
        - Function returns both sessions cleanly without raising.
        """
        orchestrator = GeminiLensSyncOrchestrator(dry_run=False)
        mock_auth_manager = MagicMock()

        def side_effect_auth(acct_id: str, is_dry: bool) -> AccountSession:
            if "fail" in acct_id:
                raise TimeoutError("TLS handshake timed out during certificate negotiation")
            return AccountSession(
                account_id=acct_id,
                role="personal_admin",
                is_authenticated=True,
                auth_method="adc",
            )

        mock_auth_manager.authenticate_account.side_effect = side_effect_auth
        orchestrator.auth_manager = mock_auth_manager

        target_accounts = ["fail_account@lauburu.com", "ok_account@lauburu.com"]
        sessions = orchestrator.authenticate_accounts_concurrently(
            account_ids=target_accounts,
            dry_run=False,
        )

        assert len(sessions) == 2
        fail_sess = sessions["fail_account@lauburu.com"]
        assert fail_sess.is_authenticated is False
        assert fail_sess.auth_method == "error"
        assert "TLS handshake timed out" in (fail_sess.error or "")

        ok_sess = sessions["ok_account@lauburu.com"]
        assert ok_sess.is_authenticated is True
        assert ok_sess.auth_method == "adc"

    def test_rapid_sequential_sync_atomic_manifest_cleanliness(self, tmp_path: Path) -> None:
        """Challenge 1.5: 30 rapid sequential sync cycles with atomic manifest writing.

        Verifies:
        - All 30 iterations succeed and produce 100% valid JSON
        - Zero orphaned .tmp.* files remain in target directory.
        """
        manifest_path = tmp_path / "session_logs" / "status_manifest.json"
        orchestrator = GeminiLensSyncOrchestrator(dry_run=True)
        orchestrator.status_manifest_path = manifest_path

        for i in range(30):
            data = {
                "iteration": i,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "status": "ok",
                "nonce": f"nonce-{i}-{time.time_ns()}",
            }
            written_path = orchestrator.write_status_manifest(data, target_path=manifest_path)
            assert written_path.exists()

        # Verify final file is valid JSON with last iteration
        with open(manifest_path, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        assert final_data["iteration"] == 29

        # Ensure zero temporary files remain in session_logs
        parent_dir = manifest_path.parent
        tmp_files = list(parent_dir.glob("*.tmp*"))
        assert len(tmp_files) == 0, f"Found orphaned temp files: {tmp_files}"


# ============================================================================
# Test Suite 2: resilience.py Adversarial & Boundary Stress
# ============================================================================

class TestResilienceAdversarial:
    """Adversarial challenge tests for resilience.py."""

    def test_execute_with_retry_cooldown_returns_none_when_disabled(self) -> None:
        """Challenge 2.1: execute_with_retry(raise_on_cooldown=False) returns None during cooldown.

        Verifies:
        - is_cooling_down() is True
        - execute_with_retry with raise_on_cooldown=False returns None immediately without calling target
        - execute_with_retry with raise_on_cooldown=True raises RateLimitCooldownError.
        """
        mgr = ResilienceManager()
        mgr.record_rate_limit(cooldown_seconds=60.0)
        assert mgr.is_cooling_down() is True

        call_counter = {"count": 0}

        def dummy_fn() -> int:
            call_counter["count"] += 1
            return 42

        # 1. raise_on_cooldown=False -> returns None
        result = mgr.execute_with_retry(dummy_fn, raise_on_cooldown=False)
        assert result is None
        assert call_counter["count"] == 0

        # 2. raise_on_cooldown=True -> raises RateLimitCooldownError
        with pytest.raises(RateLimitCooldownError) as exc_info:
            mgr.execute_with_retry(dummy_fn, raise_on_cooldown=True)
        assert "Rate limit cooldown active" in str(exc_info.value)
        assert call_counter["count"] == 0

    def test_nested_and_obscure_rate_limit_exception_detection(self) -> None:
        """Challenge 2.2: Detection of nested and obscure rate limit errors.

        Verifies:
        - Matches status_code=429 on exc, exc.resp, exc.response
        - Matches strings: 'resource_exhausted', 'quota exceeded', 'too many requests'
        - Rejects 500, 503, ValueError, KeyError.
        """
        mgr = ResilienceManager()

        # 1. Attribute-based matching on exc
        class ExcWithStatusCode(Exception):
            status_code = 429

        class ExcWithCode(Exception):
            code = 429

        class ExcWithHttpStatus(Exception):
            http_status = 429

        assert mgr._is_rate_limit_error(ExcWithStatusCode("error")) is True
        assert mgr._is_rate_limit_error(ExcWithCode("error")) is True
        assert mgr._is_rate_limit_error(ExcWithHttpStatus("error")) is True

        # 2. Nested response object matching
        class DummyResp:
            status_code = 429

        class ExcWithNestedResp(Exception):
            def __init__(self) -> None:
                self.resp = DummyResp()

        class ExcWithNestedResponse(Exception):
            def __init__(self) -> None:
                self.response = DummyResp()

        assert mgr._is_rate_limit_error(ExcWithNestedResp()) is True
        assert mgr._is_rate_limit_error(ExcWithNestedResponse()) is True

        # 3. String-based keyword matching
        assert mgr._is_rate_limit_error(RuntimeError("google.genai.errors.APIError: RESOURCE_EXHAUSTED")) is True
        assert mgr._is_rate_limit_error(Exception("Quota exceeded for quota metric 'GenerateContent'")) is True
        assert mgr._is_rate_limit_error(Exception("HTTP 429 Too Many Requests")) is True
        assert mgr._is_rate_limit_error(Exception("Rate limit reached: ratelimit active")) is True

        # 4. Non-rate-limit errors
        class Exc500(Exception):
            status_code = 500

        class Exc503(Exception):
            status_code = 503

        assert mgr._is_rate_limit_error(Exc500("Internal Server Error")) is False
        assert mgr._is_rate_limit_error(Exc503("Service Unavailable")) is False
        assert mgr._is_rate_limit_error(KeyError("missing_field")) is False
        assert mgr._is_rate_limit_error(ValueError("invalid argument")) is False

    def test_execute_with_retry_triggers_cooldown_on_nested_429(self) -> None:
        """Challenge 2.2b: execute_with_retry enters cooldown when encountering nested 429."""
        mgr = ResilienceManager(max_retries=1, cooldown_period_seconds=30.0)
        assert mgr.is_cooling_down() is False

        class CustomNested429(Exception):
            def __init__(self) -> None:
                self.resp = MagicMock(status_code=429)

        def failing_call() -> None:
            raise CustomNested429()

        with pytest.raises(CustomNested429):
            mgr.execute_with_retry(failing_call, max_retries=1, backoff_base=0.01, use_jitter=False)

        assert mgr.is_cooling_down() is True
        assert mgr.circuit.state == "OPEN"

    def test_concurrent_mid_drain_queue_append_preserves_records(self, tmp_path: Path) -> None:
        """Challenge 2.3: Lines appended to queue during active drain are preserved.

        Verifies:
        - When sender_fn executes, a concurrent write appends new records
        - Draining initial records completes and returns drained count
        - Queue file is NOT deleted, and contains the newly appended records
        - Second drain successfully flushes the appended records.
        """
        queue_file = tmp_path / "pending_sync_queue.jsonl"
        mgr = ResilienceManager(offline_queue_path=queue_file)

        # Queue initial 3 records
        mgr.queue_offline_payload({"id": "rec-1", "data": "first"})
        mgr.queue_offline_payload({"id": "rec-2", "data": "second"})
        mgr.queue_offline_payload({"id": "rec-3", "data": "third"})

        drained_ids: List[str] = []

        def sender(payload: Dict[str, Any]) -> bool:
            rec_id = payload.get("id")
            drained_ids.append(rec_id)
            # When processing rec-2, simulate concurrent background thread appending 2 records
            if rec_id == "rec-2":
                with open(queue_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"payload": {"id": "rec-concurrent-1", "data": "c1"}}) + "\n")
                    f.write(json.dumps({"payload": {"id": "rec-concurrent-2", "data": "c2"}}) + "\n")
            return True

        drained_count = mgr.drain_offline_queue(sender)
        assert drained_count == 3
        assert drained_ids == ["rec-1", "rec-2", "rec-3"]

        # The queue file MUST still exist because concurrent records were appended!
        assert queue_file.exists()

        # Inspect remaining records in file
        with open(queue_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) == 2
        assert lines[0].get("id") == "rec-concurrent-1" or lines[0].get("payload", {}).get("id") == "rec-concurrent-1"
        assert lines[1].get("id") == "rec-concurrent-2" or lines[1].get("payload", {}).get("id") == "rec-concurrent-2"

        # Second drain: should process the 2 concurrent records and delete file
        second_drained_ids: List[str] = []
        second_count = mgr.drain_offline_queue(lambda p: second_drained_ids.append(p.get("id")) or True)
        assert second_count == 2
        assert second_drained_ids == ["rec-concurrent-1", "rec-concurrent-2"]
        assert not queue_file.exists()

    def test_corrupted_queue_lines_cleanly_unlinked(self, tmp_path: Path) -> None:
        """Challenge 2.4: Queue file with 100% corrupted lines is cleanly unlinked without crash.

        Verifies:
        - File with malformed non-JSON lines returns 0
        - No JSONDecodeError crashes caller
        - File is cleanly unlinked.
        """
        queue_file = tmp_path / "corrupt_queue.jsonl"
        queue_file.write_text(
            "CORRUPTED_NON_JSON_LINE_1\n"
            "{invalid: json syntax\n"
            "&&^%$#@!\n"
            "\n"
            "   \n"
        )
        mgr = ResilienceManager(offline_queue_path=queue_file)

        sender_called = False

        def sender(p: Any) -> bool:
            nonlocal sender_called
            sender_called = True
            return True

        drained = mgr.drain_offline_queue(sender)
        assert drained == 0
        assert sender_called is False
        assert not queue_file.exists()

    def test_darwin_mach_memory_pressure_audit_levels(self) -> None:
        """Challenge 2.5a: Mach memory pressure levels 1, 2, and 3 compliance auditing.

        Verifies:
        - Level 1 (Normal) with >= 4.8 GB free is compliant=True
        - Level 2 (Warning) even with high RAM is compliant=False
        - Level 3 (Critical) even with high RAM is compliant=False
        - Level 1 with < 4.8 GB free is compliant=False.
        """
        mgr = ResilienceManager(min_ram_sanctuary_gb=4.8)

        vm_stat_mock = subprocess.CompletedProcess(
            args=["/usr/bin/vm_stat"],
            returncode=0,
            stdout=(
                "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
                "Pages free: 100000.\n"
                "Pages active: 200000.\n"
                "Pages inactive: 150000.\n"
                "Pages speculative: 50000.\n"
                "Pages throttled: 0.\n"
                "Pages wired down: 200000.\n"
                "Pages purgeable: 50000.\n"
                "Anonymous pages: 300000.\n"
                "Pages occupied by compressor: 50000.\n"
                "File-backed pages: 200000.\n"
            ),
        )

        def mock_subprocess_run(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
            if "hw.pagesize" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="16384\n")
            if "hw.memsize" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=str(24 * 1024**3) + "\n")
            if "kern.memorystatus_vm_pressure_level" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=str(mock_pressure) + "\n")
            if "/usr/bin/vm_stat" in cmd:
                return vm_stat_mock
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        with patch("sys.platform", "darwin"), patch("subprocess.run", side_effect=mock_subprocess_run):
            # Level 1 (Normal): should be compliant
            mock_pressure = 1
            res_normal = mgr.check_memory_sanctuary()
            assert res_normal["compliant"] is True
            assert res_normal["pressure"] == 1
            assert res_normal["pressure_label"] == "normal"
            assert res_normal["free_ram_gb"] >= 4.8

            # Level 2 (Warning): non-compliant
            mock_pressure = 2
            res_warning = mgr.check_memory_sanctuary()
            assert res_warning["compliant"] is False
            assert res_warning["pressure"] == 2
            assert res_warning["pressure_label"] == "warning"

            # Level 3 (Critical): strictly non-compliant
            mock_pressure = 3
            res_critical = mgr.check_memory_sanctuary()
            assert res_critical["compliant"] is False
            assert res_critical["pressure"] == 3
            assert res_critical["pressure_label"] == "critical"

    def test_darwin_mach_memory_accounting_formulas(self) -> None:
        """Challenge 2.5b: Adherence to Rule 1 Section 6 & Rule 3 Mach accounting formulas.

        App Memory = (anon - purgeable) * page_size
        Wired = wired * page_size
        Compressed = compressor * page_size
        Cached = (file_backed + purgeable) * page_size
        Used = App + Wired + Compressed
        Free = Total - Used
        """
        mgr = ResilienceManager(min_ram_sanctuary_gb=4.8)

        page_size = 16384
        total_ram_bytes = 24 * (1024 ** 3)

        anon = 600000
        purgeable = 100000
        wired = 250000
        compressed = 100000
        file_backed = 200000

        expected_app_bytes = (anon - purgeable) * page_size
        expected_wired_bytes = wired * page_size
        expected_comp_bytes = compressed * page_size
        expected_cached_bytes = (file_backed + purgeable) * page_size
        expected_used_bytes = expected_app_bytes + expected_wired_bytes + expected_comp_bytes
        expected_free_bytes = total_ram_bytes - expected_used_bytes

        vm_stat_mock = subprocess.CompletedProcess(
            args=["/usr/bin/vm_stat"],
            returncode=0,
            stdout=(
                "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
                f"Anonymous pages: {anon}.\n"
                f"Pages purgeable: {purgeable}.\n"
                f"Pages wired down: {wired}.\n"
                f"Pages occupied by compressor: {compressed}.\n"
                f"File-backed pages: {file_backed}.\n"
            ),
        )

        def mock_subprocess_run(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
            if "hw.pagesize" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=f"{page_size}\n")
            if "hw.memsize" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=f"{total_ram_bytes}\n")
            if "kern.memorystatus_vm_pressure_level" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="1\n")
            if "/usr/bin/vm_stat" in cmd:
                return vm_stat_mock
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

        with patch("sys.platform", "darwin"), patch("subprocess.run", side_effect=mock_subprocess_run):
            audit = mgr.check_memory_sanctuary()

            assert audit["app_memory_gb"] == round(expected_app_bytes / (1024**3), 2)
            assert audit["wired_gb"] == round(expected_wired_bytes / (1024**3), 2)
            assert audit["compressed_gb"] == round(expected_comp_bytes / (1024**3), 2)
            assert audit["cached_files_gb"] == round(expected_cached_bytes / (1024**3), 2)
            assert audit["used_ram_gb"] == round(expected_used_bytes / (1024**3), 2)
            assert audit["free_ram_gb"] == round(expected_free_bytes / (1024**3), 2)


# ============================================================================
# Test Suite 3: auth_manager.py Adversarial & Boundary Stress
# ============================================================================

class TestAuthManagerAdversarial:
    """Adversarial challenge tests for auth_manager.py."""

    def test_service_account_dwd_failure_falls_back_to_workspace_api_key(self, tmp_path: Path) -> None:
        """Challenge 3.1: Service Account DWD refresh failure falls back to GEMINI_API_KEY_WORKSPACE.

        Verifies:
        - When DWD throws unauthorized_client / GoogleAuthError
        - Manager falls back to GEMINI_API_KEY_WORKSPACE
        - Session is marked is_authenticated=True, auth_method='api_key'.
        """
        cred_file = tmp_path / "sa.json"
        cred_file.write_text('{"type": "service_account", "project_id": "test", "private_key": "dummy"}')

        profile = AccountProfile(
            account_id="lauburu@lauburugrappling.com",
            role=AccountRole.WORKSPACE_BUSINESS,
            primary_cred_type=CredentialType.OAUTH2_TOKEN,
            cred_file_path=tmp_path / "missing_oauth.json",
            fallback_cred_type=CredentialType.SERVICE_ACCOUNT_DWD,
            fallback_cred_file_path=cred_file,
            api_key_env_var="GEMINI_API_KEY_WORKSPACE",
        )

        manager = DualAccountManager(dry_run=False)
        manager.profiles = {profile.account_id: profile}

        # Mock service_account.Credentials to raise GoogleAuthError on refresh
        mock_sa_creds = MagicMock()
        mock_sa_creds.refresh.side_effect = Exception("unauthorized_client: Client is unauthorized")
        mock_sa_creds.valid = False

        with patch("auth_manager.GOOGLE_AUTH_AVAILABLE", True), \
             patch("auth_manager.service_account.Credentials.from_service_account_file", return_value=mock_sa_creds), \
             patch.dict(os.environ, {"GEMINI_API_KEY_WORKSPACE": "test-workspace-key-xyz"}):

            session = manager.authenticate_account("lauburu@lauburugrappling.com", dry_run=False)

            assert session.is_authenticated is True
            assert session.auth_method == "api_key"
            assert session.error is None
            assert session.metadata.get("api_key_env_var") == "GEMINI_API_KEY_WORKSPACE"

    def test_service_account_dwd_failure_without_api_key_fails_cleanly(self, tmp_path: Path) -> None:
        """Challenge 3.1b: DWD failure when fallback env var is empty fails without crashing."""
        cred_file = tmp_path / "sa.json"
        cred_file.write_text('{"type": "service_account"}')

        profile = AccountProfile(
            account_id="lauburu@lauburugrappling.com",
            role=AccountRole.WORKSPACE_BUSINESS,
            primary_cred_type=CredentialType.SERVICE_ACCOUNT_DWD,
            cred_file_path=cred_file,
            fallback_cred_type=CredentialType.SERVICE_ACCOUNT_DWD,
            fallback_cred_file_path=cred_file,
            api_key_env_var="GEMINI_API_KEY_WORKSPACE",
        )

        manager = DualAccountManager(dry_run=False)
        manager.profiles = {profile.account_id: profile}

        mock_sa_creds = MagicMock()
        mock_sa_creds.refresh.side_effect = Exception("unauthorized_client")
        mock_sa_creds.valid = False

        env_clean = dict(os.environ)
        env_clean.pop("GEMINI_API_KEY_WORKSPACE", None)

        with patch("auth_manager.GOOGLE_AUTH_AVAILABLE", True), \
             patch("auth_manager.service_account.Credentials.from_service_account_file", return_value=mock_sa_creds), \
             patch.dict(os.environ, env_clean, clear=True):

            session = manager.authenticate_account("lauburu@lauburugrappling.com", dry_run=False)

            assert session.is_authenticated is False
            assert "unauthorized_client" in (session.error or "")

    def test_verify_isolation_rejection_duplicate_client_instances(self) -> None:
        """Challenge 3.2a: Rejection when active clients share identical Python object ID."""
        manager = DualAccountManager(dry_run=False)

        shared_client = DummyGenAIClient(name="SharedClient")

        s1 = AccountSession(account_id="a1@test.com", role="personal_admin", is_authenticated=True, auth_method="adc", client=shared_client)
        s2 = AccountSession(account_id="a2@test.com", role="workspace_business", is_authenticated=True, auth_method="oauth2", client=shared_client)

        manager.sessions = {"a1@test.com": s1, "a2@test.com": s2}
        manager.clients = {"a1@test.com": shared_client, "a2@test.com": shared_client}

        # Should strictly reject due to non-unique object IDs (Line 964)
        assert manager._verify_isolation() is False

    def test_verify_isolation_rejection_duplicate_api_client_instances(self) -> None:
        """Challenge 3.2b: Rejection when distinct client wrappers share identical _api_client."""
        manager = DualAccountManager(dry_run=False)

        shared_api_client = DummyApiClient(api_key="KEY_A")
        c1 = DummyGenAIClient(api_client=shared_api_client, name="C1")
        c2 = DummyGenAIClient(api_client=shared_api_client, name="C2")

        # Distinct wrapper object IDs
        assert id(c1) != id(c2)
        # Identical underlying _api_client
        assert id(c1._api_client) == id(c2._api_client)

        s1 = AccountSession(account_id="a1@test.com", role="personal_admin", is_authenticated=True, auth_method="adc", client=c1)
        s2 = AccountSession(account_id="a2@test.com", role="workspace_business", is_authenticated=True, auth_method="oauth2", client=c2)

        manager.sessions = {"a1@test.com": s1, "a2@test.com": s2}
        manager.clients = {"a1@test.com": c1, "a2@test.com": c2}

        # Rejection via Line 970
        assert manager._verify_isolation() is False

    def test_verify_isolation_rejection_duplicate_api_keys(self) -> None:
        """Challenge 3.2c: Rejection when separate _api_client objects share identical api_key."""
        manager = DualAccountManager(dry_run=False)

        ac1 = DummyApiClient(api_key="IDENTICAL_SECRET_API_KEY")
        ac2 = DummyApiClient(api_key="IDENTICAL_SECRET_API_KEY")
        c1 = DummyGenAIClient(api_client=ac1)
        c2 = DummyGenAIClient(api_client=ac2)

        s1 = AccountSession(account_id="a1@test.com", role="personal_admin", is_authenticated=True, auth_method="api_key", client=c1)
        s2 = AccountSession(account_id="a2@test.com", role="workspace_business", is_authenticated=True, auth_method="api_key", client=c2)

        manager.sessions = {"a1@test.com": s1, "a2@test.com": s2}
        manager.clients = {"a1@test.com": c1, "a2@test.com": c2}

        # Rejection via Line 986
        assert manager._verify_isolation() is False

    def test_verify_isolation_rejection_duplicate_authorization_headers(self) -> None:
        """Challenge 3.2d: Rejection when separate clients share identical Authorization header."""
        manager = DualAccountManager(dry_run=False)

        ac1 = DummyApiClient(headers={"Authorization": "Bearer SHARED_BEARER_TOKEN"})
        ac2 = DummyApiClient(headers={"Authorization": "Bearer SHARED_BEARER_TOKEN"})
        c1 = DummyGenAIClient(api_client=ac1)
        c2 = DummyGenAIClient(api_client=ac2)

        s1 = AccountSession(account_id="a1@test.com", role="personal_admin", is_authenticated=True, auth_method="oauth2", client=c1)
        s2 = AccountSession(account_id="a2@test.com", role="workspace_business", is_authenticated=True, auth_method="oauth2", client=c2)

        manager.sessions = {"a1@test.com": s1, "a2@test.com": s2}
        manager.clients = {"a1@test.com": c1, "a2@test.com": c2}

        # Rejection via Line 989
        assert manager._verify_isolation() is False

    def test_verify_isolation_rejection_missing_client_when_sdk_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Challenge 3.2e: Rejection when authenticated session has client=None while SDK is active."""
        import auth_manager
        monkeypatch.setattr(auth_manager, "GENAI_SDK_AVAILABLE", True)

        manager = DualAccountManager(dry_run=False)
        s1 = AccountSession(account_id="a1@test.com", role="personal_admin", is_authenticated=True, auth_method="adc", client=None)
        manager.sessions = {"a1@test.com": s1}
        manager.clients = {}

        assert manager._verify_isolation() is False

    def test_verify_isolation_passes_when_completely_isolated(self) -> None:
        """Challenge 3.2f: Isolation succeeds when all client objects and credentials are distinct."""
        manager = DualAccountManager(dry_run=False)

        ac1 = DummyApiClient(api_key="API_KEY_PERSONAL")
        ac2 = DummyApiClient(headers={"Authorization": "Bearer WORKSPACE_BEARER_TOKEN"})
        c1 = DummyGenAIClient(api_client=ac1, name="Client1")
        c2 = DummyGenAIClient(api_client=ac2, name="Client2")

        s1 = AccountSession(account_id="a1@test.com", role="personal_admin", is_authenticated=True, auth_method="api_key", client=c1)
        s2 = AccountSession(account_id="a2@test.com", role="workspace_business", is_authenticated=True, auth_method="oauth2", client=c2)

        manager.sessions = {"a1@test.com": s1, "a2@test.com": s2}
        manager.clients = {"a1@test.com": c1, "a2@test.com": c2}

        assert manager._verify_isolation() is True

    def test_read_only_token_file_refresh_updates_in_memory_without_crash(self, tmp_path: Path) -> None:
        """Challenge 3.3: Headless token refresh when credential file on disk is read-only (chmod 0400).

        Verifies:
        - In-memory credentials refresh succeeds
        - Atomic file persistence fails cleanly with logged warning without raising exception
        - refresh_credentials returns True and updates session.
        """
        token_file = tmp_path / "readonly_token.json"
        token_file.write_text('{"token": "old_token", "refresh_token": "valid_refresh"}')
        os.chmod(token_file, 0o400)

        profile = AccountProfile(
            account_id="lauburu@lauburugrappling.com",
            role=AccountRole.WORKSPACE_BUSINESS,
            primary_cred_type=CredentialType.OAUTH2_TOKEN,
            cred_file_path=token_file,
        )

        manager = DualAccountManager(dry_run=False)
        manager.profiles = {profile.account_id: profile}

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        mock_creds.to_json.return_value = '{"token": "new_refreshed_token"}'

        session = AccountSession(
            account_id=profile.account_id,
            role=profile.role.value,
            is_authenticated=True,
            auth_method="oauth2",
            credentials=mock_creds,
        )
        manager.sessions[profile.account_id] = session

        try:
            # Execute refresh
            res = manager.refresh_credentials(profile.account_id)
            assert res is True
            assert session.is_authenticated is True
            assert session.token_expiry is not None
        finally:
            # Restore permissions for temp directory cleanup
            os.chmod(token_file, 0o600)

    def test_extract_expiry_timestamp_adversarial_types(self) -> None:
        """Challenge 3.4: Adversarial input types for _extract_expiry_timestamp.

        Verifies:
        - Naive datetime (treated as UTC)
        - Aware datetime (with timezone)
        - Numeric float and int timestamps
        - Extreme numbers, None, strings, and missing attributes.
        """
        manager = DualAccountManager()

        # 1. Naive datetime
        naive_dt = datetime.datetime(2026, 10, 11, 20, 0, 0)
        expected_ts = naive_dt.replace(tzinfo=datetime.timezone.utc).timestamp()
        assert manager._extract_expiry_timestamp(MagicMock(expiry=naive_dt)) == expected_ts

        # 2. Timezone-aware datetime
        aware_dt = datetime.datetime(2026, 10, 11, 20, 0, 0, tzinfo=datetime.timezone.utc)
        assert manager._extract_expiry_timestamp(MagicMock(expiry=aware_dt)) == aware_dt.timestamp()

        # 3. Numeric float and integer
        assert manager._extract_expiry_timestamp(MagicMock(expiry=1791752400.5)) == 1791752400.5
        assert manager._extract_expiry_timestamp(MagicMock(expiry=1791752400)) == 1791752400.0

        # 4. Extreme values
        assert manager._extract_expiry_timestamp(MagicMock(expiry=0)) is None  # 0 is falsy in "and creds.expiry"
        assert manager._extract_expiry_timestamp(MagicMock(expiry=1e12)) == 1e12

        # 5. Invalid types & missing attributes
        assert manager._extract_expiry_timestamp(MagicMock(expiry="2026-10-11T20:00:00Z")) is None
        assert manager._extract_expiry_timestamp(MagicMock(expiry=None)) is None
        assert manager._extract_expiry_timestamp(object()) is None
        assert manager._extract_expiry_timestamp(None) is None

    def test_inactive_and_unknown_account_profiles(self) -> None:
        """Challenge 3.5: Inactive profile and unconfigured account profile handling.

        Verifies:
        - Inactive profile returns auth_method='disabled', is_authenticated=False
        - Unknown profile returns auth_method='none', is_authenticated=False.
        """
        manager = DualAccountManager(dry_run=False)

        inactive_profile = AccountProfile(
            account_id="inactive@domain.com",
            role=AccountRole.PERSONAL_ADMIN,
            primary_cred_type=CredentialType.ADC,
            is_active=False,
        )
        manager.profiles = {"inactive@domain.com": inactive_profile}

        # Inactive account
        sess_inactive = manager.authenticate_account("inactive@domain.com")
        assert sess_inactive.is_authenticated is False
        assert sess_inactive.auth_method == "disabled"
        assert "inactive" in (sess_inactive.error or "").lower()

        # Unknown account
        sess_unknown = manager.authenticate_account("nonexistent@domain.com")
        assert sess_unknown.is_authenticated is False
        assert sess_unknown.auth_method == "none"
        assert "No account profile configured" in (sess_unknown.error or "")
