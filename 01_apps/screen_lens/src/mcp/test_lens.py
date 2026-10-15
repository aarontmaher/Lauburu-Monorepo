import sys
import asyncio
sys.path.append("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/mcp")
import screen_lens_mcp_server

async def main():
    try:
        # Check if function is async or sync
        if asyncio.iscoroutinefunction(screen_lens_mcp_server.screen_lens_mesh_telemetry):
            telemetry = await screen_lens_mcp_server.screen_lens_mesh_telemetry()
        else:
            telemetry = screen_lens_mcp_server.screen_lens_mesh_telemetry()
        print(telemetry)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
