import sys

# 1. Update lens_mcp_server.py
mcp_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/mcp_server/lens_mcp_server.py"
with open(mcp_path, "r") as f:
    mcp_content = f.read()

if "lens_sync_split_screen_gemini" not in mcp_content:
    harvest_func = '''
def handle_sync_split_screen_gemini() -> dict:
    """Harvests research from the side-by-side Chrome/Gemini window and streams to LoRA lake."""
    from integrations.gemini_split_screen_harvester import GeminiSplitScreenHarvester
    harvester = GeminiSplitScreenHarvester()
    return harvester.process_and_sync()
'''
    mcp_content = mcp_content.replace('def handle_screen_summary() -> dict:', harvest_func + '\ndef handle_screen_summary() -> dict:')
    mcp_content = mcp_content.replace(
        '"lens_get_sanitized_screen_summary"',
        '"lens_get_sanitized_screen_summary",\n            "lens_sync_split_screen_gemini"'
    )
    with open(mcp_path, "w") as f:
        f.write(mcp_content)
    print("Updated lens_mcp_server.py with lens_sync_split_screen_gemini tool")

# 2. Update lens_omniscient_router.py
router_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_omniscient_router.py"
with open(router_path, "r") as f:
    router_content = f.read()

if "sync_split_screen" not in router_content:
    router_content = router_content.replace(
        '"query_graph_sql": "sqlite_tuned_executor"',
        '"query_graph_sql": "sqlite_tuned_executor",\n            "sync_split_screen": "gemini_split_screen_harvester"'
    )
    with open(router_path, "w") as f:
        f.write(router_content)
    print("Updated lens_omniscient_router.py with sync_split_screen route")
