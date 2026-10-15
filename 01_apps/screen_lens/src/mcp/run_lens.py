import sys
import json
sys.path.append("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/mcp")
import screen_lens_mcp_server
import asyncio

async def run_tool():
    res = screen_lens_mcp_server.handle_tool_call("screen_lens_inspect_screen", {"target": "chrome"})
    if asyncio.iscoroutine(res):
        res = await res
    print(json.dumps(res, indent=2))

asyncio.run(run_tool())
