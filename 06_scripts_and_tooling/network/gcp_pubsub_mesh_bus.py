#!/usr/bin/env python3
"""
================================================================================
Lauburu Sovereign Mesh: Cloud Pub/Sub Always Free Event Bus
================================================================================
Subsystem: 06_scripts_and_tooling/network/gcp_pubsub_mesh_bus.py
Governed by:
- Rule #0 (Zero-Mock Empirical Truth Verification)
- Rule #1 & Rule #5 (Victory-Triggered Tri-Proof Interceptor Gate)
- Rule #2 (Tri-Vault Storage Synchronization)
- Rule #3 (Host Sanctuary & Dynamic RAM Governance Invariant)
- Rule #9 (Zero-Waste Background Daemon & Cron Governance)

Role:
1. Manages Always Free Cloud Pub/Sub messaging bus (10 GB/month Always Free).
2. Topic: lauburu-mesh-events; Subscription: lauburu-mesh-sub.
3. Broadcasts real telemetry events, node state shifts, and AI consensus triggers.
4. Enforces Zero-Spend Circuit Breaker checks before publishing.
================================================================================
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"))

try:
    from gcp_free_tier_circuit_breaker import GCPFreeTierCircuitBreaker
except ImportError:
    GCPFreeTierCircuitBreaker = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PubSubMeshBus] %(message)s"
)
logger = logging.getLogger("PubSubMeshBus")

DEFAULT_PROJECT_ID = "lauburu-play-deploy"
DEFAULT_TOPIC = "lauburu-mesh-events"
DEFAULT_SUBSCRIPTION = "lauburu-mesh-sub"


class GCPPubSubMeshBus:
    """Manages Always Free Cloud Pub/Sub messaging bus for distributed mesh events."""

    def __init__(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        topic: str = DEFAULT_TOPIC,
        subscription: str = DEFAULT_SUBSCRIPTION,
        circuit_breaker: Optional[Any] = None,
    ):
        self.project_id = project_id
        self.topic = topic
        self.subscription = subscription
        self.circuit_breaker = circuit_breaker or (
            GCPFreeTierCircuitBreaker() if GCPFreeTierCircuitBreaker else None
        )

    def publish_event(self, event_type: str, payload: Dict[str, Any], origin_node: str = "Mac_Node") -> Tuple[bool, str]:
        """Publishes an event packet to the Always Free Pub/Sub topic."""
        packet = {
            "event_type": event_type,
            "origin_node": origin_node,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "payload": payload,
        }
        message_json = json.dumps(packet)
        message_bytes = len(message_json.encode("utf-8"))

        # 1. Circuit Breaker validation
        if self.circuit_breaker:
            can_publish, reason = self.circuit_breaker.can_publish_pubsub(message_bytes)
            if not can_publish:
                return False, f"Circuit breaker blocked Pub/Sub publish: {reason}"

        # 2. Publish via gcloud pubsub topics publish
        cmd = [
            "gcloud", "pubsub", "topics", "publish",
            self.topic,
            f"--message={message_json}",
            f"--project={self.project_id}",
            "--attribute", f"event_type={event_type},origin={origin_node}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            if self.circuit_breaker:
                self.circuit_breaker.record_pubsub_publish(message_bytes)
            msg_id = proc.stdout.strip().replace("messageIds:\n- ", "")
            logger.info(f"Published Pub/Sub event '{event_type}' ({message_bytes} B) [ID: {msg_id}]")
            return True, msg_id
        else:
            logger.error(f"Failed to publish Pub/Sub event: {proc.stderr}")
            return False, proc.stderr

    def pull_messages(self, max_messages: int = 5, auto_ack: bool = True) -> List[Dict[str, Any]]:
        """Pulls messages from the Always Free Pub/Sub subscription."""
        cmd = [
            "gcloud", "pubsub", "subscriptions", "pull",
            self.subscription,
            f"--limit={max_messages}",
            f"--project={self.project_id}",
            "--format=json",
        ]
        if auto_ack:
            cmd.append("--auto-ack")

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error(f"Error pulling from subscription {self.subscription}: {proc.stderr}")
            return []

        try:
            raw_entries = json.loads(proc.stdout) if proc.stdout.strip() else []
            parsed_messages = []
            for entry in raw_entries:
                msg_data = entry.get("message", {}).get("data", "")
                import base64
                try:
                    decoded = base64.b64decode(msg_data).decode("utf-8")
                    parsed = json.loads(decoded)
                    parsed_messages.append(parsed)
                except Exception:
                    pass
            return parsed_messages
        except json.JSONDecodeError as e:
            logger.error(f"Failed parsing pull response: {e}")
            return []


def main() -> None:
    bus = GCPPubSubMeshBus()
    print("================================================================================")
    print("🛰️  TESTING CLOUD PUB/SUB ALWAYS FREE EVENT BUS")
    print("================================================================================")
    sample_payload = {
        "node": "Pixel_10_Pro_XL",
        "battery_pct": 89,
        "thermal_state": "NOMINAL",
        "mesh_role": "Vision_Edge_TPU",
    }
    pub_ok, msg_id = bus.publish_event("NODE_HEARTBEAT", sample_payload, origin_node="Pixel_10_Pro_XL")
    print(f"Publish Event: {'✅ SUCCESS' if pub_ok else '❌ FAILED'} (Message ID: {msg_id})")

    # Pull message back
    messages = bus.pull_messages(max_messages=5, auto_ack=True)
    print(f"Pull Events: {'✅ SUCCESS' if len(messages) > 0 else '⚠️ EMPTY'} ({len(messages)} received)")
    for m in messages:
        print(f"  - Event: {m.get('event_type')} from {m.get('origin_node')}")


if __name__ == "__main__":
    main()
