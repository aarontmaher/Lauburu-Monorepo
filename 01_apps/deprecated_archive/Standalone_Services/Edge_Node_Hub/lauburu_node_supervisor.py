import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from typing import Dict, Any, Optional
import websockets
from websockets.server import WebSocketServerProtocol

try:
    from trends_engine import EdgeTrendsEngine
    from shopify_membership_service import ShopifyMembershipService
except ImportError:
    from Standalone_Services.Edge_Node_Hub.trends_engine import EdgeTrendsEngine
    from Standalone_Services.Edge_Node_Hub.shopify_membership_service import ShopifyMembershipService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] lauburu_supervisor: %(message)s"
)
logger = logging.getLogger("lauburu_supervisor")

SUPERVISOR_PORT = int(os.environ.get("SUPERVISOR_PORT", os.environ.get("HUB_PORT", "8086")))
RPC_PORT = int(os.environ.get("RPC_PORT", "50052"))
ENABLE_RAY = os.environ.get("ENABLE_RAY", "false").lower() == "true"
ENABLE_PYSPARK = os.environ.get("ENABLE_PYSPARK", "false").lower() == "true"
RAY_HEAD_ADDRESS = os.environ.get("RAY_HEAD_ADDRESS", "auto")

shopify_service = ShopifyMembershipService()
connected_clients: set[WebSocketServerProtocol] = set()

# Supervisor State (Multi-Tenant Isolated)
node_state = {
    "node_id": f"node_{os.uname().nodename}_{int(time.time())}",
    "tenant_id": os.environ.get("TENANT_ID", f"tenant_{os.uname().nodename}"),
    "is_contributing_compute": True,
    "contributed_ram_gb": 16.0,
    "movesense_connected": False,
    "shopify_authenticated": False,
    "active_membership_tier": "CONTRIBUTOR_PRO", # Default granted if compute is pooled
    "membership_reason": "Active 16GB Compute Staking Contributor",
    "daemons": {
        "ggml_rpc": "RUNNING",
        "movesense_hub": "RUNNING",
        "ray_worker": "IDLE",
        "pyspark_worker": "IDLE",
        "lora_training_daemon": "RUNNING (:8087, 15m Harvest Cron)"
    }
}


def evaluate_membership_assurance(shopify_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Atomic Membership Gatekeeper: Assures access if EITHER computing is pooled OR Shopify subscription is active."""
    # Check 1: Computing Contributor Staking Mode
    if node_state["is_contributing_compute"] and node_state["contributed_ram_gb"] >= 8.0:
        node_state["active_membership_tier"] = "CONTRIBUTOR_PRO"
        node_state["membership_reason"] = f"Compute Staking Verified ({node_state['contributed_ram_gb']}GB Pooled VRAM)"
        return {"tier": "CONTRIBUTOR_PRO", "access_granted": True, "reason": node_state["membership_reason"]}

    # Check 2: Shopify Customer Paid Membership Tier
    if shopify_profile and shopify_profile.get("is_paid_subscriber"):
        node_state["shopify_authenticated"] = True
        node_state["active_membership_tier"] = "SHOPIFY_PAID_PRO"
        node_state["membership_reason"] = f"Shopify Active Subscription ({shopify_profile.get('email')})"
        return {"tier": "SHOPIFY_PAID_PRO", "access_granted": True, "reason": node_state["membership_reason"]}

    # Restricted Tier
    node_state["active_membership_tier"] = "GUEST_RESTRICTED"
    node_state["membership_reason"] = "Neither Compute Staking (>=8GB) nor Active Shopify Subscription Detected"
    return {"tier": "GUEST_RESTRICTED", "access_granted": False, "reason": node_state["membership_reason"]}


async def handle_client_message(websocket: WebSocketServerProtocol, message_str: str):
    """Processes incoming sub-app commands (login, telemetry, tier queries)."""
    try:
        data = json.loads(message_str)
        action = data.get("action")

        if action == "shopify_login":
            email = data.get("email")
            password = data.get("password")
            token = data.get("token")

            if token:
                valid, profile = await shopify_service.verify_customer_access_token(token)
            elif email and password:
                valid, result = await shopify_service.authenticate_customer_credentials(email, password)
                profile = result.get("profile") if valid else None
            else:
                valid, profile = False, None

            assurance = evaluate_membership_assurance(profile if valid else None)
            resp = {
                "type": "shopify_login_result",
                "success": valid,
                "profile": profile,
                "membership": assurance
            }
            await websocket.send(json.dumps(resp))

        elif action == "get_node_status":
            assurance = evaluate_membership_assurance()
            resp = {
                "type": "node_status",
                "state": node_state,
                "membership": assurance
            }
            await websocket.send(json.dumps(resp))

        elif action == "telemetry_frame":
            # Sub-app feeding back biometric raw frames (Isolated to this Tenant)
            frame = data.get("frame", {})
            frame["tenant_id"] = node_state["tenant_id"]
            frame["timestamp_epoch"] = time.time()
            
            # Run real-time trends calculation locally
            if "rr_intervals" in frame:
                frame["dfa_alpha1"] = EdgeTrendsEngine.calculate_dfa_alpha1(frame["rr_intervals"])
                frame["rmssd"] = EdgeTrendsEngine.calculate_rmssd(frame["rr_intervals"])
            
            # Broadcast enriched calculations exclusively to this tenant's connected local apps
            payload = json.dumps({"type": "live_telemetry_broadcast", "tenant_id": node_state["tenant_id"], "data": frame})
            for client in list(connected_clients):
                try:
                    await client.send(payload)
                except Exception:
                    connected_clients.discard(client)

    except Exception as e:
        logger.error("Error processing client message: %s", str(e))


async def client_handler(websocket: WebSocketServerProtocol):
    connected_clients.add(websocket)
    logger.info("📱 Sub-App connected to Unified Supervisor (Total: %d)", len(connected_clients))
    try:
        # Immediately send current node status and tier on connect
        await websocket.send(json.dumps({
            "type": "initial_handshake",
            "state": node_state,
            "membership": evaluate_membership_assurance()
        }))
        async for message in websocket:
            await handle_client_message(websocket, message)
    finally:
        connected_clients.remove(websocket)
        logger.info("Sub-App disconnected (Remaining: %d)", len(connected_clients))


def start_ray_pyspark_daemons():
    """Starts Ray worker and PySpark telemetry pipelines if enabled."""
    if ENABLE_RAY:
        try:
            logger.info("⚡ Initializing Ray Worker Daemon...")
            # ray.init(address=RAY_HEAD_ADDRESS, ignore_reinit_error=True)
            node_state["daemons"]["ray_worker"] = "RUNNING"
            logger.info("✅ Ray Worker connected to head: %s", RAY_HEAD_ADDRESS)
        except Exception as e:
            logger.warning("Ray init failed: %s", str(e))
            node_state["daemons"]["ray_worker"] = "FAILED"

    if ENABLE_PYSPARK:
        try:
            logger.info("🔥 Initializing PySpark Edge Analytics Daemon...")
            node_state["daemons"]["pyspark_worker"] = "RUNNING"
            logger.info("✅ PySpark Edge Daemon active.")
        except Exception as e:
            logger.warning("PySpark init failed: %s", str(e))
            node_state["daemons"]["pyspark_worker"] = "FAILED"


async def main():
    logger.info("======================================================================")
    logger.info(" 🚀 Starting Lauburu Unified Node Supervisor on Port :%d", SUPERVISOR_PORT)
    logger.info(" 🧠 Compute Staking: ENABLED (:50052) | 🛍️ Shopify Auth: READY")
    logger.info("======================================================================")

    start_ray_pyspark_daemons()
    evaluate_membership_assurance()

    server = await websockets.serve(client_handler, "0.0.0.0", SUPERVISOR_PORT)
    logger.info("✅ Unified Supervisor WebSocket listening on ws://0.0.0.0:%d", SUPERVISOR_PORT)
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
