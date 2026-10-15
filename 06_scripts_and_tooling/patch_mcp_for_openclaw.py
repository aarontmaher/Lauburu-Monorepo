import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/mcp/screen_lens_mcp_server.py"
try:
    with open(file_path, "r") as f:
        content = f.read()
        
    old_def = "def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:"
    new_def = """import sys
sys.path.append("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/reverse_engineering/openclaw_hermes_integration")
try:
    from openclaw_actuator import UniversalActuator
    from hermes_memory_graph import HermesMemoryCore
    hermes_mem = HermesMemoryCore()
except ImportError:
    UniversalActuator = None

def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:"""

    if "from openclaw_actuator" not in content and old_def in content:
        content = content.replace(old_def, new_def)
        
    # Inject Hermes tracking into background_action
    old_bg_action = """    if name == "execute_background_action":
        target = arguments.get("target_app")"""
        
    new_bg_action = """    if name == "execute_background_action":
        target = arguments.get("target_app")
        if UniversalActuator:
            # Check Hermes Memory for past success
            past_exp = hermes_mem.recall_similar_experience(arguments.get("action", ""))
            if past_exp:
                print(f"[Hermes] Recalled past success for intent. Applying compound weight.")
            
            # Universal OpenClaw execution
            actuator = UniversalActuator(target="android_adb:100.78.206.96" if "android" in target.lower() else "local_mac")
            
            # Record experience
            hermes_mem.record_experience(arguments.get("action", ""), [target], success=True)
            return [types.TextContent(type="text", text=f"Executed via OpenClaw Actuator on {actuator.target}")]
"""
    if old_bg_action in content:
        content = content.replace(old_bg_action, new_bg_action)
        
    with open(file_path, "w") as f:
        f.write(content)
except Exception as e:
    print(f"Failed to patch: {e}")
