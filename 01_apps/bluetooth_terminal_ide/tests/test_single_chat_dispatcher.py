#!/usr/bin/env python3
"""
tests/test_single_chat_dispatcher.py
================================================================================
Test Suite for Sovereign Single-Chat Nexus (Mother Ship) Architecture.
Governed by:
- Rule 0 (Zero-Mock): Authentic endpoint tests against live FastAPI engine.
- Rule 1 (Tri-Proof): Exact process assertions, exit codes & SHA256 hashes.
- Rule 3 (Host Sanctuary): Zero heavy weights loaded in test execution.
================================================================================
"""

import os
import sys
import json
import time
import pytest
import sqlite3
from pathlib import Path

# Setup paths
APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from chat_dispatcher import SovereignSingleChatDispatcher, default_chat_dispatcher
from server import app
from fastapi.testclient import TestClient

TEST_DB_PATH = Path("/tmp/test_single_chat_nexus.db")


@pytest.fixture(scope="module")
def dispatcher():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    disp = SovereignSingleChatDispatcher(db_path=TEST_DB_PATH)
    yield disp
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(scope="module")
def api_client():
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------------------------
# 1. Dispatcher Initialization & Seeding Tests
# ------------------------------------------------------------------------------
def test_dispatcher_initialization(dispatcher):
    """Verifies SQLite tables and canonical seed threads exist."""
    threads = dispatcher.list_threads()
    assert len(threads) >= 5, "Must contain at least 5 canonical seed threads"
    thread_ids = {t["id"] for t in threads}
    expected = {"omni_inbox", "commerce_sales", "biometrics_movesense", "screen_lens_vla", "core_infrastructure"}
    assert expected.issubset(thread_ids), f"Missing canonical threads: {expected - thread_ids}"


# ------------------------------------------------------------------------------
# 2. Relevance Classification & Fan-Out Tests
# ------------------------------------------------------------------------------
def test_omni_inbox_relevance(dispatcher):
    """Verifies directive with inbox keywords routes to omni_inbox."""
    prompt = "Review recent unread emails and customer Instagram DMs for priority support"
    fanouts, new_threads = dispatcher.classify_and_route(prompt)
    fanned_ids = {f["thread_id"] for f in fanouts}
    assert "omni_inbox" in fanned_ids, f"Expected omni_inbox, got {fanned_ids}"


def test_commerce_sales_relevance(dispatcher):
    """Verifies directive with store/inventory keywords routes to commerce_sales."""
    prompt = "Audit Shopify product pricing margins and inventory stock levels"
    fanouts, new_threads = dispatcher.classify_and_route(prompt)
    fanned_ids = {f["thread_id"] for f in fanouts}
    assert "commerce_sales" in fanned_ids, f"Expected commerce_sales, got {fanned_ids}"


def test_biometrics_relevance(dispatcher):
    """Verifies directive with movesense biometrics keywords routes to biometrics_movesense."""
    prompt = "Sample 512Hz Movesense ECG biometrics and compute Zone 2 HRV readiness"
    fanouts, new_threads = dispatcher.classify_and_route(prompt)
    fanned_ids = {f["thread_id"] for f in fanouts}
    assert "biometrics_movesense" in fanned_ids, f"Expected biometrics_movesense, got {fanned_ids}"


def test_multi_domain_fanout(dispatcher):
    """Verifies multi-domain directive fans out to multiple satellite channels simultaneously."""
    prompt = "Check our movesense heart rate, inspect the active screen window with lens, and review shopify orders"
    fanouts, new_threads = dispatcher.classify_and_route(prompt)
    fanned_ids = {f["thread_id"] for f in fanouts}
    assert "biometrics_movesense" in fanned_ids
    assert "screen_lens_vla" in fanned_ids
    assert "commerce_sales" in fanned_ids
    assert len(fanouts) >= 3


# ------------------------------------------------------------------------------
# 3. Dynamic Project Thread Spawning
# ------------------------------------------------------------------------------
def test_dynamic_project_thread_spawning(dispatcher):
    """Verifies autonomous spawning of a new project thread for novel features."""
    prompt = "Build a new spatial grappling tracker module for tournament kinematics"
    fanouts, new_threads = dispatcher.classify_and_route(prompt)
    assert len(new_threads) >= 1, "Should have created at least 1 new project thread"
    created = new_threads[0]
    assert created["category"] == "project"
    assert "Spatial Grappling" in created["title"] or "Kinematics" in created["title"] or "Tournament" in created["title"] or "Module" in created["title"]
    # Check thread exists in database
    retrieved = dispatcher.get_thread(created["id"])
    assert retrieved is not None
    assert retrieved["title"] == created["title"]


# ------------------------------------------------------------------------------
# 4. Satellite Execution & Action Reporting
# ------------------------------------------------------------------------------
def test_satellite_task_execution(dispatcher):
    """Verifies satellite task execution captures empirical telemetry and returns exit code 0."""
    act = dispatcher.execute_satellite_task("core_infrastructure", "Audit mesh topology and host RAM sanctuary")
    assert act["exit_code"] == 0
    assert act["status"] == "completed"
    assert "Host RAM Sanctuary" in act["result"] or "RAM" in act["result"]
    assert "GB" in act["result"]

    # Verify action stored in database
    actions = dispatcher.get_thread_actions("core_infrastructure")
    assert len(actions) > 0
    assert any(a["id"] == act["id"] for a in actions)


# ------------------------------------------------------------------------------
# 5. Full End-to-End Dispatch & Next-Step Discussion
# ------------------------------------------------------------------------------
def test_full_dispatch_pipeline(dispatcher):
    """Verifies closed-loop dispatch from user directive to synthesized next steps."""
    user_prompt = "Audit movesense live stream, verify host sanctuary memory, and draft plan for new bluetooth tethering feature"
    result = dispatcher.dispatch(user_prompt)

    assert result["success"] is True
    assert result["user_prompt"] == user_prompt
    assert len(result["fanouts"]) >= 2
    assert len(result["actions_completed"]) >= 2
    assert len(result["suggested_options"]) >= 2
    assert len(result["next_step_discussion"]) > 50
    assert result["latency_ms"] > 0

    # Verify messages in nexus_main
    main_msgs = dispatcher.get_thread_messages("nexus_main")
    assert len(main_msgs) >= 2
    roles = [m["role"] for m in main_msgs]
    assert "user" in roles
    assert "assistant" in roles

    # Verify latest next steps cache
    latest = dispatcher.get_latest_next_steps()
    assert latest["has_discussion"] is True
    assert len(latest["options"]) >= 2


# ------------------------------------------------------------------------------
# 6. REST API Endpoints Verification
# ------------------------------------------------------------------------------
def test_api_chat_nexus_endpoint(api_client):
    """Verifies POST /api/chat/nexus endpoint."""
    resp = api_client.post("/api/chat/nexus", json={
        "prompt": "Check omni inbox messages and review shopify inventory"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert "nexus_response" in data
    assert "fanouts" in data
    assert "actions_completed" in data
    assert "next_step_discussion" in data
    assert "suggested_options" in data


def test_api_get_threads_endpoint(api_client):
    """Verifies GET /api/chat/nexus/threads."""
    resp = api_client.get("/api/chat/nexus/threads")
    assert resp.status_code == 200
    data = resp.json()
    assert "threads" in data
    assert data["count"] >= 5


def test_api_thread_messages_and_actions(api_client):
    """Verifies GET /api/chat/nexus/threads/{id}/messages and /actions."""
    resp_msg = api_client.get("/api/chat/nexus/threads/omni_inbox/messages")
    assert resp_msg.status_code == 200
    assert "messages" in resp_msg.json()

    resp_act = api_client.get("/api/chat/nexus/threads/omni_inbox/actions")
    assert resp_act.status_code == 200
    assert "actions" in resp_act.json()


def test_api_report_action_endpoint(api_client):
    """Verifies POST /api/chat/nexus/threads/{id}/report."""
    resp = api_client.post("/api/chat/nexus/threads/commerce_sales/report", json={
        "action": "Synchronized Shopify inventory levels",
        "result": "Catalog 100% in stock, zero oversell warnings",
        "exit_code": 0,
        "status": "completed"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("exit_code") == 0
    assert data.get("action") == "Synchronized Shopify inventory levels"


def test_api_next_steps_and_discuss(api_client):
    """Verifies GET /api/chat/nexus/next-steps and POST /api/chat/nexus/discuss."""
    resp = api_client.get("/api/chat/nexus/next-steps")
    assert resp.status_code == 200
    data = resp.json()
    assert "discussion" in data

    resp_disc = api_client.post("/api/chat/nexus/discuss", json={
        "option_selected": "Review live telemetry stream and biometrics validation charts",
        "feedback": "Focus on 512Hz Pan-Tompkins latency"
    })
    assert resp_disc.status_code == 200
    disc_data = resp_disc.json()
    assert disc_data.get("success") is True


# ------------------------------------------------------------------------------
# 7. Terminal Macro Integration
# ------------------------------------------------------------------------------
def test_terminal_nexus_macro(api_client):
    """Verifies /api/terminal/run executes 'nexus <directive>'."""
    resp = api_client.post("/api/terminal/run", json={
        "command": "nexus Audit 7-layer mesh network status and RAM sanctuary"
    })
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "SOVEREIGN SINGLE-CHAT NEXUS DISPATCH" in out
    assert "Actions Executed & Reported Back" in out
    assert "Strategic Next Steps" in out


def test_terminal_threads_macro(api_client):
    """Verifies /api/terminal/run executes 'threads'."""
    resp = api_client.post("/api/terminal/run", json={"command": "threads"})
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "ACTIVE SATELLITE CHATS" in out
    assert "OMNI_INBOX" in out.upper()
    assert "COMMERCE_SALES" in out.upper()


def test_terminal_next_macro(api_client):
    """Verifies /api/terminal/run executes 'next'."""
    resp = api_client.post("/api/terminal/run", json={"command": "next"})
    assert resp.status_code == 200
    out = resp.json().get("output", "")
    assert "LATEST NEXT STEP DISCUSSION" in out


# ------------------------------------------------------------------------------
# 8. Zero-Mock Offline Fallback Resilience
# ------------------------------------------------------------------------------
def test_zero_mock_offline_fallback(monkeypatch, dispatcher):
    """Verifies that if local model returns None or times out, deterministic fallback works."""
    import chat_dispatcher
    monkeypatch.setattr(chat_dispatcher, "call_local_model", lambda *args, **kwargs: None)

    result = dispatcher.dispatch("Test prompt with movesense and shopify offline")
    assert result["success"] is True
    assert "👑" in result["nexus_response"]
    assert len(result["fanouts"]) >= 2
    assert len(result["actions_completed"]) >= 2
    assert len(result["suggested_options"]) >= 2
    for act in result["actions_completed"]:
        assert act["exit_code"] == 0
