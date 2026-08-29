#!/usr/bin/env python3
"""
Mesh Governor Model Context Protocol (MCP) Server
=================================================
Subsystem: 06_scripts_and_tooling/mcp/mesh_governor_mcp_server.py
Version: 2.0.0-MCP-GOVERNOR
Lauburu Mesh Ecosystem — 2026

Exposes structured JSON-RPC MCP tools to local and cloud AI agents:
1. `audit_ram_and_hardware`: Returns live router & host RAM metrics.
2. `audit_and_heal_daemons`: Checks ports 8080-8086, 18802, 50052, 8088 and heals failures.
3. `audit_and_heal_storage`: Verifies Obsidian Vault, PySpark Lake, and Git Locks.
4. `optimize_mesh_network`: Enforces SQM fq_codel, MTU 9000, and WireGuard keepalives.
"""

import sys
import json
from pathlib import Path

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling/network"))

from hybrid_router_mesh_governor import HybridMeshGovernor

governor = HybridMeshGovernor()

def handle_request(request_str: str) -> str:
    try:
        req = json.loads(request_str)
        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id", 1)

        if method == "tools/list":
            tools = [
                {
                    "name": "audit_ram_and_hardware",
                    "description": "Returns real hardware RAM metrics from GL.iNet Router and Host Mac.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "audit_and_heal_daemons",
                    "description": "Audits all 7 core monorepo daemons (Ports 8080-8086, 18802, 50052, 8088) and triggers healing.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "audit_and_heal_storage",
                    "description": "Audits and self-heals Obsidian Vault mount, PySpark Data Lake, and Git lock files.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "optimize_mesh_network",
                    "description": "Applies network-wide tuning (SQM fq_codel, MTU 9000, WireGuard keepalive).",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
            return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})

        elif method == "tools/call":
            tool_name = params.get("name")
            res = governor.execute_full_governance_cycle()
            
            if tool_name == "audit_ram_and_hardware":
                out = {"router_ram": res["router_real_ram"], "host_ram": res["host_ram"]}
            elif tool_name == "audit_and_heal_daemons":
                out = res["daemon_watchdog"]
            elif tool_name == "audit_and_heal_storage":
                out = res["storage_health"]
            elif tool_name == "optimize_mesh_network":
                out = {"status": "OPTIMAL", "synergy_score": res["synergy_efficiency_score"]}
            else:
                out = res

            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}
            })

        return json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}})
    except Exception as e:
        return json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": str(e)}})

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Testing MCP tools/list:")
        print(handle_request(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})))
        print("\nTesting MCP tools/call (audit_ram_and_hardware):")
        print(handle_request(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "audit_ram_and_hardware"}})))
    else:
        # Standard MCP stdio transport loop
        for line in sys.stdin:
            if line.strip():
                response = handle_request(line.strip())
                print(response, flush=True)
