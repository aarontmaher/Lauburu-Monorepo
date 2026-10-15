"""Challenger M1 Iteration 2 Adversarial Stress Harness.

Empirically tests and stress-tests:
1. Concurrency: Multi-threaded read/write tests against DualAccountManager under extreme
   contention and dynamic dictionary mutation to ensure zero `RuntimeError: dictionary changed size during iteration`.
2. Memory and Header Isolation: Deep inspection of authorization headers, underlying _api_client
   isolation, mutable header independence, and ambient environment variable containment.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_manager import (
    AccountProfile,
    AccountRole,
    AccountSession,
    CredentialType,
    DualAccountManager,
    create_dual_account_manager,
)


class TestConcurrencyExtremeContention:
    """Stress tests multi-threaded contention against DualAccountManager dictionaries."""

    def test_extreme_multithreaded_read_write_contention(self):
        """Spawns 32 concurrent threads (16 writers, 16 readers) under intense contention.

        Writers repeatedly authenticate accounts, refresh credentials, and update profiles.
        Readers repeatedly export status manifests, verify isolation, and query sessions.
        Ensures zero `RuntimeError: dictionary changed size during iteration` occurs.
        """
        manager = DualAccountManager(dry_run=True)
        stop_event = threading.Event()
        read_errors: List[Exception] = []
        write_errors: List[Exception] = []
        read_ops = [0]
        write_ops = [0]

        accounts = ["aaron.t.maher@gmail.com", "lauburu@lauburugrappling.com"]

        def writer_worker(w_id: int):
            step = 0
            while not stop_event.is_set():
                try:
                    target_account = accounts[step % len(accounts)]
                    if step % 3 == 0:
                        manager.authenticate_account(target_account, dry_run=True)
                    elif step % 3 == 1:
                        manager.authenticate_all(dry_run=True)
                    else:
                        manager.refresh_credentials(target_account)
                    write_ops[0] += 1
                    step += 1
                except Exception as e:
                    write_errors.append(e)

        def reader_worker(r_id: int):
            step = 0
            while not stop_event.is_set():
                try:
                    if step % 4 == 0:
                        manifest = manager.export_status_manifest()
                        assert "accounts" in manifest
                        assert "client_isolation_verified" in manifest
                    elif step % 4 == 1:
                        target_account = accounts[step % len(accounts)]
                        s = manager.get_session(target_account)
                        assert s is None or isinstance(s, AccountSession)
                    elif step % 4 == 2:
                        target_account = accounts[step % len(accounts)]
                        c = manager.get_genai_client(target_account)
                    else:
                        p = manager.get_profile(accounts[step % len(accounts)])
                        assert p is None or isinstance(p, AccountProfile)
                    read_ops[0] += 1
                    step += 1
                except Exception as e:
                    read_errors.append(e)

        writers = [threading.Thread(target=writer_worker, args=(i,)) for i in range(16)]
        readers = [threading.Thread(target=reader_worker, args=(i,)) for i in range(16)]

        for t in writers + readers:
            t.start()

        # Let the stress test run under heavy multi-core contention for 2.5 seconds
        time.sleep(2.5)
        stop_event.set()

        for t in writers + readers:
            t.join()

        dict_mutation_errors = [
            e for e in read_errors + write_errors
            if "dictionary changed size during iteration" in str(e)
        ]

        assert len(dict_mutation_errors) == 0, (
            f"Encountered dictionary mutation race conditions: {dict_mutation_errors}"
        )
        assert len(read_errors) == 0, f"Read errors encountered: {read_errors[:5]}"
        assert len(write_errors) == 0, f"Write errors encountered: {write_errors[:5]}"
        assert write_ops[0] > 100, f"Expected >100 write operations, got {write_ops[0]}"
        assert read_ops[0] > 500, f"Expected >500 read operations, got {read_ops[0]}"

    def test_dynamic_account_profile_injection_race(self):
        """Stress tests dynamic profile addition and configuration reloading concurrent with readers.

        Adversarial scenario: A thread rapidly mutates manager.profiles with dynamic accounts
        while multiple reader threads continuously export manifests and iterate sessions.
        """
        manager = DualAccountManager(dry_run=True)
        stop_event = threading.Event()
        errors: List[Exception] = []
        iteration_count = [0]

        def dynamic_injector():
            idx = 0
            while not stop_event.is_set():
                try:
                    new_id = f"dynamic_user_{idx % 50}@example.com"
                    profile = AccountProfile(
                        account_id=new_id,
                        role=AccountRole.PERSONAL_ADMIN,
                        primary_cred_type=CredentialType.ADC,
                        is_active=(idx % 2 == 0)
                    )
                    with manager._lock:
                        manager.profiles[new_id] = profile
                        if idx % 10 == 0 and len(manager.profiles) > 5:
                            # prune an entry
                            to_remove = [k for k in manager.profiles if k.startswith("dynamic_user_")][:1]
                            for k in to_remove:
                                del manager.profiles[k]
                    time.sleep(0.001)
                    idx += 1
                except Exception as e:
                    errors.append(e)

        def continuous_manifest_reader():
            while not stop_event.is_set():
                try:
                    manifest = manager.export_status_manifest()
                    assert manifest["total_accounts"] >= 0
                    iteration_count[0] += 1
                except Exception as e:
                    errors.append(e)

        injector = threading.Thread(target=dynamic_injector)
        readers = [threading.Thread(target=continuous_manifest_reader) for _ in range(8)]

        for t in [injector] + readers:
            t.start()

        time.sleep(1.5)
        stop_event.set()

        for t in [injector] + readers:
            t.join()

        dict_mutation_errors = [
            e for e in errors
            if "dictionary changed size during iteration" in str(e)
        ]
        assert len(dict_mutation_errors) == 0, (
            f"Dynamic injection caused dictionary changed size error: {dict_mutation_errors}"
        )
        assert len(errors) == 0, f"Encountered unexpected errors during dynamic injection: {errors}"
        assert iteration_count[0] > 100

    def test_simultaneous_token_refresh_race(self):
        """Two concurrent threads attempt to refresh credentials for the same account simultaneously."""
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()

        errors: List[Exception] = []
        results: List[bool] = []

        def refresh_worker():
            try:
                res = manager.refresh_credentials("lauburu@lauburugrappling.com")
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=refresh_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during simultaneous refresh: {errors}"
        assert len(results) == 10
        assert all(r is True for r in results)

        session = manager.get_session("lauburu@lauburugrappling.com")
        assert session is not None
        assert session.is_authenticated is True


class TestMemoryAndHeaderIsolationChallenges:
    """Rigorous empirical inspection of memory addresses and authorization headers."""

    def test_exhaustive_client_object_and_http_options_isolation(self):
        """Verifies distinct memory addresses for clients, _api_clients, and http_options."""
        manager = DualAccountManager(dry_run=True)
        sessions = manager.authenticate_all()

        assert sessions["aaron.t.maher@gmail.com"].is_authenticated is True
        assert sessions["lauburu@lauburugrappling.com"].is_authenticated is True

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        assert c1 is not None, "Personal client must not be None"
        assert c2 is not None, "Workspace client must not be None"

        # 1. Distinct GenAI Client instances
        assert id(c1) != id(c2), "Personal and Workspace GenAI clients share memory address"
        assert c1 is not c2

        # 2. Distinct underlying _api_client instances
        ac1 = getattr(c1, "_api_client", None)
        ac2 = getattr(c2, "_api_client", None)
        assert ac1 is not None and ac2 is not None
        assert id(ac1) != id(ac2), "_api_client instances share memory address"
        assert ac1 is not ac2

        # 3. Distinct _http_options instances
        opts1 = getattr(ac1, "_http_options", None)
        opts2 = getattr(ac2, "_http_options", None)
        assert opts1 is not None and opts2 is not None
        assert id(opts1) != id(opts2), "_http_options instances share memory address"
        assert opts1 is not opts2

        # 4. Distinct headers dictionaries
        h1 = getattr(opts1, "headers", None)
        h2 = getattr(opts2, "headers", None)
        assert h1 is not None and h2 is not None
        assert id(h1) != id(h2), "Headers dictionaries share memory address"
        assert h1 is not h2

    def test_header_mutation_independence(self):
        """Mutating headers on c1 must have zero side effects on c2."""
        manager = DualAccountManager(dry_run=True)
        manager.authenticate_all()

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        h1 = c1._api_client._http_options.headers
        h2 = c2._api_client._http_options.headers

        # Inject canary header into c1
        h1["X-Personal-Admin-Canary"] = "isolated-personal-123"

        assert "X-Personal-Admin-Canary" not in h2, "Canary header leaked into Workspace client headers!"
        assert h2.get("X-Personal-Admin-Canary") is None

    def test_ambient_gemini_api_key_does_not_pollute_workspace_headers_or_api_client(self, monkeypatch):
        """CRITICAL CHALLENGE: Set ambient GEMINI_API_KEY in environment.

        Inspect whether workspace client picks up the ambient personal key
        in its headers, options, or api_key attributes.
        """
        personal_ambient = "AIzaSyAaronPersonalKeyAmbientValue999"
        workspace_ambient = "AIzaSyLauburuWorkspaceKeyAmbientValue888"

        monkeypatch.setenv("GEMINI_API_KEY", personal_ambient)
        monkeypatch.setenv("GEMINI_API_KEY_WORKSPACE", workspace_ambient)

        manager = DualAccountManager(dry_run=True)
        sessions = manager.authenticate_all()

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        # Inspect c2 (Workspace Business)
        h2 = c2._api_client._http_options.headers or {}
        auth2 = h2.get("Authorization") or h2.get("x-goog-api-key")
        c2_key = getattr(c2._api_client, "api_key", None)

        # Workspace client MUST NOT have personal_ambient anywhere
        assert auth2 != personal_ambient, f"Workspace client Authorization header is personal key: {auth2}"
        assert c2_key != personal_ambient, f"Workspace client _api_client.api_key is personal key: {c2_key}"
        assert "AIzaSyAaronPersonalKey" not in str(h2), f"Personal key found in Workspace headers: {h2}"

        # Inspect c1 (Personal Admin)
        h1 = c1._api_client._http_options.headers or {}
        auth1 = h1.get("Authorization") or h1.get("x-goog-api-key")
        assert auth1 != auth2, f"Personal and Workspace auth headers collided: {auth1} == {auth2}"

    def test_clean_environment_headers_structure_and_bearer_separation(self, monkeypatch):
        """Verifies authorization headers in clean environment without ambient keys."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY_WORKSPACE", raising=False)

        manager = DualAccountManager(dry_run=True)
        sessions = manager.authenticate_all()

        c1 = manager.get_genai_client("aaron.t.maher@gmail.com")
        c2 = manager.get_genai_client("lauburu@lauburugrappling.com")

        h1 = c1._api_client._http_options.headers or {}
        h2 = c2._api_client._http_options.headers or {}

        assert "Authorization" in h1, f"Missing Authorization in c1 headers: {h1}"
        assert "Authorization" in h2, f"Missing Authorization in c2 headers: {h2}"

        bearer1 = h1["Authorization"]
        bearer2 = h2["Authorization"]

        assert bearer1.startswith("Bearer "), f"Invalid Bearer token format: {bearer1}"
        assert bearer2.startswith("Bearer "), f"Invalid Bearer token format: {bearer2}"
        assert bearer1 != bearer2, f"Bearer tokens must not be identical: {bearer1} == {bearer2}"

        # If on-disk credentials has genuine token, verify it's used; otherwise verify simulated fallback
        if getattr(sessions["lauburu@lauburugrappling.com"].credentials, "token", None):
            expected_token = sessions["lauburu@lauburugrappling.com"].credentials.token
            assert bearer2 == f"Bearer {expected_token}"
        else:
            assert "lauburu@lauburugrappling.com" in bearer2


    def test_live_mode_with_genuine_credentials_produces_isolated_headers(self):
        """Simulates live authentication with mocked google.oauth2.credentials.Credentials."""
        mock_creds_personal = MagicMock()
        mock_creds_personal.valid = True
        mock_creds_personal.expired = False
        mock_creds_personal.token = "genuine_live_token_aaron_abc123"
        mock_creds_personal.expiry = time.time() + 3600.0

        mock_creds_workspace = MagicMock()
        mock_creds_workspace.valid = True
        mock_creds_workspace.expired = False
        mock_creds_workspace.token = "genuine_live_token_lauburu_xyz789"
        mock_creds_workspace.expiry = time.time() + 3600.0

        manager = DualAccountManager(dry_run=False)

        # Patch Credentials.from_authorized_user_file to return appropriate mock
        def mock_from_file(path_str):
            if "aaron.t.maher" in str(path_str):
                return mock_creds_personal
            elif "workspace_token" in str(path_str):
                return mock_creds_workspace
            return mock_creds_personal

        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file", side_effect=mock_from_file):
            s1 = manager.authenticate_account("aaron.t.maher@gmail.com", dry_run=False)
            s2 = manager.authenticate_account("lauburu@lauburugrappling.com", dry_run=False)

            assert s1.is_authenticated is True
            assert s2.is_authenticated is True

            c1 = s1.client
            c2 = s2.client

            assert c1 is not None and c2 is not None
            assert c1 is not c2

            h1 = c1._api_client._http_options.headers
            h2 = c2._api_client._http_options.headers

            assert h1["Authorization"] == "Bearer genuine_live_token_aaron_abc123"
            assert h2["Authorization"] == "Bearer genuine_live_token_lauburu_xyz789"
            assert h1["Authorization"] != h2["Authorization"]

            manifest = manager.export_status_manifest()
            assert manifest["client_isolation_verified"] is True
            assert manifest["authenticated_accounts"] == 2

    def test_asyncio_massive_fanout_stress(self):
        """Massive asyncio fanout stress test with 50 concurrent tasks."""
        import asyncio

        manager = DualAccountManager(dry_run=True)

        async def worker(task_id: int):
            account = "aaron.t.maher@gmail.com" if task_id % 2 == 0 else "lauburu@lauburugrappling.com"
            if task_id % 3 == 0:
                s = await asyncio.to_thread(manager.authenticate_account, account)
                assert s.is_authenticated is True
            elif task_id % 3 == 1:
                manifest = await asyncio.to_thread(manager.export_status_manifest)
                assert manifest["client_isolation_verified"] is True
            else:
                c = await asyncio.to_thread(manager.get_genai_client, account)
                assert c is not None

        async def main():
            tasks = [worker(i) for i in range(50)]
            await asyncio.gather(*tasks)

        asyncio.run(main())

    def test_dual_api_key_profile_isolation(self, monkeypatch):
        """Verifies isolation when both accounts are configured to use distinct API keys."""
        monkeypatch.setenv("TEST_PERSONAL_KEY", "key-personal-secret-11111")
        monkeypatch.setenv("TEST_WORKSPACE_KEY", "key-workspace-secret-22222")

        cfg = {
            "accounts": {
                "personal@domain.com": {
                    "account_id": "personal@domain.com",
                    "role": "personal_admin",
                    "primary_cred_type": "api_key",
                    "api_key_env_var": "TEST_PERSONAL_KEY",
                    "rate_limit_rpm": 14,
                    "rate_limit_rpd": 1400,
                    "is_active": True
                },
                "workspace@domain.com": {
                    "account_id": "workspace@domain.com",
                    "role": "workspace_business",
                    "primary_cred_type": "api_key",
                    "api_key_env_var": "TEST_WORKSPACE_KEY",
                    "rate_limit_rpm": 14,
                    "rate_limit_rpd": 1400,
                    "is_active": True
                }
            }
        }

        mgr = DualAccountManager(config_data=cfg, dry_run=False)
        sessions = mgr.authenticate_all()

        assert sessions["personal@domain.com"].is_authenticated is True
        assert sessions["workspace@domain.com"].is_authenticated is True

        c1 = mgr.get_genai_client("personal@domain.com")
        c2 = mgr.get_genai_client("workspace@domain.com")

        assert c1 is not None and c2 is not None
        assert c1 is not c2
        assert c1._api_client is not c2._api_client

        # Check API keys
        key1 = getattr(c1._api_client, "api_key", None)
        key2 = getattr(c2._api_client, "api_key", None)

        assert key1 == "key-personal-secret-11111"
        assert key2 == "key-workspace-secret-22222"
        assert key1 != key2

        manifest = mgr.export_status_manifest()
        assert manifest["client_isolation_verified"] is True

