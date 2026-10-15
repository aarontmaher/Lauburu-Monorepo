import os
import httpx
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# The internal Tailscale IP or MagicDNS of the Mac Mini
# We will pass this in via Cloud Run Environment Variables
MAC_MINI_TAILSCALE_IP = os.environ.get("MAC_MINI_TAILSCALE_IP", "100.119.199.76")
MAC_MINI_PORT = os.environ.get("MAC_MINI_PORT", "4000")

@app.post("/shopify/webhook")
async def shopify_webhook_proxy(request: Request):
    """Catches Shopify webhooks and routes them securely over Tailscale to the Mac Mini."""
    payload = await request.body()
    headers = dict(request.headers)
    
    # Optional: Strip out host headers so we don't confuse the local receiver
    headers.pop("host", None)
    
    local_target = f"http://{MAC_MINI_TAILSCALE_IP}:{MAC_MINI_PORT}/api/webhooks/shopify"
    
    print(f"📦 Received Webhook. Routing to Tailscale Edge: {local_target}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                local_target, 
                content=payload, 
                headers=headers,
                timeout=10.0
            )
        return {"status": "forwarded", "local_response": response.status_code}
    except Exception as e:
        print(f"❌ Failed to reach Mac Mini over Tailscale: {e}")
        raise HTTPException(status_code=502, detail="Mesh Edge Node Offline or Unreachable")

@app.get("/")
def health_check():
    return {"status": "Cloud Run Tailscale Proxy Active"}
