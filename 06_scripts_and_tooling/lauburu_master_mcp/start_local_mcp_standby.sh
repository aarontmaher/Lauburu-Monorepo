#!/bin/bash
# Local Active-Standby Production MCP Server on Mac Mini Host (Port 9999)
pkill -f "lauburu_master_mcp/production_mesh_mcp_server.py" 2>/dev/null || true
PORT=9999 python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/lauburu_master_mcp/production_mesh_mcp_server.py > /tmp/lauburu_local_mcp.log 2>&1 &
echo $! > /tmp/lauburu_local_mcp.pid
echo "Local Standby MCP Server started with PID $(cat /tmp/lauburu_local_mcp.pid)"
