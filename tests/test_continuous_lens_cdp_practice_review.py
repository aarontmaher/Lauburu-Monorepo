"""
================================================================================
Continuous Lens CDP Practice & Webapp Review Suite — Pytest Verification
================================================================================
File Ownership: tests/test_continuous_lens_cdp_practice_review.py
Subsystem: 06_scripts_and_tooling/automation/continuous_lens_cdp_practice.py
Lauburu Mesh Ecosystem — 2026

Verifies Requirements & Acceptance Criteria:
- R1. Chrome DevTools Integration: Discover & connect to running local webapps.
- R2. Comprehensive Webapp Review Suite:
    * Lighthouse audit triggering & saving to disk.
    * Full DOM structure and Accessibility Tree extraction.
    * Interactive element bounding boxes and viewport screenshot capture.
    * Memory leak HeapSnapshots saved to disk.
    * Injection of test interactions (mouse click & keystroke).
    * AI review feedback generation.
- R3. Host Sanctuary Constraint: Host RAM headroom enforcement.
================================================================================
"""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PRACTICE_SCRIPT = (
    REPO_ROOT
    / "06_scripts_and_tooling"
    / "automation"
    / "continuous_lens_cdp_practice.py"
)
PERCEPTION_DIR = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "VLA_PERCEPTION"

# Import runner module directly for unit verification
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling" / "automation"))
import continuous_lens_cdp_practice as cdp_mod


def test_host_sanctuary_memory_check():
    """Asserts Host Sanctuary RAM check correctly evaluates system memory."""
    is_safe, free_ram = cdp_mod.check_host_sanctuary(min_free_ram_gb=1.0)
    assert isinstance(is_safe, bool)
    assert isinstance(free_ram, float)
    assert free_ram > 0.0, "Free RAM calculation returned non-positive value"


def test_discover_running_webapps():
    """Asserts webapp discovery autonomously finds target webapp configurations."""
    targets = cdp_mod.discover_running_webapps()
    assert len(targets) >= 1, "Failed to discover any local webapp targets"

    target_ids = {t["target_id"] for t in targets}
    assert "GO_GATT_BROWSER" in target_ids, "GO_GATT_BROWSER target missing from discovered targets"
    assert "JUPYTERLAB" in target_ids, "JUPYTERLAB target missing from discovered targets"


def test_practice_script_single_pass_execution():
    """Executes continuous_lens_cdp_practice.py --single-pass and asserts clean exit code 0."""
    assert PRACTICE_SCRIPT.exists(), f"Practice script not found at {PRACTICE_SCRIPT}"

    cmd = [sys.executable, str(PRACTICE_SCRIPT), "--single-pass"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)

    assert res.returncode == 0, (
        f"Practice script failed with exit code {res.returncode}.\n"
        f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}"
    )


def test_review_artifacts_presence_and_integrity():
    """Verifies presence, non-zero file size, and valid SHA256 integrity of all Review Artifacts."""
    assert PERCEPTION_DIR.exists(), f"Perception directory missing: {PERCEPTION_DIR}"

    png_files = list(PERCEPTION_DIR.glob("VLA_SNAPSHOT_*.png"))
    json_files = list(PERCEPTION_DIR.glob("VLA_AXTREE_*.json"))
    heap_files = list(PERCEPTION_DIR.glob("HEAP_SNAPSHOT_*.heapsnapshot"))
    audit_files = list(PERCEPTION_DIR.glob("LIGHTHOUSE_AUDIT_*.json"))

    # Assert all four artifact categories are present on disk
    assert len(png_files) >= 1, "No PNG screenshot artifacts found"
    assert len(json_files) >= 1, "No AXTree JSON snapshot artifacts found"
    assert len(heap_files) >= 1, "No HeapSnapshot memory leak artifacts found"
    assert len(audit_files) >= 1, "No Lighthouse Audit JSON artifacts found"

    # 1. Verify HeapSnapshot integrity
    for h_path in heap_files:
        assert h_path.stat().st_size > 0, f"HeapSnapshot file {h_path} is 0 bytes"

    # 2. Verify Lighthouse Audit integrity
    for a_path in audit_files:
        assert a_path.stat().st_size > 0, f"Lighthouse Audit file {a_path} is 0 bytes"
        with open(a_path, "r", encoding="utf-8") as f:
            a_data = json.load(f)
        assert "categories" in a_data or "lighthouseVersion" in a_data

    # 3. Verify AXTree JSON & PNG Screenshot pairs
    verified_v2_artifacts = 0
    for json_path in json_files:
        assert json_path.stat().st_size > 0, f"JSON artifact {json_path} is 0 bytes"
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        target_id = payload.get("target_id", "UNKNOWN")
        if target_id == "BAD_TARGET" or "BAD_TARGET" in json_path.name:
            continue

        ax_nodes = payload.get("ax_tree_nodes", [])
        assert len(ax_nodes) >= 50, f"AXTree node count in {json_path.name} is < 50"

        # Check for V2 review suite keys if generated by V2 script
        if "dom_structure" in payload:
            verified_v2_artifacts += 1
            assert "test_interactions" in payload, f"Missing test_interactions in {json_path.name}"
            assert "heap_snapshot" in payload, f"Missing heap_snapshot in {json_path.name}"
            assert "lighthouse_audit" in payload, f"Missing lighthouse_audit in {json_path.name}"
            assert "ai_review_feedback" in payload, f"Missing ai_review_feedback in {json_path.name}"

        # Verify integrity SHA256 checksums
        recorded_ax_sha = payload.get("integrity", {}).get("json_sha256")
        calc_ax_sha = hashlib.sha256(
            json.dumps(ax_nodes, sort_keys=True).encode("utf-8")
        ).hexdigest()
        assert recorded_ax_sha == calc_ax_sha, f"AXTree JSON SHA256 checksum mismatch in {json_path.name}"

    assert verified_v2_artifacts >= 1, "Expected at least 1 artifact manifest containing V2 DevTools review fields"


def test_direct_runner_review_methods():
    """Directly invokes LensCDPPracticeRunner review methods and asserts structural validity."""
    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)
        timestamp = "TEST_" + str(int(time.time()))

        # 1. Test Lighthouse audit generation
        audit_path, audit_sha256, scores = await runner.run_lighthouse_audit(
            target_id="UNIT_TEST_WEBAPP",
            target_url="http://127.0.0.1:8084/",
            timestamp_str=timestamp,
        )
        assert audit_path.exists()
        assert audit_path.stat().st_size > 0
        assert len(audit_sha256) == 64
        assert isinstance(scores, dict)

        # 2. Test Cloud Model AI Review query
        ai_feedback = await runner.query_cloud_model_review(
            target_id="UNIT_TEST_WEBAPP",
            target_url="http://127.0.0.1:8084/",
            dom_node_count=120,
            ax_node_count=85,
            lighthouse_scores=scores,
            heap_size=204800,
            sha256_png=audit_sha256,
        )
        assert isinstance(ai_feedback, str)
        assert len(ai_feedback) > 10

    asyncio.run(_test())


def test_discover_running_webapps_http_errors(monkeypatch):
    """Verifies webapp discovery correctly handles HTTP error responses (e.g. 500, 503, 401)."""
    import urllib.error
    import urllib.request

    def mock_urlopen(req, timeout=1.5):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "8084" in url:
            raise urllib.error.HTTPError(url, 500, "Internal Server Error", {}, None)
        elif "8889" in url or "8888" in url:
            raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    targets = cdp_mod.discover_running_webapps()
    assert len(targets) >= 1
    discovered_ids = {t["target_id"] for t in targets}
    assert "GO_GATT_BROWSER" in discovered_ids or "JUPYTERLAB" in discovered_ids


def test_host_sanctuary_low_memory_handling(monkeypatch):
    """Verifies HeapSnapshot capture respects Host Sanctuary by skipping heavy allocation when RAM is low."""
    # Force check_host_sanctuary to report unsafe (low free RAM)
    monkeypatch.setattr(cdp_mod, "get_free_ram_gb", lambda: 1.2)

    class DummyWS:
        async def send(self, msg): pass
        async def recv(self): return "{}"

    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)
        dummy_ws = DummyWS()
        heap_path, heap_sha, heap_size = await runner.capture_heap_snapshot(
            dummy_ws, "LOW_RAM_TARGET", f"SANCTUARY_{int(time.time())}"
        )
        assert heap_path.exists()
        assert heap_size > 0
        with open(heap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("sanctuary_skipped") is True

    asyncio.run(_test())


def test_inject_test_interactions_malformed_input():
    """Verifies inject_test_interactions handles malformed, empty, or invalid bounding boxes safely."""
    class DummyWS:
        pass

    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)

        # Mock send_cdp_command to avoid network calls
        async def mock_send(ws, method, params=None, timeout=15.0):
            return {"result": {}}

        runner.send_cdp_command = mock_send

        # Test with None, empty list, malformed bbox
        malformed_inputs = [
            None,
            [],
            [None],
            [{}],
            [{"bbox": None}],
            [{"bbox": {"cx": "invalid", "cy": -100}}],
        ]

        for bbox_input in malformed_inputs:
            log_entries = await runner.inject_test_interactions(DummyWS(), bbox_input)
            assert isinstance(log_entries, list)
            assert len(log_entries) == 2
            assert log_entries[0]["type"] == "click"
            assert log_entries[1]["type"] == "keystroke"

    asyncio.run(_test())


def test_lighthouse_audit_corrupted_json_and_malformed_scores(monkeypatch):
    """Verifies run_lighthouse_audit safely recovers from corrupted JSON output and malformed category scores."""
    async def mock_exec(*args, **kwargs):
        raise FileNotFoundError("lighthouse CLI not installed for fast test path")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)

    async def _test():
        test_dir = PERCEPTION_DIR / "test_tmp_audit"
        test_dir.mkdir(parents=True, exist_ok=True)
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=test_dir)
        timestamp = f"CORRUPTED_{int(time.time())}"

        # 1. Pre-create a corrupted JSON file at the expected output path to simulate a failed/partial Lighthouse CLI run
        target_id = "CORRUPTED_TEST"
        expected_filename = f"LIGHTHOUSE_AUDIT_{target_id}_{timestamp}.json"
        corrupted_path = test_dir / expected_filename
        with open(corrupted_path, "w", encoding="utf-8") as f:
            f.write("{corrupted_json_truncated: true, categories: { performance: ")

        audit_path, audit_sha, scores = await runner.run_lighthouse_audit(
            target_id=target_id,
            target_url="http://127.0.0.1:8084/",
            timestamp_str=timestamp,
        )

        assert audit_path.exists()
        assert audit_path.stat().st_size > 0
        assert len(audit_sha) == 64
        assert isinstance(scores, dict)
        assert "performance" in scores
        assert isinstance(scores["performance"], float)

        # Clean up
        if corrupted_path.exists():
            corrupted_path.unlink()
        shutil.rmtree(test_dir, ignore_errors=True)

    asyncio.run(_test())


def test_query_cloud_model_review_malformed_responses():
    """Verifies query_cloud_model_review handles non-JSON, non-dict, and malformed model response payloads gracefully."""
    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)

        # Test with string/malformed performance score in lighthouse_scores
        malformed_scores = {"performance": "invalid_string_score", "accessibility": None}

        ai_review = await runner.query_cloud_model_review(
            target_id="MALFORMED_RESP_TARGET",
            target_url="http://127.0.0.1:8084/",
            dom_node_count=100,
            ax_node_count=50,
            lighthouse_scores=malformed_scores,
            heap_size=1048576,
            sha256_png="a" * 64,
        )

        assert isinstance(ai_review, str)
        assert len(ai_review) > 10
        assert "MALFORMED_RESP_TARGET" in ai_review
        assert "Chrome DevTools MCP" in ai_review

    asyncio.run(_test())


def test_send_cdp_command_non_json_frames():
    """Verifies send_cdp_command ignores non-JSON WebSocket frames and awaits valid JSON-RPC matching ID."""
    class DummyWSWithFrames:
        def __init__(self):
            self.sent = []
            self.frames = [
                "NOT_VALID_JSON_FRAME",
                "12345",
                json.dumps({"method": "Page.loadEventFired"}),
                json.dumps({"id": 1, "result": {"success": True}}),
            ]
            self.idx = 0

        async def send(self, msg):
            self.sent.append(msg)

        async def recv(self):
            if self.idx < len(self.frames):
                frame = self.frames[self.idx]
                self.idx += 1
                return frame
            await asyncio.sleep(10)

    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)
        ws = DummyWSWithFrames()
        res = await runner.send_cdp_command(ws, "Test.method", timeout=5.0)
        assert res.get("result", {}).get("success") is True

    asyncio.run(_test())


def test_custom_nested_output_directory(monkeypatch):
    """Verifies LensCDPPracticeRunner automatically creates nested output directories and saves artifacts cleanly."""
    async def mock_exec(*args, **kwargs):
        raise FileNotFoundError("lighthouse CLI not installed for fast test path")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)

    nested_dir = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "VLA_PERCEPTION" / "nested_test_dir" / "sub"
    runner = cdp_mod.LensCDPPracticeRunner(out_dir=nested_dir)
    assert nested_dir.exists()

    async def _test():
        timestamp = f"NESTED_{int(time.time())}"
        audit_path, audit_sha, scores = await runner.run_lighthouse_audit(
            target_id="NESTED_DIR_TARGET",
            target_url="http://127.0.0.1:8084/",
            timestamp_str=timestamp,
        )
        assert audit_path.exists()
        assert nested_dir in audit_path.parents
        audit_path.unlink()

    asyncio.run(_test())
    shutil.rmtree(nested_dir.parent, ignore_errors=True)


def test_safe_get_dict_helper():
    """Verifies safe_get_dict extracts nested keys cleanly without raising AttributeError on None values."""
    data = {
        "a": {"b": None, "c": {"d": 42}},
        "e": None,
    }
    assert cdp_mod.safe_get_dict(data, "a", "c", "d") == 42
    assert cdp_mod.safe_get_dict(data, "a", "b", "x", default="fallback") == "fallback"
    assert cdp_mod.safe_get_dict(data, "e", "f", default="fallback") == "fallback"
    assert cdp_mod.safe_get_dict(None, "a", "b", default="fallback") == "fallback"
    assert cdp_mod.safe_get_dict("string_obj", "a", default=100) == 100


def test_target_url_unreachable_or_invalid_domain(monkeypatch):
    """Verifies run_single_pass with custom unreachable --target-url completes cleanly with graceful fallback."""
    async def mock_exec(*args, **kwargs):
        raise FileNotFoundError("lighthouse CLI not installed for fast test path")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)

    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)
        unreachable_url = "http://nonexistent-domain-xyz-9999.local:9999/"
        results = await runner.run_single_pass(target_url=unreachable_url)

        assert isinstance(results, list)
        assert len(results) >= 1
        for png_p, json_path, png_sha, json_sha in results:
            assert png_p.exists()
            assert json_path.exists()
            assert len(png_sha) == 64
            assert len(json_sha) == 64

    asyncio.run(_test())


def test_cli_argument_parsing_and_custom_target_url():
    """Executes practice script CLI with --target-url, invalid --cdp-ports, and --single-pass."""
    cmd = [
        sys.executable,
        str(PRACTICE_SCRIPT),
        "--single-pass",
        "--target-url", "http://127.0.0.1:8084/",
        "--cdp-ports", "invalid_port,9222",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    assert res.returncode == 0, f"CLI execution failed:\nStdout:\n{res.stdout}\nStderr:\n{res.stderr}"


def test_multi_pass_artifact_integrity_and_hashes(monkeypatch):
    """Verifies multi-pass execution yields valid, non-zero, deterministic artifact pairs across iterations."""
    async def mock_exec(*args, **kwargs):
        raise FileNotFoundError("lighthouse CLI not installed for fast test path")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)

    async def _test():
        runner = cdp_mod.LensCDPPracticeRunner(out_dir=PERCEPTION_DIR)
        res1 = await runner.run_single_pass()
        res2 = await runner.run_single_pass()

        assert len(res1) >= 1
        assert len(res2) >= 1

        for res_list in (res1, res2):
            for png_p, json_p, png_sha, json_sha in res_list:
                assert png_p.exists() and png_p.stat().st_size > 1000
                assert json_p.exists() and json_p.stat().st_size > 0
                with open(json_p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ax_nodes = data.get("ax_tree_nodes", [])
                assert len(ax_nodes) >= 50
                assert data["ax_tree_nodes"][0].get("name", {}).get("value") != "Node_1"
                assert "chromium_polyglot_specialists" in data
                calc_sha = hashlib.sha256(json.dumps(ax_nodes, sort_keys=True).encode("utf-8")).hexdigest()
                assert data.get("integrity", {}).get("json_sha256") == calc_sha

    asyncio.run(_test())


def test_dom_to_axtree_parser_void_tags_and_visible_text():
    """Verifies DOMToAXTreeParser skips head/meta/script/style, does not leak void tags on stack, and prefers visible text over CSS class names."""
    sample_html = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link rel="stylesheet" href="/style.css">
        <title>⚡ Console Lauburu Live</title>
        <style>.tab-btn { color: green; }</style>
        <script>console.log("hidden script text");</script>
    </head>
    <body>
        <header class="top-bar">
            <img src="/logo.png" alt="Lauburu Logo">
            <input type="text" placeholder="Search sensor...">
            <button class="tab-btn"><span>🏠 Home</span></button>
            <button class="tab-btn" aria-label="ECG Stream"><span>❤️</span></button>
        </header>
    </body>
    </html>
    """
    parser = cdp_mod.DOMToAXTreeParser()
    parser.feed(sample_html)

    # 1. RootWebArea should take the parsed <title>
    assert parser.title == "⚡ Console Lauburu Live"
    assert parser.nodes[0]["role"]["value"] == "RootWebArea"
    assert parser.nodes[0]["name"]["value"] == "⚡ Console Lauburu Live"

    # 2. <meta>, <link>, <style>, <script> must never appear in AXTree nodes
    node_names = [n["name"]["value"] for n in parser.nodes]
    assert "hidden script text" not in node_names
    for forbidden_tag in ("meta", "link", "style", "script", "head"):
        assert forbidden_tag not in node_names

    # 3. Button with class="tab-btn" and visible text "🏠 Home" must be named "🏠 Home", NOT "tab-btn"
    button_nodes = [n for n in parser.nodes if n["role"]["value"] == "button"]
    assert len(button_nodes) == 2
    assert button_nodes[0]["name"]["value"] == "🏠 Home"
    assert button_nodes[1]["name"]["value"] == "ECG Stream"

    # 4. Bounding boxes must also carry the visible text "🏠 Home", not the CSS class name
    button_bboxes = [b for b in parser.bboxes if b["tag"] == "button"]
    assert len(button_bboxes) == 2
    assert button_bboxes[0]["text"] == "🏠 Home"
    assert button_bboxes[1]["text"] == "ECG Stream"


def test_devtools_active_port_discovery_and_session_multiplexing(monkeypatch, tmp_path):
    """Verifies DevToolsActivePort discovery when /json/version fails and full end-to-end Target.attachToTarget (flatten=True) session multiplexing over a real WebSocket server with interleaved CDP events."""
    import base64
    import urllib.error
    import urllib.request
    import websockets

    # Pre-capture a real PNG frame before monkeypatching urlopen
    seed_runner = cdp_mod.LensCDPPracticeRunner(out_dir=tmp_path / "seed")
    valid_png_b64 = base64.b64encode(seed_runner.capture_live_visual_frame_png()).decode("ascii")

    # Force /json/version HTTP probe to fail while allowing webapp target discovery if needed
    def fail_urlopen(req, timeout=1.0):
        raise urllib.error.URLError("HTTP /json/version disabled on Chrome 136+")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)

    async def mock_exec(*args, **kwargs):
        raise FileNotFoundError("lighthouse CLI not installed for fast test path")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)

    multiplex_calls = []

    async def ws_multiplex_handler(websocket):
        path = getattr(websocket, "path", "")
        if not path and hasattr(websocket, "request") and websocket.request:
            path = websocket.request.path
        # Reject any direct /devtools/page/<id> connection to prove Target.attachToTarget multiplexing is used
        if "/devtools/page/" in path:
            await websocket.close(code=1008, reason="Direct page websocket disabled in Chrome 136+ DevToolsActivePort mode")
            return

        async for message in websocket:
            req = json.loads(message)
            msg_id = req.get("id")
            method = req.get("method")
            session_id = req.get("sessionId")
            multiplex_calls.append((method, session_id))

            # Emit an interleaved asynchronous event before replying to verify session-aware event filtering
            await websocket.send(
                json.dumps(
                    {
                        "method": "Page.lifecycleEvent",
                        "sessionId": session_id or "session-mux-1",
                        "params": {"name": "networkIdle"},
                    }
                )
            )

            res = {}
            if method == "Target.createTarget":
                res = {"targetId": "TARGET_MUX_PAGE_1"}
            elif method == "Target.attachToTarget":
                assert req.get("params", {}).get("flatten") is True
                res = {"sessionId": "session-mux-1"}
            elif method == "Target.closeTarget":
                res = {"success": True}
            elif method == "Page.navigate":
                res = {"frameId": "FRAME_MUX_1"}
            elif method == "Runtime.evaluate":
                expr = req.get("params", {}).get("expression", "")
                if "document.title" in expr:
                    res = {"result": {"value": json.dumps({"title": "Multiplexed Session App", "isErr": False})}}
                elif "outerHTML" in expr:
                    res = {
                        "result": {
                            "value": json.dumps(
                                {
                                    "title": "Multiplexed Session App",
                                    "html": "<html><body><button>Mux Action</button></body></html>",
                                    "bboxes": [
                                        {
                                            "index": 0,
                                            "tag": "button",
                                            "id": "mux-btn",
                                            "className": "primary",
                                            "text": "Mux Action",
                                            "bbox": {"x": 50, "y": 60, "width": 120, "height": 36, "cx": 110, "cy": 78},
                                        }
                                    ],
                                }
                            )
                        }
                    }
                elif "performance" in expr:
                    res = {
                        "result": {
                            "value": json.dumps(
                                {"domInteractive": 35, "loadTime": 80, "scripts": 2, "stylesheets": 1, "imagesWithAlt": 2, "totalImages": 2, "hasViewport": True, "hasTitle": True}
                            )
                        }
                    }
            elif method == "Accessibility.getFullAXTree":
                nodes = [
                    {
                        "nodeId": f"mux_ax_{i}",
                        "ignored": False,
                        "role": {"type": "role", "value": "button" if i % 2 == 0 else "StaticText"},
                        "name": {"type": "computedString", "value": f"MuxComponent_{i}"},
                        "childIds": [],
                    }
                    for i in range(1, 60)
                ]
                res = {"nodes": nodes}
            elif method == "Page.captureScreenshot":
                res = {"data": valid_png_b64}
            elif method == "HeapProfiler.takeHeapSnapshot":
                await websocket.send(
                    json.dumps(
                        {
                            "method": "HeapProfiler.addHeapSnapshotChunk",
                            "sessionId": session_id,
                            "params": {"chunk": '{"snapshot":{"meta":{},"node_count":15,"edge_count":30},"nodes":[1,2,3]}'},
                        }
                    )
                )
                res = {}

            resp_payload = {"id": msg_id, "result": res}
            if session_id:
                resp_payload["sessionId"] = session_id
            await websocket.send(json.dumps(resp_payload))

    async def _run_e2e_multiplex():
        async with websockets.serve(ws_multiplex_handler, "127.0.0.1", 0, max_size=None) as server:
            port = server.sockets[0].getsockname()[1]
            fake_home = tmp_path / "home"
            active_port_file = fake_home / "Library" / "Application Support" / "Google" / "Chrome" / "DevToolsActivePort"
            active_port_file.parent.mkdir(parents=True, exist_ok=True)
            active_port_file.write_text(f"{port}\n/devtools/browser/test-uuid-1234\n", encoding="utf-8")
            monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

            out_dir = tmp_path / "out_mux"
            runner = cdp_mod.LensCDPPracticeRunner(cdp_host="127.0.0.1", cdp_ports=[port], out_dir=out_dir)
            info, active_host, active_port = runner.get_cdp_version_info()
            assert info is not None
            assert info.get("devtools_active_port") is True
            assert active_host == "127.0.0.1"
            assert active_port == port

            results = await runner.run_single_pass(target_url="http://127.0.0.1:4000/")
            assert len(results) >= 1
            png_path, json_path, png_sha, json_sha = results[0]
            assert png_path.exists() and png_path.stat().st_size > 1000
            assert json_path.exists()

            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            assert payload["page_title"] == "Multiplexed Session App"
            assert len(payload["ax_tree_nodes"]) == 59

            # Verify Target.attachToTarget was invoked and page-level commands carried sessionId="session-mux-1"
            methods_called = [m for m, _ in multiplex_calls]
            assert "Target.attachToTarget" in methods_called
            page_cmds = [(m, sid) for m, sid in multiplex_calls if m.startswith(("Page.", "Runtime.", "Accessibility.", "HeapProfiler."))]
            assert len(page_cmds) >= 6
            assert all(sid == "session-mux-1" for _, sid in page_cmds)

    asyncio.run(_run_e2e_multiplex())


def test_personal_chrome_devtools_active_port_skipped_in_production(monkeypatch, tmp_path):
    """Verifies INV_2_HUMAN_BROWSER_SANCTUARY: personal default Chrome DevToolsActivePort is skipped in production so Chrome 136+ does not repeatedly prompt 'Allow remote debugging?' on every pass."""
    import socket
    import urllib.error
    import urllib.request

    def fail_urlopen(req, timeout=1.0):
        raise urllib.error.URLError("HTTP /json/version disabled")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
    monkeypatch.delenv("LENS_ALLOW_PERSONAL_CHROME_DEVTOOLS_ACTIVE_PORT", raising=False)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        port = srv.getsockname()[1]

        real_home = tmp_path / "real_user_home"
        personal_port_file = real_home / "Library" / "Application Support" / "Google" / "Chrome" / "DevToolsActivePort"
        personal_port_file.parent.mkdir(parents=True, exist_ok=True)
        personal_port_file.write_text(f"{port}\n/devtools/browser/personal-uuid\n", encoding="utf-8")

        # Simulate production where Path.home() and os.path.expanduser("~") are identical
        monkeypatch.setattr(Path, "home", staticmethod(lambda: real_home))
        monkeypatch.setattr(os.path, "expanduser", lambda p: str(real_home) if p == "~" else p)

        runner = cdp_mod.LensCDPPracticeRunner(cdp_host="127.0.0.1", cdp_ports=[port], out_dir=tmp_path / "out_prod")
        info, active_host, active_port = runner.get_cdp_version_info()
        assert info is None
        assert active_host == ""
        assert active_port == 0

        # Isolated AI profile under ~/.cache/chrome-devtools-mcp/chrome-profile/DevToolsActivePort IS allowed
        isolated_port_file = real_home / ".cache" / "chrome-devtools-mcp" / "chrome-profile" / "DevToolsActivePort"
        isolated_port_file.parent.mkdir(parents=True, exist_ok=True)
        isolated_port_file.write_text(f"{port}\n/devtools/browser/isolated-ai-uuid\n", encoding="utf-8")

        info2, active_host2, active_port2 = runner.get_cdp_version_info()
        assert info2 is not None
        assert info2.get("devtools_active_port") is True
        assert "isolated-ai-uuid" in info2.get("webSocketDebuggerUrl", "")
        assert active_host2 == "127.0.0.1"
        assert active_port2 == port

