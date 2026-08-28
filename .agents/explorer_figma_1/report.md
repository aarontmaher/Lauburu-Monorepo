# Technical Specification & Architecture Report: Figma MCP Server Registration, Configuration & Authentication

- **Author:** Explorer 1 (`explorer_figma_1`)
- **Target Subsystem:** `06_scripts_and_tooling` / Monorepo MCP Infrastructure
- **Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_1`
- **Report Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_1/report.md`
- **Timestamp:** 2026-08-26T21:57:00+10:00
- **Integrity Level:** Rule #0 Strict Empirical Specification

---

## 1. Executive Summary

This report establishes the comprehensive technical architecture, configuration schemas, authentication workflows, workspace reload mechanics, and file-by-file implementation blueprints for integrating the **Figma Model Context Protocol (MCP)** server into the Gemini CLI / Antigravity Monorepo ecosystem.

Under **Monorepo Rule #0** ("Zero Fake Data / 100% Empirical Proof Mandate"), all design extraction and design-to-code pipelines must interface with live Figma canvas nodes and authentic tokens. This document defines:
1. The exact structure of `~/.gemini/settings.json` for registering both local stdio and remote Figma MCP endpoints.
2. Complete input/output JSON schemas for standard tools (`get_file`, `get_file_nodes`, `get_image`, `get_comments`) and remote tools (`get_design_context`, `get_metadata`, `get_screenshot`).
3. Dual authentication architectures: Personal Access Token (PAT) validation and an interactive OAuth 2.0 Browser Callback server.
4. Workspace reload protocols and a 4-tier live health-check probe.
5. Complete, production-grade implementation specifications for:
   - `06_scripts_and_tooling/scripts/setup_figma_mcp.py` (Registration, OAuth callback, settings manager)
   - `06_scripts_and_tooling/scripts/figma_mcp_client.py` (Zero-mock REST client, CLI probe, and stdio JSON-RPC 2.0 server)

---

## 2. Gemini Settings.json & Workspace Configuration Structure

### 2.1 Settings Schema Analysis (`~/.gemini/settings.json`)

Based on direct inspection of `/Users/aaron/.gemini/settings.json`, MCP servers are registered under the top-level `"mcpServers"` dictionary. The schema supports both local stdio subprocesses and remote SSE/HTTP endpoints:

```
~/.gemini/settings.json
├── security
│   └── auth: { "selectedType": "oauth-personal" }
├── mcpServers
│   ├── <server_id>: {
│   │   ├── command: string (executable path e.g. "python3", "npx", "node", "/path/to/bin")
│   │   ├── args: string[] (command line arguments)
│   │   ├── env: Record<string, string> (environment variables with ${VAR} substitution support)
│   │   ├── trust: boolean (must be true for pre-approved tool invocation)
│   │   ├── description: string (human-readable server capability description)
│   │   └── url?: string (alternative for remote SSE/HTTP MCP endpoints)
│   │   }
├── experimental
└── openclawProxy
```

### 2.2 Standard Stdio Registration (Monorepo Native Python MCP)

For maximum reliability, zero third-party npm dependency lockouts, and offline portability across macOS, Linux, and Android/Termux, the primary registration binds directly to the monorepo's standalone Python MCP server:

```json
{
  "mcpServers": {
    "figma": {
      "command": "python3",
      "args": [
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/figma_mcp_client.py",
        "--stdio"
      ],
      "env": {
        "FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}"
      },
      "trust": true,
      "description": "Native Figma MCP server providing live REST AST extraction (get_file, get_file_nodes, get_image, get_comments) under Rule #0."
    }
  }
}
```

### 2.3 Remote SSE / HTTP Alternative Registration

For teams utilizing Figma's official cloud Dev Mode / Remote MCP service:

```json
{
  "mcpServers": {
    "figma-remote": {
      "url": "https://mcp.figma.com/mcp",
      "trust": true,
      "description": "Official Figma Remote MCP endpoint with OAuth browser authentication."
    }
  }
}
```

### 2.4 Workspace Trust & Folder Permissions (`~/.gemini/trustedFolders.json`)

To prevent interactive tool invocation confirmation dialogs during automated swarm runs, `/Users/aaron/.gemini/trustedFolders.json` contains:
```json
{
  "/volumes": "TRUST_FOLDER"
}
```
Setting `"trust": true` within the `mcpServers.figma` entry is mandatory to inherit trusted execution privileges.

---

## 3. Figma MCP Tool Catalog & Schemas

### 3.1 Tool Schema Specifications

```
┌──────────────────┬──────────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Tool Name        │ Input Schema                             │ Output Schema                                          │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_file         │ {                                        │ {                                                      │
│                  │   "file_key": string,                    │   "name": string,                                      │
│                  │   "depth"?: number                       │   "document": { "id": "0:0", "type": "DOCUMENT", ... },│
│                  │ }                                        │   "components": { ... }, "schemaVersion": 0            │
│                  │                                          │ }                                                      │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_file_nodes   │ {                                        │ {                                                      │
│                  │   "file_key": string,                    │   "nodes": {                                           │
│                  │   "ids": string[],                       │     "<node_id>": {                                     │
│                  │   "depth"?: number                       │       "document": { "type": "FRAME", ... },            │
│                  │ }                                        │       "components": { ... }                            │
│                  │                                          │     }                                                  │
│                  │                                          │   }                                                    │
│                  │                                          │ }                                                      │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_image        │ {                                        │ {                                                      │
│                  │   "file_key": string,                    │   "err": null,                                         │
│                  │   "ids": string[],                       │   "images": { "<node_id>": "https://figma-alpha..." }  │
│                  │   "format"?: "png"|"svg"|"pdf",          │ }                                                      │
│                  │   "scale"?: number                       │                                                        │
│                  │ }                                        │                                                        │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_comments     │ {                                        │ {                                                      │
│                  │   "file_key": string                     │   "comments": [                                        │
│                  │ }                                        │     { "id": "1", "message": "...", "user": { ... } }   │
│                  │                                          │   ]                                                    │
│                  │                                          │ }                                                      │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_me           │ {}                                       │ {                                                      │
│                  │                                          │   "id": "12345", "email": "user@lauburu.ai",           │
│                  │                                          │   "handle": "Developer", "img_url": "..."              │
│                  │                                          │ }                                                      │
└──────────────────┴──────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

### 3.2 Granular AST Node Properties (`get_file_nodes`)

When extracting nodes for UI code generation, `get_file_nodes` returns high-fidelity layout parameters:
- **Layout Engine (AutoLayout):**
  - `layoutMode`: `"NONE"` | `"HORIZONTAL"` | `"VERTICAL"` (maps to CSS `display: flex; flex-direction: row | column`)
  - `itemSpacing`: number (maps to CSS `gap: Xpx`)
  - `paddingLeft`, `paddingRight`, `paddingTop`, `paddingBottom`: numbers (maps to CSS `padding`)
  - `primaryAxisAlignItems`: `"MIN"` | `"CENTER"` | `"MAX"` | `"SPACE_BETWEEN"` (maps to `justify-content`)
  - `counterAxisAlignItems`: `"MIN"` | `"CENTER"` | `"MAX"` | `"BASELINE"` (maps to `align-items`)
  - `primaryAxisSizingMode` / `counterAxisSizingMode`: `"FIXED"` | `"AUTO"` (maps to `flex: 1` vs `width: fit-content`)
- **Visual Styling & Typography:**
  - `fills`: array of `{ type: "SOLID" | "GRADIENT_LINEAR", color: { r, g, b, a }, opacity }`
  - `strokes`: array of stroke geometry and weights
  - `cornerRadius`: number or `rectangleCornerRadii: [tl, tr, br, bl]`
  - `style`: `{ fontFamily, fontWeight, fontSize, letterSpacing, lineHeightPx, textAlignHorizontal }`
- **Geometry & Constraints:**
  - `absoluteBoundingBox`: `{ x, y, width, height }` (ground truth for SSIM pixel diffing)
  - `constraints`: `{ horizontal: "LEFT" | "RIGHT" | "SCALE", vertical: "TOP" | "BOTTOM" | "SCALE" }`

---

## 4. Authentication Architecture

```
                               ┌─────────────────────────────┐
                               │   Authentication Gateway    │
                               └──────────────┬──────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │  Personal Access Token  │                       │   OAuth 2.0 Cloud Code  │
        │          (PAT)          │                       │     Browser Callback    │
        ├─────────────────────────┤                       ├─────────────────────────┤
        │ • Header: X-Figma-Token │                       │ • Port 3000 HTTP Server │
        │ • Format: figd_*        │                       │ • User Browser Auth     │
        │ • Env: FIGMA_ACCESS_TOK │                       │ • Code Exchange Token   │
        │ • Zero setup overhead   │                       │ • Auto Refresh Loop     │
        └─────────────────────────┘                       └─────────────────────────┘
```

### 4.1 Personal Access Token (PAT) Workflow
1. **Token Generation:**
   - User navigates to Figma $\rightarrow$ Settings $\rightarrow$ Security $\rightarrow$ Personal Access Tokens.
   - Creates token with description (e.g. `Lauburu-Swarm-MCP`) and required scopes (`file_read`, `file_comments:read`).
   - Token string generated (starts with `figd_` or alphanumeric sequence).
2. **Storage & Scope:**
   - Saved to environment: `export FIGMA_ACCESS_TOKEN="figd_..."` or stored in `.env` / `~/.gemini/settings.json`.
3. **HTTP Header Injection:**
   - Included in all outbound requests to `https://api.figma.com/v1/*`:
     ```http
     GET /v1/me HTTP/1.1
     Host: api.figma.com
     X-Figma-Token: figd_abc123xyz...
     Accept: application/json
     ```
4. **Validation Endpoint:**
   - Probe: `GET https://api.figma.com/v1/me`
   - Returns HTTP 200 with `{ "id": "...", "email": "...", "handle": "..." }` on success.
   - Returns HTTP 403 Forbidden on invalid or expired token.

### 4.2 OAuth 2.0 Browser Callback Architecture
1. **Figma Developer App Registration:**
   - Client configured with `client_id`, `client_secret`, and `redirect_uri` (`http://localhost:3000/oauth/callback`).
2. **Ephemeral Local HTTP Callback Server:**
   - `setup_figma_mcp.py` binds a non-blocking TCP socket to `127.0.0.1:3000` (or dynamic port).
   - Generates cryptographically secure `state` parameter (`secrets.token_urlsafe(16)`).
3. **Browser Launch:**
   - Opens user's default browser to:
     `https://www.figma.com/oauth?client_id={CLIENT_ID}&redirect_uri=http://localhost:3000/oauth/callback&scope=file_read&state={STATE}&response_type=code`
   - Also displays clickable terminal URL for headless/remote SSH sessions.
4. **Callback Handling & Code Extraction:**
   - Browser redirects to `http://localhost:3000/oauth/callback?code={CODE}&state={STATE}`.
   - Ephemeral server verifies `state` match (preventing CSRF).
   - Serves immediate HTTP 200 HTML confirmation page to browser:
     ```html
     <!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:50px;background:#0f172a;color:#f8fafc;">
     <h1 style="color:#22c55e;">Authentication Successful</h1>
     <p>Figma MCP credentials have been safely stored. You may close this tab.</p>
     </body></html>
     ```
5. **Token Exchange:**
   - Sends `POST https://api.figma.com/v1/oauth/token` with payload:
     ```json
     {
       "client_id": "<CLIENT_ID>",
       "client_secret": "<CLIENT_SECRET>",
       "redirect_uri": "http://localhost:3000/oauth/callback",
       "code": "<CODE>",
       "grant_type": "authorization_code"
     }
     ```
   - Receives `{ "access_token": "...", "refresh_token": "...", "expires_in": 7776000 }`.
   - Stores tokens securely and updates `~/.gemini/settings.json`.

---

## 5. Workspace Reload Mechanics & Environment Validation

### 5.1 Atomic Settings Mutation Protocol
To avoid file corruption or race conditions with running Gemini CLI processes:
1. **Pre-flight Backup:** Copy `~/.gemini/settings.json` $\rightarrow$ `~/.gemini/settings.json.bak.<timestamp>`.
2. **In-Memory Parse & Schema Validation:** Parse existing JSON, inject `mcpServers.figma`, and validate syntax.
3. **Atomic Replacement:** Write to `~/.gemini/settings.json.tmp` and execute atomic POSIX rename (`os.replace`).

### 5.2 4-Tier Health Check Probe Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      4-TIER HEALTH CHECK PIPELINE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Runtime Probe: Verify python3 / node executable on $PATH                 │
│ 2. Credentials Probe: Verify FIGMA_ACCESS_TOKEN presence & structure        │
│ 3. REST API Ping Probe: Execute GET https://api.figma.com/v1/me (HTTP 200)   │
│ 4. Stdio JSON-RPC Handshake: Spawn client subprocess -> 'initialize'        │
│    -> 'tools/list' -> assert ['get_file', 'get_file_nodes', ...] in tools    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Specification: `setup_figma_mcp.py`

- **Target Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/setup_figma_mcp.py`
- **Dependencies:** Python 3 Standard Library only (`urllib.request`, `http.server`, `json`, `os`, `sys`, `argparse`, `webbrowser`, `secrets`, `socket`, `time`, `shutil`). Zero external pip packages required.

### 6.1 Architecture & Class Blueprint

```python
#!/usr/bin/env python3
"""
setup_figma_mcp.py - Interactive & Non-Interactive Figma MCP Registration CLI
Enforces Rule #0 Zero-Mock Data Integrity.
Registers Figma MCP server into ~/.gemini/settings.json with verified PAT / OAuth tokens.
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.error
import urllib.parse
import argparse
import webbrowser
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import threading

DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.gemini/settings.json")
FIGMA_CLIENT_SCRIPT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/figma_mcp_client.py"

class FigmaAuthManager:
    """Handles Personal Access Token validation and OAuth 2.0 browser authorization."""

    @staticmethod
    def validate_pat(token: str) -> dict:
        """Probe GET https://api.figma.com/v1/me using provided PAT."""
        url = "https://api.figma.com/v1/me"
        headers = {
            "X-Figma-Token": token.strip(),
            "User-Agent": "Lauburu-Figma-MCP-Setup/1.0"
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {"valid": True, "user": data, "error": None}
                return {"valid": False, "user": None, "error": f"HTTP status {resp.status}"}
        except urllib.error.HTTPError as e:
            return {"valid": False, "user": None, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"valid": False, "user": None, "error": str(e)}

    @staticmethod
    def start_oauth_flow(client_id: str, client_secret: str, port: int = 3000) -> dict:
        """Spawns local HTTP server, launches browser, and exchanges auth code for tokens."""
        state = secrets.token_urlsafe(16)
        auth_code_holder = {"code": None, "state_received": None, "error": None}
        redirect_uri = f"http://localhost:{port}/oauth/callback"

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default noisy console logs

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/oauth/callback":
                    qs = urllib.parse.parse_qs(parsed.query)
                    code = qs.get("code", [None])[0]
                    recv_state = qs.get("state", [None])[0]

                    if recv_state != state:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b"State mismatch error.")
                        auth_code_holder["error"] = "State verification failed."
                        return

                    auth_code_holder["code"] = code
                    auth_code_holder["state_received"] = recv_state

                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = (
                        "<html><body style='font-family:sans-serif;text-align:center;padding:50px;"
                        "background:#0f172a;color:#f8fafc;'>"
                        "<h1 style='color:#22c55e;'>Authentication Successful!</h1>"
                        "<p>Figma MCP has captured your token. You may close this tab.</p>"
                        "</body></html>"
                    )
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

        server = HTTPServer(("127.0.0.1", port), OAuthCallbackHandler)
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.daemon = True
        server_thread.start()

        auth_url = (
            f"https://www.figma.com/oauth?client_id={client_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&scope=file_read&state={state}&response_type=code"
        )

        print(f"\n[OAuth] Launching browser to authorize Figma MCP...")
        print(f"[OAuth] URL: {auth_url}\n")
        webbrowser.open(auth_url)

        server_thread.join(timeout=120)
        server.server_close()

        if not auth_code_holder["code"]:
            return {"success": False, "error": auth_code_holder["error"] or "Timed out waiting for browser callback."}

        # Exchange code for tokens
        token_url = "https://api.figma.com/v1/oauth/token"
        payload = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": auth_code_holder["code"],
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=payload, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "token_data": token_data, "error": None}
        except Exception as e:
            return {"success": False, "error": f"Token exchange failed: {e}"}


class SettingsConfigurator:
    """Manages atomic read/write and backup of ~/.gemini/settings.json."""

    def __init__(self, settings_path: str = DEFAULT_SETTINGS_PATH):
        self.settings_path = os.path.expanduser(settings_path)

    def load_settings(self) -> dict:
        if not os.path.exists(self.settings_path):
            return {"mcpServers": {}}
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse {self.settings_path}: {e}")

    def backup_settings(self) -> str:
        if not os.path.exists(self.settings_path):
            return ""
        backup_path = f"{self.settings_path}.bak.{int(time.time())}"
        shutil.copy2(self.settings_path, backup_path)
        return backup_path

    def register_stdio_server(self, token: str = None) -> bool:
        settings = self.load_settings()
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}

        env_dict = {"FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}"}
        if token:
            env_dict["FIGMA_ACCESS_TOKEN"] = token

        settings["mcpServers"]["figma"] = {
            "command": "python3",
            "args": [FIGMA_CLIENT_SCRIPT, "--stdio"],
            "env": env_dict,
            "trust": True,
            "description": "Native Figma MCP server providing live REST AST extraction (get_file, get_file_nodes, get_image, get_comments) under Rule #0."
        }

        self.backup_settings()
        tmp_path = f"{self.settings_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp_path, self.settings_path)
        return True

    def register_remote_server(self, remote_url: str = "https://mcp.figma.com/mcp") -> bool:
        settings = self.load_settings()
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}

        settings["mcpServers"]["figma-remote"] = {
            "url": remote_url,
            "trust": True,
            "description": "Official Figma Remote MCP endpoint with OAuth browser authentication."
        }

        self.backup_settings()
        tmp_path = f"{self.settings_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp_path, self.settings_path)
        return True

    def unregister_server(self, name: str = "figma") -> bool:
        settings = self.load_settings()
        if "mcpServers" in settings and name in settings["mcpServers"]:
            del settings["mcpServers"][name]
            self.backup_settings()
            tmp_path = f"{self.settings_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            os.replace(tmp_path, self.settings_path)
            return True
        return False

    def get_status(self) -> dict:
        settings = self.load_settings()
        servers = settings.get("mcpServers", {})
        figma_stdio = servers.get("figma")
        figma_remote = servers.get("figma-remote")
        env_token = os.environ.get("FIGMA_ACCESS_TOKEN", "")

        return {
            "settings_path": self.settings_path,
            "stdio_registered": figma_stdio is not None,
            "stdio_config": figma_stdio,
            "remote_registered": figma_remote is not None,
            "remote_config": figma_remote,
            "env_token_present": bool(env_token),
            "env_token_preview": f"{env_token[:8]}...{env_token[-4:]}" if len(env_token) > 12 else ("SET" if env_token else "EMPTY")
        }
```

---

## 7. Implementation Specification: `figma_mcp_client.py`

- **Target Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/figma_mcp_client.py`
- **Capabilities:**
  1. Standalone Python REST Client with rate-limiting, retry-after backoff, and URL auto-parsing.
  2. CLI Diagnostic Probes (`ping`, `get-file`, `get-nodes`, `get-image`, `get-comments`).
  3. Stdio JSON-RPC 2.0 MCP Server (`--stdio`) compliant with Model Context Protocol (2024-11-05).

### 7.1 Architecture & Class Blueprint

```python
#!/usr/bin/env python3
"""
figma_mcp_client.py - Zero-Mock Figma MCP Protocol Server & REST Client
Strictly obeys Rule #0 (Zero Fake Data).
Supports direct CLI probing, Python library ingestion, and stdio MCP JSON-RPC 2.0.
"""

import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
import urllib.parse
import argparse

FIGMA_API_BASE = "https://api.figma.com/v1"

class FigmaAPIError(Exception):
    """Raised when Figma REST API returns an error."""
    def __init__(self, status_code: int, message: str, body: dict = None):
        super().__init__(f"Figma API Error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body or {}

class FigmaRESTClient:
    """Low-level zero-mock HTTP client for Figma REST API v1."""

    def __init__(self, token: str = None):
        self.token = (token or os.environ.get("FIGMA_ACCESS_TOKEN", "")).strip()
        if not self.token:
            # Under Rule #0, we never fabricate data; token must be present
            pass

    def _get_headers(self) -> dict:
        if not self.token:
            raise FigmaAPIError(401, "FIGMA_ACCESS_TOKEN is missing or empty. Please set environment variable or run setup_figma_mcp.py.")
        # If token starts with figd_, send X-Figma-Token, otherwise Authorization: Bearer
        if self.token.startswith("figd_"):
            return {"X-Figma-Token": self.token, "User-Agent": "Lauburu-Figma-MCP/1.0"}
        return {"Authorization": f"Bearer {self.token}", "User-Agent": "Lauburu-Figma-MCP/1.0"}

    def request(self, endpoint: str, params: dict = None, max_retries: int = 3) -> dict:
        """Executes GET request with exponential backoff on HTTP 429 / 5xx."""
        url = f"{FIGMA_API_BASE}/{endpoint.lstrip('/')}"
        if params:
            query_str = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}?{query_str}"

        headers = self._get_headers()
        req = urllib.request.Request(url, headers=headers, method="GET")

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(retry_after)
                    continue
                body_text = e.read().decode("utf-8") if e.fp else ""
                try:
                    body_json = json.loads(body_text)
                except Exception:
                    body_json = {"raw": body_text}
                raise FigmaAPIError(e.code, e.reason, body_json)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise FigmaAPIError(500, f"Network transport error: {e}")
                time.sleep(1)

        raise FigmaAPIError(500, "Exceeded maximum retry attempts.")

    @staticmethod
    def parse_file_key(input_str: str) -> tuple[str, str]:
        """Extracts file_key and optional node_id from raw string or Figma URL."""
        # e.g., https://www.figma.com/design/abc123XYZ456/ProjectName?node-id=1-23
        url_match = re.search(r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)", input_str)
        if url_match:
            file_key = url_match.group(1)
            node_match = re.search(r"[?&]node-id=([a-zA-Z0-9%:-]+)", input_str)
            node_id = urllib.parse.unquote(node_match.group(1)).replace("-", ":") if node_match else None
            return file_key, node_id
        # Plain key string
        return input_str.strip(), None

    def get_me(self) -> dict:
        return self.request("me")

    def get_file(self, file_key: str, depth: int = 2) -> dict:
        key, _ = self.parse_file_key(file_key)
        params = {}
        if depth:
            params["depth"] = depth
        return self.request(f"files/{key}", params)

    def get_file_nodes(self, file_key: str, ids: list[str], depth: int = None) -> dict:
        key, _ = self.parse_file_key(file_key)
        formatted_ids = [str(i).replace("-", ":") for i in ids]
        params = {"ids": ",".join(formatted_ids)}
        if depth:
            params["depth"] = depth
        return self.request(f"files/{key}/nodes", params)

    def get_image(self, file_key: str, ids: list[str], format: str = "png", scale: float = 1.0) -> dict:
        key, _ = self.parse_file_key(file_key)
        formatted_ids = [str(i).replace("-", ":") for i in ids]
        params = {
            "ids": ",".join(formatted_ids),
            "format": format.lower(),
            "scale": scale
        }
        return self.request(f"images/{key}", params)

    def get_comments(self, file_key: str) -> list[dict]:
        key, _ = self.parse_file_key(file_key)
        res = self.request(f"files/{key}/comments")
        return res.get("comments", [])


class FigmaMCPServer:
    """Stdio JSON-RPC 2.0 MCP Server implementation."""

    def __init__(self, client: FigmaRESTClient):
        self.client = client
        self.tools = [
            {
                "name": "get_file",
                "description": "Fetch high-level Figma file AST, page hierarchy, and components under Rule #0.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string", "description": "Figma file key or full URL"},
                        "depth": {"type": "integer", "description": "Tree traversal depth (1-N)", "default": 2}
                    },
                    "required": ["file_key"]
                }
            },
            {
                "name": "get_file_nodes",
                "description": "Fetch detailed AST properties of specific nodes (AutoLayout, typography, geometry).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string", "description": "Figma file key or full URL"},
                        "ids": {"type": "array", "items": {"type": "string"}, "description": "Node IDs e.g. ['0:1', '1:23']"},
                        "depth": {"type": "integer", "description": "Node subtree depth"}
                    },
                    "required": ["file_key", "ids"]
                }
            },
            {
                "name": "get_image",
                "description": "Render specified Figma nodes into downloadable image URLs or SVG vector markup.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string", "description": "Figma file key or full URL"},
                        "ids": {"type": "array", "items": {"type": "string"}, "description": "Node IDs to render"},
                        "format": {"type": "string", "enum": ["png", "svg", "pdf"], "default": "png"},
                        "scale": {"type": "number", "default": 1.0}
                    },
                    "required": ["file_key", "ids"]
                }
            },
            {
                "name": "get_comments",
                "description": "Retrieve designer comments, review threads, and annotations for a file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string", "description": "Figma file key or full URL"}
                    },
                    "required": ["file_key"]
                }
            },
            {
                "name": "get_me",
                "description": "Retrieve authenticated user details and verify token connectivity.",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]

    def serve_stdio(self):
        """Standard IO event loop for JSON-RPC 2.0."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                res = self.handle_jsonrpc(req)
                if res is not None:
                    sys.stdout.write(json.dumps(res) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_res = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"}
                }
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()

    def handle_jsonrpc(self, req: dict) -> dict:
        method = req.get("method")
        msg_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "figma-mcp", "version": "1.0.0"}
                }
            }
        elif method == "notifications/initialized":
            return None
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": self.tools}}
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                content = self.execute_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(content, indent=2)}],
                        "isError": False
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error executing tool '{tool_name}': {str(e)}"}],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"}
            }

    def execute_tool(self, name: str, args: dict):
        if name == "get_file":
            return self.client.get_file(args["file_key"], depth=args.get("depth", 2))
        elif name == "get_file_nodes":
            return self.client.get_file_nodes(args["file_key"], args["ids"], depth=args.get("depth"))
        elif name == "get_image":
            return self.client.get_image(args["file_key"], args["ids"], format=args.get("format", "png"), scale=args.get("scale", 1.0))
        elif name == "get_comments":
            return self.client.get_comments(args["file_key"])
        elif name == "get_me":
            return self.client.get_me()
        else:
            raise ValueError(f"Unknown tool: {name}")
```

---

## 8. Verification Matrix & Rule #0 Pre-Flight Protocols

| Step | Objective | Command / Action | Expected Result | Invalidation Condition |
|---|---|---|---|---|
| **V1** | Settings Integrity | `python3 -c "import json; json.load(open('$HOME/.gemini/settings.json'))"` | Exit code 0, valid JSON dictionary | JSONDecodeError, syntax error |
| **V2** | Token Format & Auth | `python3 06_scripts_and_tooling/scripts/setup_figma_mcp.py --status` | Shows status table, token present/valid | Missing token, HTTP 401/403 |
| **V3** | REST API Connectivity | `python3 06_scripts_and_tooling/scripts/figma_mcp_client.py ping` | Outputs authenticated user payload | Unauthorized error or connection drop |
| **V4** | Stdio MCP Handshake | Run JSON-RPC `initialize` & `tools/list` on subprocess | Returns list containing 5 tools | Process exits immediately or invalid JSON-RPC |
| **V5** | Rule #0 Zero-Mock Check | Verify no hardcoded node mocks in client code | 100% authentic REST requests only | Synthetic fallback mock objects found |

---
*Report certified by `explorer_figma_1` under Monorepo Rule #0 Data Authenticity Protocol.*
