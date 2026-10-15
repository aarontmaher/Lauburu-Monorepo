import sys
import json
import time
import asyncio

sys.path.append("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/mcp")
import screen_lens_mcp_server

async def find_and_click(target_text, retries=3):
    for attempt in range(retries):
        # 1. Inspect screen
        res = screen_lens_mcp_server.handle_tool_call("screen_lens_inspect_screen", {"target": "chrome"})
        if asyncio.iscoroutine(res):
            res = await res
        
        # 2. Find bounding box for target_text
        # Assuming res contains a list of UI elements with text and coordinates
        elements = res.get("ui_elements", [])
        for el in elements:
            if target_text.lower() in el.get("text", "").lower():
                print(f"👁️ Lens found '{target_text}' at {el['x']}, {el['y']}")
                # 3. Actuate physical click
                action_res = screen_lens_mcp_server.handle_tool_call("screen_lens_actuate_action", {
                    "device_id": "mac_host",
                    "action": "click",
                    "x": el['x'],
                    "y": el['y']
                })
                if asyncio.iscoroutine(action_res):
                    await action_res
                time.sleep(2) # Wait for page render
                return True
        
        print(f"⚠️ Lens could not find '{target_text}', retrying ({attempt+1}/{retries})...")
        time.sleep(1)
    
    return False

async def extract_token():
    # Once on the token page, grab the screen text to find the shpat_ token
    res = screen_lens_mcp_server.handle_tool_call("screen_lens_inspect_screen", {"target": "chrome"})
    if asyncio.iscoroutine(res):
        res = await res
        
    elements = res.get("ui_elements", [])
    for el in elements:
        text = el.get("text", "")
        if "shpat_" in text:
            return text.strip()
    return None

async def run_automation():
    print("🚀 Starting Screen Lens Shopify Admin Token Retrieval Protocol...")
    
    steps = [
        "Settings",
        "Apps",
        "Develop apps",
        "Lauburu AI Core",
        "API credentials",
        "Reveal token once"
    ]
    
    for step in steps:
        success = await find_and_click(step)
        if not success:
            print(f"❌ Automation failed at step: {step}")
            return
            
    # Extract the revealed token
    token = await extract_token()
    if token:
        print(f"✅ Lens successfully extracted token: {token}")
        with open("/Volumes/Lauburu-Monorepo/01_apps/commerce_and_business/lauburu-storefront/.env", "a") as f:
            f.write(f"\nSHOPIFY_ADMIN_TOKEN={token}\n")
        print("💾 Token saved to .env")
    else:
        print("❌ Lens could not find the shpat_ token on the screen.")

if __name__ == "__main__":
    asyncio.run(run_automation())
