"""Milestone 1 Challenger Stress Test Suite.

Empirical verification and adversarial stress-testing for Milestone 1 remediations:
1. Concurrency & Thread-Safety: Multi-threaded & coroutine authentication, RLock protection, dictionary mutation safety under reader/writer contention.
2. Memory Isolation & Authorization Headers: Verify client instances, underlying _api_client separation, distinct authorization headers, zero ambient key bleed.
3. Ambient Independence: Flawless authentication and isolated client instantiation when ambient GEMINI_API_KEY is unset.
4. Primary API Key Support: Live mode handling for primary_cred_type == CredentialType.API_KEY.
5. Atomic Token File Persistence: Mode 0600 permissions and atomic replacement.
6. CLI & Stderr Logging: Clean stdout JSON and --account filtering.
7. Dry-Run Network Isolation: refresh_credentials in dry-run mode performs no network egress.
"""

from __future__ import annotations

import asyncio
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from auth_manager import (
    AccountProfile,
    AccountRole,
    AccountSession,
    CredentialType,
    DualAccountManager,
    create_dual_account_manager,
)


class TestConcurrencyStress:
    """Stress tests concurrent execution across threads and coroutines."""

    def test_multi_threaded_simultaneous_authenticate_all(self):
        """Spawns 20 concurrent threads calling authenticate_all simultaneously on a shared manager."""
        manager = DualAccountManager(dry_run=True)
        errors: List[Exception] = []
        results: List[Dict[str, AccountSession]] = []
        num_threads = 20

        def worker(idx: int):
            try:
                res = manager.authenticate_all()
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered exceptions during concurrent authenticate_all: {errors}"
        assert len(results) == num_threads
        for res in results:
            assert "aaron.t.maher@gmail.com" in res
            assert "lauburu@lauburugrappling.com" in res
            assert res["aaron.t.maher@gmail.com"].is_authenticated is True
            assert res["lauburu@lauburugrappling.com"].is_authenticated is True

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")
        if c1 is not None and c2 is not None:
            assert c1 is not c2
            assert c1._api_client is not c2._api_client

    def test_concurrency_race_condition_detection_dictionary_mutation(self):
        """Verifies dictionary mutation thread safety under concurrent read/write contention."""
        manager = DualAccountManager(dry_run=True)
        stop_event = threading.Event()
        read_errors: List[Exception] = []
        write_errors: List[Exception] = []
        read_count = [0]
        write_count = [0]

        def writer():
            accounts = ["aaron.t.maher@gmail.com", "lauburu@lauburugrappling.com"]
            idx = 0
            while not stop_event.is_set():
                try:
                    manager.authenticate_account(accounts[idx % 2])
                    write_count[0] += 1
                    idx += 1
                except Exception as e:
                    write_errors.append(e)

        def reader():
            while not stop_event.is_set():
                try:
                    manifest = manager.export_status_manifest()
                    assert "accounts" in manifest
                    assert "client_isolation_verified" in manifest
                    read_count[0] += 1
                except Exception as e:
                    read_errors.append(e)

        writers = [threading.Thread(target=writer) for _ in range(4)]
        readers = [threading.Thread(target=reader) for _ in range(8)]

        for t in writers + readers:
            t.start()

        time.sleep(1.0)
        stop_event.set()

        for t in writers + readers:
            t.join()

        # Under RLock and snapshot iteration, zero race conditions or iteration errors occur
        has_dict_race = any("dictionary changed size during iteration" in str(e) for e in read_errors)
        assert len(read_errors) == 0, f"Read errors occurred under contention: {read_errors}"
        assert len(write_errors) == 0, f"Write errors occurred under contention: {write_errors}"
        assert not has_dict_race, "Dictionary mutation race condition detected!"
        assert read_count[0] > 0, "No reader operations completed"
        assert write_count[0] > 0, "No writer operations completed"

    def test_asyncio_concurrent_dual_authentication(self):
        """Verifies coroutine-level concurrency via asyncio gathering authentication tasks."""
        manager = DualAccountManager(dry_run=True)

        async def run_async_test():
            async def auth_task(acc_id: str):
                return await asyncio.to_thread(manager.authenticate_account, acc_id)

            tasks = [
                auth_task("aaron.t.maher@gmail.com"),
                auth_task("lauburu@lauburugrappling.com"),
                auth_task("aaron.t.maher@gmail.com"),
                auth_task("lauburu@lauburugrappling.com"),
            ]
            sessions = await asyncio.gather(*tasks)
            return sessions

        sessions = asyncio.run(run_async_test())
        assert len(sessions) == 4
        assert all(s.is_authenticated for s in sessions)
        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")
        if c1 is not None and c2 is not None:
            assert c1 is not c2
            assert c1._api_client is not c2._api_client


class TestMemoryIsolationAndHeaderChallenges:
    """Stress tests client memory isolation, underlying _api_client, and authorization headers."""

    def test_distinct_client_and_api_client_instances(self):
        """Empirically asserts distinct memory addresses for client and _api_client when clients exist."""
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        assert c1 is not None and c2 is not None
        assert id(c1) != id(c2), "client1 and client2 share identical memory id"
        assert id(c1._api_client) != id(c2._api_client), "_api_client instances share identical memory id"
        assert c1._api_client is not c2._api_client

    def test_audit_authorization_headers_and_ambient_key_bleed(self, monkeypatch):
        """Verifies that ambient GEMINI_API_KEY does not bleed into the Workspace client.
        
        Personal Admin uses its ADC credentials (or its configured key) while Workspace Business
        uses its OAuth2 credentials, producing distinct authorization headers with zero key bleed.
        """
        monkeypatch.setenv("GEMINI_API_KEY", "personal-ambient-key-999")
        monkeypatch.setenv("GEMINI_API_KEY_WORKSPACE", "workspace-ambient-key-888")

        manager = DualAccountManager(dry_run=True)
        sessions = manager.authenticate_all()

        assert sessions["aaron.t.maher@gmail.com"].is_authenticated is True
        assert sessions["lauburu@lauburugrappling.com"].is_authenticated is True

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        assert c1 is not None and c2 is not None
        h1 = c1._api_client._http_options.headers or {}
        h2 = c2._api_client._http_options.headers or {}

        auth1 = h1.get("Authorization") or h1.get("x-goog-api-key")
        auth2 = h2.get("Authorization") or h2.get("x-goog-api-key")

        assert auth1 is not None and auth2 is not None
        # Must have distinct authorization headers on the wire
        assert auth1 != auth2, f"Headers must not collide: {auth1} == {auth2}"
        # Workspace client must not inherit Aaron's ambient key
        assert auth2 != "personal-ambient-key-999"
        assert getattr(c2._api_client, "api_key", None) != "personal-ambient-key-999"
        assert manager.export_status_manifest()["client_isolation_verified"] is True

    def test_audit_client_creation_success_when_ambient_api_key_unset(self, monkeypatch):
        """Verifies that when GEMINI_API_KEY is unset, client instantiation succeeds via on-disk credentials."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        manager = DualAccountManager(dry_run=True)
        sessions = manager.authenticate_all()

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        assert c1 is not None, "Personal client should instantiate via ADC credentials without ambient key"
        assert c2 is not None, "Workspace client should instantiate via OAuth2 credentials without ambient key"
        assert sessions["aaron.t.maher@gmail.com"].is_authenticated is True
        assert sessions["lauburu@lauburugrappling.com"].is_authenticated is True

        manifest = manager.export_status_manifest()
        assert manifest["client_isolation_verified"] is True
        assert manifest["authenticated_accounts"] == 2

    def test_client_instantiation_failure_marks_session_unauthenticated(self, monkeypatch):
        """Verifies that if client instantiation fails, session.is_authenticated is set to False."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        manager = DualAccountManager(dry_run=True)
        # Mock _instantiate_genai_client to return None
        with patch.object(manager, "_instantiate_genai_client", return_value=None):
            session = manager.authenticate_account("aaron.t.maher@gmail.com", dry_run=True)
            assert session.is_authenticated is False
            assert session.client is None
            assert session.error is not None
            assert "Failed to instantiate" in session.error

    def test_audit_primary_api_key_cred_type_support(self, monkeypatch):
        """Verifies that auth_manager supports primary_cred_type == CredentialType.API_KEY in live mode."""
        test_config = {
            "accounts": {
                "test@example.com": {
                    "account_id": "test@example.com",
                    "role": "personal_admin",
                    "primary_cred_type": "api_key",
                    "api_key_env_var": "TEST_ISOLATED_KEY",
                    "rate_limit_rpm": 14,
                    "rate_limit_rpd": 1400,
                    "is_active": True
                }
            }
        }
        monkeypatch.setenv("TEST_ISOLATED_KEY", "AIzaSy_TEST_KEY_12345")
        manager = DualAccountManager(config_data=test_config, dry_run=False)
        session = manager.authenticate_account("test@example.com")

        assert session.is_authenticated is True
        assert session.client is not None
        assert session.auth_method == "api_key"
        assert session.error is None


class TestPersistenceAndCLIStress:
    """Stress tests on atomic file persistence, CLI pure JSON output, and flags."""

    def test_atomic_token_writes_0600_permissions(self, tmp_path: Path):
        """Verifies that _write_credentials_file_atomically writes atomically with mode 0600."""
        target_file = tmp_path / "atomic_token.json"
        secret_content = json.dumps({"token": "secret_access_token_xyz"})

        DualAccountManager._write_credentials_file_atomically(target_file, secret_content)

        assert target_file.exists()
        assert target_file.read_text(encoding="utf-8") == secret_content

        # Verify permissions: 0600 (read/write owner only, no group or other access)
        file_mode = target_file.stat().st_mode & 0o777
        assert file_mode == 0o600, f"Expected permissions 0600, got {oct(file_mode)}"

    def test_cli_stdout_pure_json_and_account_flag(self):
        """Verifies CLI execution outputs 100% valid JSON on stdout and supports --account flag."""
        project_root = Path(__file__).resolve().parent.parent

        # 1. Full dry-run
        cmd = ["/opt/homebrew/bin/python3", "auth_manager.py", "--dry-run"]
        res = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
        assert res.returncode == 0, f"CLI exited with {res.returncode}. Stderr: {res.stderr}"

        # Stdout must parse cleanly as JSON without leading log strings
        manifest = json.loads(res.stdout)
        assert manifest["dry_run"] is True
        assert manifest["total_accounts"] == 2
        assert manifest["authenticated_accounts"] == 2
        assert manifest["client_isolation_verified"] is True

        # 2. Targeted account flag
        cmd_acc = [
            "/opt/homebrew/bin/python3", "auth_manager.py",
            "--dry-run", "--account", "aaron.t.maher@gmail.com"
        ]
        res_acc = subprocess.run(cmd_acc, cwd=str(project_root), capture_output=True, text=True)
        assert res_acc.returncode == 0, f"CLI --account failed: {res_acc.stderr}"
        manifest_acc = json.loads(res_acc.stdout)
        assert "aaron.t.maher@gmail.com" in manifest_acc["accounts"]
        assert manifest_acc["accounts"]["aaron.t.maher@gmail.com"]["is_authenticated"] is True

    def test_dry_run_refresh_credentials_offline_safety(self):
        """Verifies that calling refresh_credentials on a dry_run manager makes no network calls."""
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()

        with patch("google.auth.transport.requests.Request.__call__") as mock_req:
            ok = manager.refresh_credentials("lauburu@lauburugrappling.com")
            assert ok is True
            assert not mock_req.called, "refresh_credentials in dry-run mode must never call external network"
            session = manager.get_session("lauburu@lauburugrappling.com")
            assert session.is_authenticated is True
