#!/usr/bin/env python3
"""
figma_mcp_client.py - Zero-Mock Figma REST API Client & Stdio MCP Server
========================================================================
Part of the Lauburu Monorepo Rule #0 Zero-Mock Guardrail Infrastructure.

Implements the Model Context Protocol (MCP) JSON-RPC 2.0 stdio server for Figma
along with a standalone zero-mock REST client and CLI probe utility.

Tools Exposed:
  - get_file: Fetches high-level document metadata, page hierarchy, and components.
  - get_file_nodes: Granular AST inspection of specific nodes (AutoLayout, typography, geometry).
  - get_image: Renders vector/raster images for visual parity diffing.
  - get_comments: Retrieves designer comments, annotations, and review threads.
  - get_me: Authenticates token and returns user profile.

Usage:
  # Stdio MCP Server (Spawned by Gemini CLI / MCP host):
  python3 figma_mcp_client.py --stdio

  # CLI Probes:
  python3 figma_mcp_client.py get-me
  python3 figma_mcp_client.py get-file --file-key <KEY_OR_URL> --depth 2
  python3 figma_mcp_client.py get-nodes --file-key <KEY_OR_URL> --ids 0:1,1:2
  python3 figma_mcp_client.py get-image --file-key <KEY_OR_URL> --ids 0:1 --format png
  python3 figma_mcp_client.py get-comments --file-key <KEY_OR_URL>
  python3 figma_mcp_client.py --test
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
from typing import Dict, Any, Optional, List, Tuple, Union

FIGMA_API_BASE = "https://api.figma.com/v1"
MCP_PROTOCOL_VERSION = "2024-11-05"


class FigmaAPIError(Exception):
    """Raised when the Figma REST API returns an error."""
    def __init__(self, status_code: int, message: str, body: Optional[Dict[str, Any]] = None):
        super().__init__(f"Figma API Error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body or {}


class FigmaRESTClient:
    """
    Zero-mock HTTP client for Figma REST API v1.
    Strictly forbids synthetic fallback responses under Monorepo Rule #0.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = (token or os.environ.get("FIGMA_ACCESS_TOKEN", "")).strip()

    def set_token(self, token: str) -> None:
        self.token = token.strip()

    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            raise FigmaAPIError(
                401,
                "FIGMA_ACCESS_TOKEN is missing or empty. Please set the environment variable "
                "or configure it using setup_figma_mcp.py."
            )
        headers = {
            "User-Agent": "Lauburu-Figma-MCP-Client/1.0",
            "Accept": "application/json"
        }
        if self.token.startswith("figd_"):
            headers["X-Figma-Token"] = self.token
        else:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout: float = 20.0
    ) -> Dict[str, Any]:
        """
        Executes an authentic GET request against the Figma REST API with rate-limiting backoff.
        """
        url = f"{FIGMA_API_BASE}/{endpoint.lstrip('/')}"
        if params:
            clean_params = {}
            for k, v in params.items():
                if v is not None:
                    if isinstance(v, list):
                        clean_params[k] = ",".join(str(item) for item in v)
                    else:
                        clean_params[k] = str(v)
            if clean_params:
                query_str = urllib.parse.urlencode(clean_params)
                url = f"{url}?{query_str}"

        headers = self._get_headers()
        req = urllib.request.Request(url, headers=headers, method="GET")

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw_data = resp.read().decode("utf-8")
                    return json.loads(raw_data)
            except urllib.error.HTTPError as e:
                # Rate limit (HTTP 429) backoff
                if e.code == 429 and attempt < max_retries - 1:
                    retry_header = e.headers.get("Retry-After")
                    try:
                        wait_seconds = float(retry_header) if retry_header else (2.0 ** attempt)
                    except ValueError:
                        wait_seconds = 2.0 ** attempt
                    time.sleep(wait_seconds)
                    continue

                body_text = e.read().decode("utf-8") if e.fp else ""
                try:
                    body_json = json.loads(body_text)
                except Exception:
                    body_json = {"raw": body_text}

                err_msg = body_json.get("message") or body_json.get("err") or e.reason
                raise FigmaAPIError(e.code, str(err_msg), body_json)
            except urllib.error.URLError as e:
                if attempt == max_retries - 1:
                    raise FigmaAPIError(500, f"Network transport error: {e.reason}")
                time.sleep(1.0)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise FigmaAPIError(500, f"Unexpected error communicating with Figma: {str(e)}")
                time.sleep(1.0)

        raise FigmaAPIError(500, "Exceeded maximum retry attempts for Figma request.")

    @staticmethod
    def parse_file_key(input_str: str) -> Tuple[str, Optional[str]]:
        """
        Parses a raw key or a Figma web URL into (file_key, optional_node_id).
        Supports formats:
          - 'abcXYZ123'
          - 'https://www.figma.com/design/abcXYZ123/ProjectName'
          - 'https://www.figma.com/file/abcXYZ123/ProjectName?node-id=1-23'
          - 'https://www.figma.com/proto/abcXYZ123/Name?node-id=1%3A23'
        """
        raw = input_str.strip()
        url_match = re.search(r"figma\.com/(?:file|design|proto)/([a-zA-Z0-9_-]+)", raw)
        if url_match:
            file_key = url_match.group(1)
            node_match = re.search(r"[?&]node-id=([a-zA-Z0-9%:-]+)", raw)
            node_id = None
            if node_match:
                decoded = urllib.parse.unquote(node_match.group(1))
                node_id = decoded.replace("-", ":")
            return file_key, node_id
        return raw, None

    def get_me(self) -> Dict[str, Any]:
        """Fetches the authenticated user profile."""
        return self.request("me")

    def get_file(
        self,
        file_key: str,
        depth: Optional[int] = 2,
        geometry: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches document structure and page hierarchy."""
        key, _ = self.parse_file_key(file_key)
        params: Dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if geometry:
            params["geometry"] = geometry
        return self.request(f"files/{key}", params)

    def get_file_nodes(
        self,
        file_key: str,
        ids: Union[List[str], str],
        depth: Optional[int] = None,
        geometry: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches detailed AST properties for specific node IDs."""
        key, _ = self.parse_file_key(file_key)
        if isinstance(ids, str):
            id_list = [i.strip() for i in ids.split(",") if i.strip()]
        else:
            id_list = list(ids)

        formatted_ids = [str(i).replace("-", ":") for i in id_list]
        params: Dict[str, Any] = {"ids": formatted_ids}
        if depth is not None:
            params["depth"] = depth
        if geometry:
            params["geometry"] = geometry
        return self.request(f"files/{key}/nodes", params)

    def get_image(
        self,
        file_key: str,
        ids: Union[List[str], str],
        format: str = "png",
        scale: float = 1.0
    ) -> Dict[str, Any]:
        """Fetches rendered image URLs for given node IDs."""
        key, _ = self.parse_file_key(file_key)
        if isinstance(ids, str):
            id_list = [i.strip() for i in ids.split(",") if i.strip()]
        else:
            id_list = list(ids)

        formatted_ids = [str(i).replace("-", ":") for i in id_list]
        params: Dict[str, Any] = {
            "ids": formatted_ids,
            "format": format.lower(),
            "scale": scale
        }
        return self.request(f"images/{key}", params)

    def get_comments(self, file_key: str) -> Dict[str, Any]:
        """Fetches all comments and review threads for the file."""
        key, _ = self.parse_file_key(file_key)
        return self.request(f"files/{key}/comments")


class FigmaMCPServer:
    """
    JSON-RPC 2.0 Stdio Model Context Protocol Server for Figma.
    """

    def __init__(self, client: Optional[FigmaRESTClient] = None):
        self.client = client or FigmaRESTClient()
        self.tools = [
            {
                "name": "get_file",
                "description": "Fetch high-level Figma file AST, page hierarchy, and components under Rule #0.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {
                            "type": "string",
                            "description": "Figma file key or full URL (e.g. https://www.figma.com/design/abcXYZ/...)"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Tree traversal depth limit (default: 2)",
                            "default": 2
                        },
                        "geometry": {
                            "type": "string",
                            "description": "Set to 'paths' to export vector geometry path data"
                        }
                    },
                    "required": ["file_key"]
                }
            },
            {
                "name": "get_file_nodes",
                "description": "Fetch detailed AST properties of specific nodes (AutoLayout, typography, geometry, fills).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {
                            "type": "string",
                            "description": "Figma file key or full URL"
                        },
                        "ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of node IDs to inspect (e.g. ['0:1', '1:23'])"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Subtree traversal depth for the specified nodes"
                        }
                    },
                    "required": ["file_key", "ids"]
                }
            },
            {
                "name": "get_image",
                "description": "Render specified Figma nodes into downloadable image URLs or SVG vector markup for visual parity auditing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {
                            "type": "string",
                            "description": "Figma file key or full URL"
                        },
                        "ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of node IDs to render"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["png", "svg", "pdf", "jpg"],
                            "description": "Output image format (default: png)",
                            "default": "png"
                        },
                        "scale": {
                            "type": "number",
                            "description": "Image rendering scale factor from 0.01 to 4.0 (default: 1.0)",
                            "default": 1.0
                        }
                    },
                    "required": ["file_key", "ids"]
                }
            },
            {
                "name": "get_comments",
                "description": "Retrieve designer comments, review threads, and annotations for a Figma file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {
                            "type": "string",
                            "description": "Figma file key or full URL"
                        }
                    },
                    "required": ["file_key"]
                }
            },
            {
                "name": "get_me",
                "description": "Retrieve authenticated user details and verify live API token connectivity under Rule #0.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Executes the requested tool by dispatching to FigmaRESTClient."""
        if name == "get_file":
            return self.client.get_file(
                file_key=args["file_key"],
                depth=args.get("depth", 2),
                geometry=args.get("geometry")
            )
        elif name == "get_file_nodes":
            ids = args.get("ids", [])
            if isinstance(ids, str):
                ids = [i.strip() for i in ids.split(",") if i.strip()]
            return self.client.get_file_nodes(
                file_key=args["file_key"],
                ids=ids,
                depth=args.get("depth")
            )
        elif name == "get_image":
            ids = args.get("ids", [])
            if isinstance(ids, str):
                ids = [i.strip() for i in ids.split(",") if i.strip()]
            return self.client.get_image(
                file_key=args["file_key"],
                ids=ids,
                format=args.get("format", "png"),
                scale=float(args.get("scale", 1.0))
            )
        elif name == "get_comments":
            return self.client.get_comments(file_key=args["file_key"])
        elif name == "get_me":
            return self.client.get_me()
        else:
            raise ValueError(f"Unknown tool name: '{name}'")

    def handle_jsonrpc(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single JSON-RPC 2.0 request frame."""
        if not isinstance(req, dict):
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Invalid Request: expected JSON object."}
            }

        method = req.get("method")
        msg_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "figma-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "notifications/initialized":
            # Handshake notification, no response required
            return None
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.tools
                }
            }
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Missing 'name' in tools/call parameters."}
                }

            try:
                result_payload = self.execute_tool(tool_name, tool_args)
                formatted_text = json.dumps(result_payload, indent=2, ensure_ascii=False)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": formatted_text
                            }
                        ],
                        "isError": False
                    }
                }
            except Exception as e:
                err_text = f"Error executing tool '{tool_name}': {str(e)}"
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": err_text
                            }
                        ],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found."}
            }

    def serve_stdio(self) -> None:
        """Runs the standard IO JSON-RPC 2.0 server loop."""
        # Use unbuffered line reading
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                try:
                    req_json = json.loads(line)
                except json.JSONDecodeError as e:
                    err_res = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                    }
                    sys.stdout.write(json.dumps(err_res) + "\n")
                    sys.stdout.flush()
                    continue

                response = self.handle_jsonrpc(req_json)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except KeyboardInterrupt:
                break
            except Exception as e:
                err_res = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal JSON-RPC error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(
        description="Figma MCP Protocol Client & REST Tool (Rule #0 Compliant)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--stdio", action="store_true", help="Run in JSON-RPC 2.0 stdio MCP server mode")
    parser.add_argument("--token", type=str, default=None, help="Explicit Figma access token")
    parser.add_argument("--test", action="store_true", help="Test token and fetch user profile")

    subparsers = parser.add_subparsers(dest="command", help="Diagnostic CLI commands")

    # ping / get-me
    subparsers.add_parser("ping", help="Ping Figma API /v1/me to verify auth")
    subparsers.add_parser("get-me", help="Retrieve authenticated user profile")

    # get-file
    p_file = subparsers.add_parser("get-file", help="Fetch document tree")
    p_file.add_argument("--file-key", type=str, required=True, help="Figma file key or URL")
    p_file.add_argument("--depth", type=int, default=2, help="Tree depth")
    p_file.add_argument("--geometry", type=str, default=None, help="Export geometry")

    # get-nodes
    p_nodes = subparsers.add_parser("get-nodes", help="Fetch specific AST nodes")
    p_nodes.add_argument("--file-key", type=str, required=True, help="Figma file key or URL")
    p_nodes.add_argument("--ids", type=str, required=True, help="Comma-separated node IDs")
    p_nodes.add_argument("--depth", type=int, default=None, help="Subtree depth")

    # get-image
    p_img = subparsers.add_parser("get-image", help="Render node images")
    p_img.add_argument("--file-key", type=str, required=True, help="Figma file key or URL")
    p_img.add_argument("--ids", type=str, required=True, help="Comma-separated node IDs")
    p_img.add_argument("--format", type=str, default="png", choices=["png", "svg", "pdf", "jpg"])
    p_img.add_argument("--scale", type=float, default=1.0)

    # get-comments
    p_com = subparsers.add_parser("get-comments", help="Fetch file comments")
    p_com.add_argument("--file-key", type=str, required=True, help="Figma file key or URL")

    args = parser.parse_args()

    client = FigmaRESTClient(token=args.token)
    server = FigmaMCPServer(client=client)

    if args.stdio:
        server.serve_stdio()
        sys.exit(0)

    if args.test or args.command in ("ping", "get-me"):
        try:
            res = client.get_me()
            print(json.dumps(res, indent=2, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.command == "get-file":
        try:
            res = client.get_file(args.file_key, depth=args.depth, geometry=args.geometry)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.command == "get-nodes":
        try:
            res = client.get_file_nodes(args.file_key, ids=args.ids, depth=args.depth)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.command == "get-image":
        try:
            res = client.get_image(args.file_key, ids=args.ids, format=args.format, scale=args.scale)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.command == "get-comments":
        try:
            res = client.get_comments(args.file_key)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # If no command given, show help
    parser.print_help()


if __name__ == "__main__":
    main()
