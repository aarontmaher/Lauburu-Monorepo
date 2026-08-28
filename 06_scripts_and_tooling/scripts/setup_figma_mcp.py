#!/usr/bin/env python3
"""
setup_figma_mcp.py - Figma MCP Server Setup, Authentication & Settings Manager
==============================================================================
Part of the Lauburu Monorepo Rule #0 Zero-Mock Guardrail Infrastructure.

Automates the registration and configuration of the Figma Model Context Protocol
(MCP) server in ~/.gemini/settings.json with "trust": true.
Supports Personal Access Token (PAT) validation, interactive OAuth 2.0 browser
callback listener, atomic settings mutation with automatic backup and rollback,
and end-to-end health verification.

Exit Codes:
  0: Operation succeeded / Verification passed
  1: Validation error, authentication failure, or verification failed
  2: Configuration error or invalid arguments
"""

import os
import sys
import json
import time
import shutil
import glob
import urllib.request
import urllib.error
import urllib.parse
import argparse
import webbrowser
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.gemini/settings.json")
DEFAULT_CLIENT_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "figma_mcp_client.py")
)
FIGMA_API_BASE = "https://api.figma.com/v1"


class FigmaAuthManager:
    """Handles Personal Access Token validation and OAuth 2.0 browser authorization."""

    @staticmethod
    def validate_pat(token: str, timeout: int = 8) -> Dict[str, Any]:
        """
        Validates Personal Access Token against Figma API /v1/me.
        Returns dictionary with validation status, user profile data, and error details.
        """
        cleaned_token = token.strip()
        if not cleaned_token:
            return {
                "valid": False,
                "user": None,
                "error": "Empty or whitespace token provided."
            }

        url = f"{FIGMA_API_BASE}/me"
        # Figma accepts X-Figma-Token for PATs or Authorization: Bearer
        headers = {
            "User-Agent": "Lauburu-Figma-MCP-Setup/1.0",
            "Accept": "application/json"
        }
        if cleaned_token.startswith("figd_"):
            headers["X-Figma-Token"] = cleaned_token
        else:
            headers["Authorization"] = f"Bearer {cleaned_token}"

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    user_data = json.loads(raw_data)
                    return {
                        "valid": True,
                        "user": user_data,
                        "error": None
                    }
                return {
                    "valid": False,
                    "user": None,
                    "error": f"Unexpected HTTP status {resp.status}"
                }
        except urllib.error.HTTPError as e:
            err_msg = f"HTTP {e.code}: {e.reason}"
            if e.code == 401 or e.code == 403:
                err_msg = f"Invalid or expired Figma token ({e.code} {e.reason})"
            return {"valid": False, "user": None, "error": err_msg}
        except urllib.error.URLError as e:
            return {"valid": False, "user": None, "error": f"Network error connecting to Figma: {e.reason}"}
        except Exception as e:
            return {"valid": False, "user": None, "error": f"Validation error: {str(e)}"}

    @staticmethod
    def start_oauth_flow(
        client_id: str,
        client_secret: str,
        port: int = 3000,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Starts an interactive OAuth 2.0 authorization server on localhost:port/oauth/callback.
        Opens default browser, captures callback authorization code, and exchanges for tokens.
        """
        state = secrets.token_urlsafe(24)
        auth_result = {
            "code": None,
            "state_received": None,
            "error": None,
            "received_event": threading.Event()
        }
        redirect_uri = f"http://localhost:{port}/oauth/callback"

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress console clutter

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path in ("/oauth/callback", "/callback"):
                    qs = urllib.parse.parse_qs(parsed.query)
                    code = qs.get("code", [None])[0]
                    recv_state = qs.get("state", [None])[0]
                    err = qs.get("error", [None])[0]

                    if err:
                        auth_result["error"] = f"OAuth authorization denied: {err}"
                        self.send_response(400)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(b"<html><body><h2>Authorization Denied</h2></body></html>")
                        auth_result["received_event"].set()
                        return

                    if recv_state != state:
                        auth_result["error"] = "Security state mismatch (possible CSRF)."
                        self.send_response(400)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(b"<html><body><h2>State verification failed.</h2></body></html>")
                        auth_result["received_event"].set()
                        return

                    if not code:
                        auth_result["error"] = "No authorization code found in callback query."
                        self.send_response(400)
                        self.end_headers()
                        auth_result["received_event"].set()
                        return

                    auth_result["code"] = code
                    auth_result["state_received"] = recv_state

                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html_content = (
                        "<!DOCTYPE html>"
                        "<html>"
                        "<head><title>Figma MCP Authentication</title></head>"
                        "<body style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; "
                        "text-align: center; padding: 60px 20px; background: #0f172a; color: #f8fafc;'>"
                        "<div style='max-width: 500px; margin: 0 auto; background: #1e293b; padding: 30px; "
                        "border-radius: 12px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.5);'>"
                        "<h1 style='color: #22c55e; margin-bottom: 12px;'>Authentication Successful</h1>"
                        "<p style='color: #94a3b8; font-size: 16px; line-height: 1.5;'>"
                        "Figma MCP authorization has been verified and registered with the Lauburu Swarm."
                        "</p>"
                        "<p style='color: #64748b; font-size: 14px;'>You can now safely close this browser window.</p>"
                        "</div>"
                        "</body>"
                        "</html>"
                    )
                    self.wfile.write(html_content.encode("utf-8"))
                    auth_result["received_event"].set()
                else:
                    self.send_response(404)
                    self.end_headers()

        try:
            server = HTTPServer(("127.0.0.1", port), OAuthCallbackHandler)
        except OSError as e:
            return {"success": False, "error": f"Failed to bind callback server on port {port}: {e}"}

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        auth_url = (
            f"https://www.figma.com/oauth"
            f"?client_id={urllib.parse.quote(client_id)}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&scope=file_read"
            f"&state={urllib.parse.quote(state)}"
            f"&response_type=code"
        )

        print(f"\n[OAuth] Starting Figma OAuth 2.0 authentication flow...")
        print(f"[OAuth] Local callback listener ready on: {redirect_uri}")
        print(f"[OAuth] Opening browser to: {auth_url}\n")

        try:
            webbrowser.open(auth_url)
        except Exception:
            print(f"[OAuth] Could not automatically open browser. Please open the link manually above.")

        # Wait for callback or timeout
        received = auth_result["received_event"].wait(timeout=timeout)
        server.shutdown()
        server.server_close()

        if not received or not auth_result["code"]:
            err_msg = auth_result["error"] or f"Timed out waiting for browser callback ({timeout}s)."
            return {"success": False, "error": err_msg}

        # Exchange authorization code for token
        print("[OAuth] Authorization code received. Exchanging for access token...")
        token_endpoint = f"{FIGMA_API_BASE}/oauth/token"
        payload_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": auth_result["code"],
            "grant_type": "authorization_code"
        }
        encoded_payload = urllib.parse.urlencode(payload_data).encode("utf-8")
        token_req = urllib.request.Request(
            token_endpoint,
            data=encoded_payload,
            headers={
                "User-Agent": "Lauburu-Figma-MCP-Setup/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(token_req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                access_token = resp_data.get("access_token")
                if not access_token:
                    return {"success": False, "error": "No access_token found in response from Figma."}
                return {
                    "success": True,
                    "access_token": access_token,
                    "refresh_token": resp_data.get("refresh_token"),
                    "expires_in": resp_data.get("expires_in"),
                    "user_id": resp_data.get("user_id"),
                    "raw": resp_data,
                    "error": None
                }
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            return {"success": False, "error": f"Token exchange failed (HTTP {e.code}): {body or e.reason}"}
        except Exception as e:
            return {"success": False, "error": f"Token exchange error: {str(e)}"}


class SettingsConfigurator:
    """Manages atomic read/write, backup, rollback, and validation of ~/.gemini/settings.json."""

    def __init__(self, settings_path: str = DEFAULT_SETTINGS_PATH):
        self.settings_path = os.path.expanduser(settings_path)

    def load_settings(self) -> Dict[str, Any]:
        """Loads and parses the settings file. Returns empty structure if missing."""
        if not os.path.exists(self.settings_path):
            return {"mcpServers": {}}
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {"mcpServers": {}}
                return json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse settings at '{self.settings_path}': {e}")

    def create_backup(self) -> Optional[str]:
        """Creates a timestamped backup of the settings file."""
        if not os.path.exists(self.settings_path):
            return None
        timestamp = int(time.time())
        backup_path = f"{self.settings_path}.bak.{timestamp}"
        try:
            shutil.copy2(self.settings_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"[Warning] Failed to create settings backup: {e}", file=sys.stderr)
            return None

    def rollback_latest_backup(self) -> Tuple[bool, str]:
        """Restores settings from the most recent backup file."""
        pattern = f"{self.settings_path}.bak.*"
        backups = sorted(glob.glob(pattern), reverse=True)
        if not backups:
            return False, "No backup files found."
        latest = backups[0]
        try:
            shutil.copy2(latest, self.settings_path)
            return True, f"Successfully restored settings from: {latest}"
        except Exception as e:
            return False, f"Failed to restore from backup '{latest}': {e}"

    def write_settings_atomically(self, settings_dict: Dict[str, Any]) -> bool:
        """Writes settings dictionary to disk using a temporary file and atomic replace."""
        dir_name = os.path.dirname(self.settings_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        self.create_backup()
        tmp_path = f"{self.settings_path}.tmp.{os.getpid()}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp_path, self.settings_path)
            return True
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise RuntimeError(f"Atomic write to '{self.settings_path}' failed: {e}")

    def register_stdio_server(
        self,
        client_script_path: str = DEFAULT_CLIENT_SCRIPT,
        token: Optional[str] = None,
        python_exec: str = sys.executable
    ) -> bool:
        """
        Registers the local stdio Figma MCP server into settings.json with "trust": true.
        """
        settings = self.load_settings()
        if "mcpServers" not in settings or not isinstance(settings["mcpServers"], dict):
            settings["mcpServers"] = {}

        abs_script = os.path.abspath(client_script_path)
        env_dict = {"FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}"}
        if token:
            env_dict["FIGMA_ACCESS_TOKEN"] = token.strip()

        settings["mcpServers"]["figma"] = {
            "command": python_exec,
            "args": [
                abs_script,
                "--stdio"
            ],
            "env": env_dict,
            "trust": True,
            "description": "Native Figma MCP server providing live REST AST extraction (get_file, get_file_nodes, get_image, get_comments, get_me) under Rule #0."
        }

        return self.write_settings_atomically(settings)

    def register_remote_server(
        self,
        remote_url: str = "https://mcp.figma.com/mcp"
    ) -> bool:
        """
        Registers the official Figma Remote MCP endpoint with "trust": true.
        """
        settings = self.load_settings()
        if "mcpServers" not in settings or not isinstance(settings["mcpServers"], dict):
            settings["mcpServers"] = {}

        settings["mcpServers"]["figma-remote"] = {
            "url": remote_url,
            "trust": True,
            "description": "Official Figma Remote MCP endpoint with OAuth browser authentication."
        }

        return self.write_settings_atomically(settings)

    def unregister_server(self, server_name: str = "figma") -> bool:
        """Removes the specified MCP server entry from settings.json."""
        settings = self.load_settings()
        servers = settings.get("mcpServers", {})
        if server_name in servers:
            del servers[server_name]
            settings["mcpServers"] = servers
            return self.write_settings_atomically(settings)
        return False

    def get_status(self) -> Dict[str, Any]:
        """Returns registration status and environment inspection."""
        settings = self.load_settings()
        servers = settings.get("mcpServers", {})
        figma_stdio = servers.get("figma")
        figma_remote = servers.get("figma-remote")
        env_token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()

        token_preview = "NOT SET"
        if env_token:
            if len(env_token) > 10:
                token_preview = f"{env_token[:6]}...{env_token[-4:]}"
            else:
                token_preview = "SET (masked)"

        return {
            "settings_path": self.settings_path,
            "settings_exists": os.path.exists(self.settings_path),
            "stdio_registered": figma_stdio is not None,
            "stdio_config": figma_stdio,
            "remote_registered": figma_remote is not None,
            "remote_config": figma_remote,
            "env_token_present": bool(env_token),
            "env_token_preview": token_preview
        }


class HealthVerifier:
    """Performs multi-stage health and handshake verification for Figma MCP."""

    @staticmethod
    def run_stdio_handshake(
        client_script_path: str = DEFAULT_CLIENT_SCRIPT,
        python_exec: str = sys.executable,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        Spawns the figma_mcp_client in --stdio mode and verifies JSON-RPC 2.0
        'initialize' and 'tools/list' exchanges.
        """
        if not os.path.exists(client_script_path):
            return {
                "success": False,
                "error": f"Client script not found at '{client_script_path}'"
            }

        cmd = [python_exec, client_script_path, "--stdio"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception as e:
            return {"success": False, "error": f"Failed to spawn process '{cmd}': {e}"}

        # Step 1: Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": "probe-init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "setup_figma_mcp_verifier", "version": "1.0.0"}
            }
        }
        try:
            stdout_data, _ = proc.communicate(
                input=json.dumps(init_req) + "\n" + json.dumps({
                    "jsonrpc": "2.0",
                    "id": "probe-tools-2",
                    "method": "tools/list",
                    "params": {}
                }) + "\n",
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"success": False, "error": f"Stdio JSON-RPC handshake timed out after {timeout}s"}
        except Exception as e:
            proc.kill()
            return {"success": False, "error": f"Stdio communication error: {e}"}

        lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]
        responses = []
        for line in lines:
            try:
                responses.append(json.loads(line))
            except Exception:
                continue

        if not responses:
            return {"success": False, "error": f"No valid JSON-RPC responses returned. Raw output: {stdout_data}"}

        # Verify tool list
        tools_found = []
        for resp in responses:
            if "result" in resp and isinstance(resp["result"], dict) and "tools" in resp["result"]:
                for t in resp["result"]["tools"]:
                    tools_found.append(t.get("name"))

        expected_tools = {"get_file", "get_file_nodes", "get_image", "get_comments", "get_me"}
        missing_tools = expected_tools - set(tools_found)

        if missing_tools:
            return {
                "success": False,
                "tools_found": tools_found,
                "error": f"Missing expected tools in MCP tools/list: {missing_tools}"
            }

        return {
            "success": True,
            "tools_found": tools_found,
            "response_count": len(responses)
        }


def print_banner():
    print("=" * 68)
    print("  🎨 FIGMA MCP SERVER SETUP & REGISTRATION HARNESS (RULE #0)")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(
        description="Figma MCP Registration, Authentication & Validation CLI (Rule #0 Compliance)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register stdio Figma MCP server in ~/.gemini/settings.json:
  python3 setup_figma_mcp.py --register

  # Register with verified Personal Access Token (PAT):
  python3 setup_figma_mcp.py --auth-token figd_abc123...

  # Check registration status and environment:
  python3 setup_figma_mcp.py --status

  # Run comprehensive health and stdio handshake probe:
  python3 setup_figma_mcp.py --verify

  # Unregister figma MCP server:
  python3 setup_figma_mcp.py --unregister
"""
    )
    parser.add_argument("--register", action="store_true", help="Register stdio Figma MCP server into settings.json")
    parser.add_argument("--register-remote", action="store_true", help="Register remote Figma MCP endpoint into settings.json")
    parser.add_argument("--unregister", action="store_true", help="Remove Figma MCP server from settings.json")
    parser.add_argument("--status", action="store_true", help="Display current MCP registration status and token preview")
    parser.add_argument("--auth-token", type=str, default=None, help="Validate PAT and save into settings.json")
    parser.add_argument("--auth-oauth", action="store_true", help="Launch interactive browser OAuth 2.0 authorization")
    parser.add_argument("--oauth-client-id", type=str, default=None, help="Figma OAuth Client ID")
    parser.add_argument("--oauth-client-secret", type=str, default=None, help="Figma OAuth Client Secret")
    parser.add_argument("--oauth-port", type=int, default=3000, help="Local OAuth callback port (default: 3000)")
    parser.add_argument("--verify", action="store_true", help="Execute end-to-end health verification and stdio handshake probe")
    parser.add_argument("--rollback", action="store_true", help="Roll back settings.json to the most recent backup")
    parser.add_argument("--settings-path", type=str, default=DEFAULT_SETTINGS_PATH, help=f"Custom settings.json path (default: {DEFAULT_SETTINGS_PATH})")
    parser.add_argument("--client-script", type=str, default=DEFAULT_CLIENT_SCRIPT, help=f"Path to figma_mcp_client.py (default: {DEFAULT_CLIENT_SCRIPT})")

    args = parser.parse_args()
    configurator = SettingsConfigurator(settings_path=args.settings_path)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    print_banner()

    # 1. Rollback
    if args.rollback:
        success, msg = configurator.rollback_latest_backup()
        if success:
            print(f"✅ {msg}")
            sys.exit(0)
        else:
            print(f"❌ {msg}", file=sys.stderr)
            sys.exit(1)

    # 2. Unregister
    if args.unregister:
        unreg_stdio = configurator.unregister_server("figma")
        unreg_remote = configurator.unregister_server("figma-remote")
        if unreg_stdio or unreg_remote:
            print("✅ Successfully unregistered Figma MCP server(s) from settings.json.")
        else:
            print("ℹ️  No Figma MCP server entries were found in settings.json.")
        sys.exit(0)

    # 3. Auth Token (PAT)
    if args.auth_token:
        token = args.auth_token.strip()
        print(f"🔍 Validating Personal Access Token against Figma API ({FIGMA_API_BASE}/me)...")
        val_res = FigmaAuthManager.validate_pat(token)
        if val_res["valid"]:
            user_info = val_res["user"]
            email = user_info.get("email", "unknown")
            handle = user_info.get("handle", "unknown")
            user_id = user_info.get("id", "unknown")
            print(f"✅ PAT Validated successfully!")
            print(f"   User: {handle} ({email}) [ID: {user_id}]")
            print("💾 Registering Figma MCP server into settings.json with verified token...")
            configurator.register_stdio_server(
                client_script_path=args.client_script,
                token=token
            )
            print("✅ Registration complete with trust: true.")
            sys.exit(0)
        else:
            print(f"❌ PAT Validation Failed: {val_res['error']}", file=sys.stderr)
            print("   Note: Under Monorepo Rule #0, only authentic and active tokens are accepted.", file=sys.stderr)
            sys.exit(1)

    # 4. Auth OAuth
    if args.auth_oauth:
        cid = args.oauth_client_id or os.environ.get("FIGMA_OAUTH_CLIENT_ID")
        csec = args.oauth_client_secret or os.environ.get("FIGMA_OAUTH_CLIENT_SECRET")
        if not cid or not csec:
            print("❌ OAuth requires client ID and client secret.", file=sys.stderr)
            print("   Provide via --oauth-client-id / --oauth-client-secret or environment variables.", file=sys.stderr)
            sys.exit(2)
        oauth_res = FigmaAuthManager.start_oauth_flow(
            client_id=cid,
            client_secret=csec,
            port=args.oauth_port
        )
        if oauth_res["success"]:
            token = oauth_res["access_token"]
            print("✅ OAuth Token Exchange Successful!")
            configurator.register_stdio_server(
                client_script_path=args.client_script,
                token=token
            )
            print("✅ Registration complete with trust: true.")
            sys.exit(0)
        else:
            print(f"❌ OAuth Flow Failed: {oauth_res['error']}", file=sys.stderr)
            sys.exit(1)

    # 5. Register Stdio
    if args.register:
        print(f"📝 Registering stdio Figma MCP server into: {configurator.settings_path}")
        print(f"   Client Script: {args.client_script}")
        configurator.register_stdio_server(client_script_path=args.client_script)
        print("✅ Registered 'figma' MCP server with 'trust': true.")

    # 6. Register Remote
    if args.register_remote:
        print(f"📝 Registering remote Figma MCP endpoint into: {configurator.settings_path}")
        configurator.register_remote_server()
        print("✅ Registered 'figma-remote' MCP server with 'trust': true.")

    # 7. Status
    if args.status or (not args.verify and not args.register and not args.register_remote):
        status = configurator.get_status()
        print("\n📊 CURRENT FIGMA MCP REGISTRATION STATUS:")
        print(f"  Settings Path:      {status['settings_path']}")
        print(f"  File Exists:        {'Yes 🟢' if status['settings_exists'] else 'No 🔴'}")
        print(f"  Stdio Registered:   {'Yes 🟢' if status['stdio_registered'] else 'No ⚪'}")
        if status['stdio_registered']:
            cfg = status['stdio_config']
            print(f"    Command:          {cfg.get('command')} {cfg.get('args', [])}")
            print(f"    Trust Flag:       {'true 🟢' if cfg.get('trust') else 'false 🔴'}")
        print(f"  Remote Registered:  {'Yes 🟢' if status['remote_registered'] else 'No ⚪'}")
        if status['remote_registered']:
            cfg = status['remote_config']
            print(f"    URL:              {cfg.get('url')}")
            print(f"    Trust Flag:       {'true 🟢' if cfg.get('trust') else 'false 🔴'}")
        print(f"  Env Token Status:   {status['env_token_preview']}")
        print("-" * 68)

    # 8. Verify
    if args.verify:
        print("\n🔬 RUNNING MULTI-TIER HEALTH VERIFICATION & HANDSHAKE PROBE:")
        all_passed = True

        # Check Python
        print(" [1/4] Checking Python Runtime Executable...")
        print(f"       Python: {sys.executable} ({sys.version.split()[0]}) 🟢")

        # Check Script Path
        print(f" [2/4] Checking Client Script: {args.client_script}...")
        if os.path.exists(args.client_script):
            print("       Client script exists and is readable 🟢")
        else:
            print(f"       Client script not found at {args.client_script} 🔴")
            all_passed = False

        # Check Stdio JSON-RPC Handshake
        print(" [3/4] Performing Stdio JSON-RPC 2.0 Handshake (initialize + tools/list)...")
        hs_res = HealthVerifier.run_stdio_handshake(
            client_script_path=args.client_script,
            python_exec=sys.executable
        )
        if hs_res["success"]:
            tools_str = ", ".join(hs_res["tools_found"])
            print(f"       Handshake successful! Exposed tools: [{tools_str}] 🟢")
        else:
            print(f"       Handshake failed: {hs_res['error']} 🔴")
            all_passed = False

        # Check Token / Network connectivity
        print(" [4/4] Checking Figma API Token / Connectivity...")
        env_token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
        if env_token:
            probe_res = FigmaAuthManager.validate_pat(env_token)
            if probe_res["valid"]:
                u = probe_res["user"]
                print(f"       Live Figma API probe succeeded! Authenticated as: {u.get('handle')} 🟢")
            else:
                print(f"       Figma API probe returned: {probe_res['error']} 🟡 (Set valid token to query live canvas)")
        else:
            print("       FIGMA_ACCESS_TOKEN not set in environment. (Optional for stdio handshake test, required for live Figma canvas AST extraction) ⚪")

        print("-" * 68)
        if all_passed:
            print("🎉 VERIFICATION PASSED: Figma MCP harness is fully operational!")
            sys.exit(0)
        else:
            print("❌ VERIFICATION FAILED: Issues detected above.")
            sys.exit(1)


if __name__ == "__main__":
    main()
