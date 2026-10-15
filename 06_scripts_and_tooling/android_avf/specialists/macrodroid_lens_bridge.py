import sys
import httpx
import asyncio

MACRODROID_WEBHOOK_URL = "http://127.0.0.1:8085"

async def trigger_macrodroid_automation(automation_name: str, payload: dict = None):
    """Triggers a MacroDroid automation via local webhook."""
    print(f"Triggering MacroDroid automation: {automation_name}")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.post(MACRODROID_WEBHOOK_URL, json={"automation": automation_name, "payload": payload or {}})
            return res.status_code == 200
    except Exception as e:
        print(f"Failed to trigger MacroDroid: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(trigger_macrodroid_automation(sys.argv[1]))
    else:
        print("Usage: python3 macrodroid_lens_bridge.py <automation_name>")
# Finished.
