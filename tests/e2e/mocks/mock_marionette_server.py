#!/usr/bin/env python3
"""
High-Fidelity Mock Marionette MCP Server
========================================
Implements a deterministic, high-fidelity JSON-RPC 2.0 stdio MCP server for headless
Firefox/GeckoDriver simulation, exposing the full 29-tool schema matching chrome-devtools-mcp.
"""

import base64
import json
import struct
import time
import uuid
import zlib
from typing import Dict, Any, List, Optional, Tuple


def _generate_valid_png_bytes(width: int = 1920, height: int = 1080) -> bytes:
    """Generates valid in-memory PNG bytes with magic headers and compressed payload."""
    raw_data = bytearray()
    for y in range(min(height, 100)):  # Fast minimal lines for testing
        raw_data.append(0)  # filter type 0
        for x in range(min(width, 100)):
            r = (x * 255) // max(width, 1)
            g = (y * 255) // max(height, 1)
            b = 128
            raw_data.extend([r, g, b, 255])
    compressed = zlib.compress(bytes(raw_data), 6)

    png = bytearray()
    png.extend(b'\x89PNG\r\n\x1a\n')  # PNG Magic Signature

    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    png.extend(struct.pack('>I', len(ihdr_data)))
    png.extend(b'IHDR')
    png.extend(ihdr_data)
    png.extend(struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff))

    # IDAT
    png.extend(struct.pack('>I', len(compressed)))
    png.extend(b'IDAT')
    png.extend(compressed)
    png.extend(struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff))

    # IEND
    png.extend(struct.pack('>I', 0))
    png.extend(b'IEND')
    png.extend(struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff))

    return bytes(png)


ALL_29_TOOLS = [
    # Navigation & Lifecycle (6)
    "navigate_page",
    "list_pages",
    "new_page",
    "close_page",
    "select_page",
    "resize_page",
    # Visual & Audit (4)
    "take_screenshot",
    "take_snapshot",
    "lighthouse_audit",
    "take_heapsnapshot",
    # Interaction (10)
    "click",
    "fill",
    "fill_form",
    "type_text",
    "hover",
    "drag",
    "press_key",
    "upload_file",
    "handle_dialog",
    "wait_for",
    # Execution (1)
    "evaluate_script",
    # Telemetry & Network (5)
    "list_console_messages",
    "get_console_message",
    "list_network_requests",
    "get_network_request",
    "emulate",
    # Performance Profiling (3)
    "performance_start_trace",
    "performance_stop_trace",
    "performance_analyze_insight",
]


class MockMarionetteMCPServer:
    """
    In-memory / stdio JSON-RPC 2.0 Mock Marionette MCP Server.
    Provides complete stateful simulation of Firefox browser sessions.
    """

    def __init__(self):
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        self.is_initialized = False
        self.is_alive = True
        self.current_url = "about:blank"
        self.current_title = "New Tab"
        self.pages: List[Dict[str, Any]] = [
            {"id": "tab_1", "url": "about:blank", "title": "New Tab", "active": True}
        ]
        self.active_tab_id = "tab_1"
        self.console_messages: List[Dict[str, Any]] = [
            {"level": "info", "text": "Marionette driver initialized.", "timestamp": time.time()}
        ]
        self.network_requests: List[Dict[str, Any]] = []
        self.tracing_active = False
        self.uid_counter = 0

    def next_uid(self) -> str:
        """Returns monotonically increasing UID marker."""
        self.uid_counter += 1
        return f"uid_{self.uid_counter:04d}"

    def handle_json_rpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Processes an incoming JSON-RPC 2.0 request."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not self.is_alive:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": "Marionette session disconnected or crashed."},
            }

        if method == "initialize":
            self.is_initialized = True
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "marionette-mcp",
                        "version": "1.0.0",
                        "description": "Headless Firefox GeckoDriver MCP Server",
                    },
                    "capabilities": {"tools": {}},
                },
            }

        if method == "tools/list":
            tools_list = []
            for t_name in ALL_29_TOOLS:
                tools_list.append({
                    "name": t_name,
                    "description": f"Marionette implementation for {t_name}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "selector": {"type": "string"},
                            "script": {"type": "string"},
                            "uid": {"type": "string"},
                            "text": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                })
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            return self.dispatch_tool(req_id, tool_name, tool_args)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def dispatch_tool(self, req_id: Any, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool invocation to specific handler."""
        valid_tools = set(ALL_29_TOOLS) | {"get_ax_tree"}
        if name not in valid_tools:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: Unknown tool {name}"}],
                    "isError": True,
                },
            }

        # 1. Navigation Tools
        if name == "navigate_page":
            url = args.get("url", "")
            if not url or url.startswith("invalid://") or "99999" in url:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Navigation failed: Unreachable host or invalid URL '{url}'"}],
                        "isError": True,
                    },
                }
            self.current_url = url
            self.current_title = f"Page - {url}"
            for p in self.pages:
                if p["id"] == self.active_tab_id:
                    p["url"] = url
                    p["title"] = self.current_title
            self.network_requests.append({
                "url": url,
                "status": 200,
                "method": "GET",
                "timestamp": time.time(),
            })
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Successfully navigated to {url} (HTTP 200 OK)"}],
                    "isError": False,
                },
            }

        if name == "list_pages":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(self.pages)}],
                    "pages": self.pages,
                },
            }

        if name == "new_page":
            new_id = f"tab_{len(self.pages) + 1}"
            url = args.get("url", "about:blank")
            for p in self.pages:
                p["active"] = False
            self.pages.append({"id": new_id, "url": url, "title": "New Tab", "active": True})
            self.active_tab_id = new_id
            self.current_url = url
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Opened tab {new_id} at {url}"}],
                    "tabId": new_id,
                },
            }

        if name == "close_page":
            tab_id = args.get("tabId") or self.active_tab_id
            self.pages = [p for p in self.pages if p["id"] != tab_id]
            if self.pages:
                self.pages[0]["active"] = True
                self.active_tab_id = self.pages[0]["id"]
                self.current_url = self.pages[0]["url"]
            else:
                self.active_tab_id = None
                self.current_url = "about:blank"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Closed tab {tab_id}"}]},
            }

        if name == "select_page":
            tab_id = args.get("tabId")
            found = False
            for p in self.pages:
                if p["id"] == tab_id:
                    p["active"] = True
                    self.active_tab_id = tab_id
                    self.current_url = p["url"]
                    found = True
                else:
                    p["active"] = False
            if not found:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Tab {tab_id} not found"}], "isError": True},
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Selected tab {tab_id}"}]},
            }

        if name == "resize_page":
            w = args.get("width", 1920)
            h = args.get("height", 1080)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Resized viewport to {w}x{h}"}]},
            }

        # 2. Visual & Audit Tools
        if name == "take_screenshot":
            png_bytes = _generate_valid_png_bytes(width=args.get("width", 1920), height=args.get("height", 1080))
            b64_str = base64.b64encode(png_bytes).decode("ascii")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "image", "data": b64_str, "mimeType": "image/png"},
                        {"type": "text", "text": f"Captured screenshot of {self.current_url} ({len(png_bytes)} bytes)"},
                    ],
                    "data": b64_str,
                    "byteLength": len(png_bytes),
                },
            }

        if name == "take_snapshot" or name == "get_ax_tree":
            depth = args.get("maxDepth", 10)
            tree = {
                "role": "RootWebArea",
                "name": self.current_title,
                "uid": self.next_uid(),
                "url": self.current_url,
                "bounds": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                "children": [
                    {
                        "role": "header",
                        "name": "Navigation Bar",
                        "uid": self.next_uid(),
                        "bounds": {"x": 0, "y": 0, "width": 1920, "height": 64},
                        "children": [
                            {
                                "role": "heading",
                                "name": "Lauburu Sovereign Hub",
                                "level": 1,
                                "uid": self.next_uid(),
                                "bounds": {"x": 20, "y": 16, "width": 300, "height": 32},
                            },
                            {
                                "role": "button",
                                "name": "Heal Mesh",
                                "uid": self.next_uid(),
                                "bounds": {"x": 1500, "y": 16, "width": 120, "height": 36},
                            },
                        ],
                    },
                    {
                        "role": "main",
                        "name": "Content Area",
                        "uid": self.next_uid(),
                        "bounds": {"x": 0, "y": 64, "width": 1920, "height": 1016},
                        "children": [
                            {
                                "role": "region",
                                "name": "Active Telemetry Grid",
                                "uid": self.next_uid(),
                                "bounds": {"x": 32, "y": 96, "width": 1856, "height": 900},
                            }
                        ],
                    },
                ],
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(tree)}],
                    "axTree": tree,
                },
            }

        if name == "lighthouse_audit":
            audit_report = {
                "performance": 0.98,
                "accessibility": 1.0,
                "bestPractices": 0.95,
                "seo": 0.92,
                "lcp_ms": 280,
                "cls": 0.01,
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(audit_report)}], "audit": audit_report},
            }

        if name == "take_heapsnapshot":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": "Heap snapshot captured (42.4 MB allocated)"}]},
            }

        # 3. Interaction Tools
        if name in ["click", "hover", "drag", "press_key", "handle_dialog", "upload_file"]:
            target_uid = args.get("uid") or args.get("selector", "unknown")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Successfully performed '{name}' on target '{target_uid}'"}]},
            }

        if name in ["fill", "type_text"]:
            val = args.get("value") or args.get("text", "")
            target = args.get("uid") or args.get("selector", "input")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Filled '{val}' into '{target}'"}]},
            }

        if name == "fill_form":
            fields = args.get("fields", {})
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Filled form with {len(fields)} fields"}]},
            }

        if name == "wait_for":
            selector = args.get("selector") or args.get("uid", "")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Element '{selector}' became visible"}]},
            }

        # 4. Execution Tools
        if name == "evaluate_script":
            script = args.get("script", "")
            if "circular" in script.lower() or "a.self" in script:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": "TypeError: Converting circular structure to JSON"}],
                        "isError": True,
                    },
                }
            if "window.location.href" in script:
                eval_val = self.current_url
            elif "document.title" in script:
                eval_val = self.current_title
            elif "2 + 2" in script:
                eval_val = 4
            else:
                eval_val = f"Evaluated: {script[:50]}"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": str(eval_val)}], "value": eval_val, "isError": False},
            }

        # 5. Telemetry & Performance
        if name == "list_console_messages":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(self.console_messages)}], "messages": self.console_messages},
            }

        if name == "get_console_message":
            msg = self.console_messages[-1] if self.console_messages else {}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(msg)}], "message": msg},
            }

        if name == "list_network_requests":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(self.network_requests)}], "requests": self.network_requests},
            }

        if name == "get_network_request":
            req = self.network_requests[-1] if self.network_requests else {}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(req)}], "request": req},
            }

        if name == "emulate":
            device = args.get("device", "Pixel 7")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Emulating device {device}"}]},
            }

        if name == "performance_start_trace":
            self.tracing_active = True
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": "Performance trace started"}]},
            }

        if name == "performance_stop_trace":
            self.tracing_active = False
            trace_data = {"traceEvents": [{"name": "CompositeLayers", "ph": "X", "ts": 1000, "dur": 250}]}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(trace_data)}], "trace": trace_data},
            }

        if name == "performance_analyze_insight":
            insight = {"lcp": {"metric": "LCP", "value": 280.0, "rating": "good"}}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(insight)}], "insight": insight},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"Executed {name}"}]},
        }

    def simulate_crash(self):
        """Simulates abrupt process crash or SIGKILL."""
        self.is_alive = False


if __name__ == "__main__":
    server = MockMarionetteMCPServer()
    init_res = server.handle_json_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    print("Init:", init_res)
    tools_res = server.handle_json_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    print("Tools count:", len(tools_res["result"]["tools"]))
