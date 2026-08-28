"""
business_client.py — Transmission Client to Business Orchestrator & Cloudflare Edge.

Governs Feature F13 (Business Swarm Transmission Interface):
1. Multi-Tier Ingress Endpoint Routing:
   - Primary LAN / Self-Healing Hub (Host: 100.101.39.98:18802 / POST /api/v1/marketplace/publish)
   - Cloudflare Worker Edge Ingress (api.lauburu.mesh / POST /mcp/marketplace/inbound)
   - Headless Shopify Storefront Gateway (Port 4000 / POST /api/storefront/listing)
2. Custom Protocol Handshake & Headers:
   - `Content-Type: application/json`
   - `X-Lauburu-Signature: sha256={hmac}`
   - `X-Lauburu-Node-ID: GL_INET_ROUTER_GW`
   - `X-Lauburu-Consensus-Proof: {merkle_root}`
3. Volatile tmpfs Outbox Staging:
   - Outbox directory `/tmp/business_queue/` for zero-flash-wear persistence until ACK.
4. Fault Tolerance & Retries:
   - Connection failure recovery with exponential backoff (`base * 2^i`).
   - Automatic failover across multi-tier ingress endpoints.
   - HTTP 429 rate-limit backoff respect.

Authoritative Reference: ORIGINAL_REQUEST.md § R7 & PROJECT.md Feature F13.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .asset_packager import AssetPackager, validate_asset_payload

logger = logging.getLogger("smolagi.monetization.business_client")


# ---------------------------------------------------------------------------
# Ingress Endpoints Configuration
# ---------------------------------------------------------------------------

DEFAULT_ENDPOINTS: Dict[str, str] = {
    "primary_lan": os.getenv(
        "BUSINESS_HUB_PRIMARY_URL",
        "http://100.101.39.98:18802/api/v1/marketplace/publish",
    ),
    "cloudflare_edge": os.getenv(
        "BUSINESS_CLOUDFLARE_EDGE_URL",
        "https://api.lauburu.mesh/mcp/v2/admin/marketplace/inbound",
    ),
    "storefront_gateway": os.getenv(
        "BUSINESS_STOREFRONT_GATEWAY_URL",
        "http://127.0.0.1:4000/api/storefront/listing",
    ),
}

NODE_IDENTIFIER = os.getenv("LAUBURU_NODE_ID", "GL_INET_ROUTER_GW")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class TransmissionReceipt:
    status: str  # "PUBLISHED", "RETRY_QUEUED", "FAILED", "QUEUED"
    listing_id: Optional[str]
    asset_id: str
    http_code: int
    endpoint_used: str
    timestamp: float = field(default_factory=time.time)
    raw_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == "PUBLISHED" and self.http_code == 200

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "listing_id": self.listing_id,
            "asset_id": self.asset_id,
            "http_code": self.http_code,
            "endpoint_used": self.endpoint_used,
            "timestamp": self.timestamp,
            "raw_response": self.raw_response,
            "error_message": self.error_message,
        }


# ---------------------------------------------------------------------------
# Business Transmission Client
# ---------------------------------------------------------------------------

class BusinessClient:
    """
    HTTP client for transmitting packaged assets from the router daemon
    to the Business AI Swarm / Self-Healing Hub / Cloudflare edge endpoints.
    """

    def __init__(
        self,
        endpoints: Optional[Dict[str, str]] = None,
        node_id: str = NODE_IDENTIFIER,
        outbox_dir: Optional[Union[str, Path]] = None,
        packager: Optional[AssetPackager] = None,
        transport_hook: Optional[Callable[[urllib.request.Request, float], Tuple[int, Dict[str, Any], Dict[str, str]]]] = None,
    ):
        self.endpoints = dict(endpoints) if endpoints else dict(DEFAULT_ENDPOINTS)
        self.node_id = node_id
        self.outbox_dir = Path(outbox_dir) if outbox_dir else Path("/tmp/business_queue")
        self.packager = packager or AssetPackager()
        self.transport_hook = transport_hook  # For testing without network sockets

    def stage_payload(self, payload: Dict[str, Any]) -> Path:
        """Stages an asset payload in the volatile tmpfs outbox directory."""
        validate_asset_payload(payload, raise_exception=True)
        return self.packager.save_to_outbox(payload, outbox_dir=self.outbox_dir)

    def list_outbox(self) -> List[Path]:
        """Lists pending payloads in the tmpfs outbox queue."""
        if not self.outbox_dir.exists():
            return []
        return sorted(self.outbox_dir.glob("*.json"))

    def build_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Constructs canonical security, routing, and consensus headers."""
        sig_hex = payload.get("consensus_signature", {}).get("hmac_sha256", "")
        merkle_root = payload.get("provenance", {}).get("merkle_state_root", "")

        return {
            "Content-Type": "application/json",
            "X-Lauburu-Signature": f"sha256={sig_hex}",
            "X-Lauburu-Node-ID": self.node_id,
            "X-Lauburu-Consensus-Proof": merkle_root,
            "User-Agent": "SmolAGI-Router-Monetization/1.0",
        }

    def _execute_http_request(
        self,
        url: str,
        data_bytes: bytes,
        headers: Dict[str, str],
        timeout_s: float = 5.0,
    ) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        """Executes HTTP POST request or invokes transport hook."""
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        if self.transport_hook is not None:
            return self.transport_hook(req, timeout_s)

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                status_code = resp.getcode()
                raw_body = resp.read()
                resp_headers = dict(resp.headers)
                try:
                    body_json = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    body_json = {"raw": raw_body.decode("utf-8", errors="replace")}
                return status_code, body_json, resp_headers
        except urllib.error.HTTPError as he:
            raw_err = he.read() if hasattr(he, "read") else b""
            try:
                err_json = json.loads(raw_err.decode("utf-8"))
            except Exception:
                err_json = {"error": str(he), "raw": raw_err.decode("utf-8", errors="replace")}
            return he.code, err_json, dict(he.headers if hasattr(he, "headers") else {})
        except Exception as e:
            raise ConnectionError(f"Network error connecting to {url}: {e}") from e

    def publish_asset(
        self,
        payload: Dict[str, Any],
        endpoint_tier: str = "primary_lan",
        max_retries: int = 3,
        base_backoff_s: float = 0.5,
        timeout_s: float = 5.0,
        enable_failover: bool = True,
    ) -> TransmissionReceipt:
        """
        Publishes a packaged asset to the specified endpoint tier with
        exponential backoff retry and automatic cross-tier failover.
        """
        validate_asset_payload(payload, raise_exception=True)

        # Stage payload in outbox
        staged_file = self.stage_payload(payload)

        headers = self.build_headers(payload)
        data_bytes = json.dumps(payload).encode("utf-8")
        asset_id = payload["asset_id"]

        # Order endpoints: requested tier first, then remaining tiers
        candidate_tiers = [endpoint_tier]
        if enable_failover:
            for t in ["primary_lan", "cloudflare_edge", "storefront_gateway"]:
                if t not in candidate_tiers and t in self.endpoints:
                    candidate_tiers.append(t)

        last_error = ""
        last_status_code = 0

        for tier in candidate_tiers:
            url = self.endpoints.get(tier)
            if not url:
                continue

            for attempt in range(max_retries):
                try:
                    status_code, resp_body, resp_headers = self._execute_http_request(
                        url=url,
                        data_bytes=data_bytes,
                        headers=headers,
                        timeout_s=timeout_s,
                    )
                    last_status_code = status_code

                    # 200 OK / 201 Created
                    if status_code in (200, 201):
                        listing_id = resp_body.get("listing_id") or resp_body.get("marketplace_id") or f"mkt_{asset_id.split(':')[-1]}"
                        receipt = TransmissionReceipt(
                            status="PUBLISHED",
                            listing_id=listing_id,
                            asset_id=asset_id,
                            http_code=status_code,
                            endpoint_used=url,
                            raw_response=resp_body,
                        )
                        # Remove from outbox upon successful publication
                        staged_file.unlink(missing_ok=True)
                        return receipt

                    # 429 Too Many Requests: inspect Retry-After
                    if status_code == 429:
                        retry_after = 1.0
                        if "Retry-After" in resp_headers:
                            try:
                                retry_after = float(resp_headers["Retry-After"])
                            except ValueError:
                                pass
                        time.sleep(retry_after)
                        continue

                    # 4xx Client Error: do not retry same endpoint if non-recoverable
                    if 400 <= status_code < 500:
                        last_error = f"HTTP {status_code} Client Error from {url}: {resp_body}"
                        break

                    # 5xx Server Error: retry with backoff
                    last_error = f"HTTP {status_code} Server Error from {url}: {resp_body}"

                except ConnectionError as ce:
                    last_error = str(ce)
                except Exception as ex:
                    last_error = f"Unexpected error during transmission: {ex}"

                # Calculate exponential backoff: base * 2^attempt
                backoff_time = base_backoff_s * (2 ** attempt)
                time.sleep(backoff_time)

        # If all tiers and retries fail, retain in volatile outbox
        return TransmissionReceipt(
            status="RETRY_QUEUED",
            listing_id=None,
            asset_id=asset_id,
            http_code=last_status_code or 503,
            endpoint_used=self.endpoints.get(endpoint_tier, "unknown"),
            error_message=last_error or "All transmission tiers exhausted",
        )

    def dispatch_pending_outbox(
        self,
        endpoint_tier: str = "primary_lan",
        max_items: int = 10,
    ) -> List[TransmissionReceipt]:
        """Dispatches any pending staged payloads currently queued in the outbox."""
        pending_files = self.list_outbox()[:max_items]
        receipts: List[TransmissionReceipt] = []

        for pf in pending_files:
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                receipt = self.publish_asset(payload, endpoint_tier=endpoint_tier)
                receipts.append(receipt)
            except Exception as e:
                logger.error(f"Failed to process outbox file {pf}: {e}")

        return receipts
