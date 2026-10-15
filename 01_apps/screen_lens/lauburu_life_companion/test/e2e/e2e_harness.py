"""
E2E Test Harness & Shared Contracts for Lauburu Life Companion
Opaque-Box Requirement-Driven Testing Engine
"""

import os
import sys
import json
import time
import socket
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Project root resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MACOS_PLIST_PATH = PROJECT_ROOT / "macos" / "com.lauburu.lifecompanion.plist"
USER_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.lauburu.lifecompanion.plist"
FALLBACK_USER_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.lauburu.screenlifecompanion.plist"

ANDROID_MANIFEST_PATH = PROJECT_ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
ANDROID_RECEIVER_PATH = PROJECT_ROOT / "android" / "app" / "src" / "main" / "kotlin" / "com" / "example" / "lauburu_life_companion" / "BootReceiver.kt"

# External & Local Services
SHOP_DOMAIN = "lauburu-grappling.myshopify.com"
STOREFRONT_TOKEN = "a39ead89f7318e991105e64873b4e10e"
SHOPIFY_GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/api/2024-04/graphql.json"

PORT_8082_URL = "http://127.0.0.1:8082"
PORT_8083_URL = "http://127.0.0.1:8083"
DAEMON_PORT = 3036
ZMQ_PORT = 5555

PROBE_TIMEOUT = 1.5
INFERENCE_TIMEOUT = 15.0

# 18-Item Canonical Commercial Catalog
CANONICAL_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "canon_01",
        "title": "Lauburu Pro Compression Rashguard",
        "category": "Apparel",
        "price_aud": 97.50,
        "stock": 42,
        "sku": "LAU-RSH-PRO-BLK",
        "description": "Reinforced flatlock stitching, antimicrobial 4-way stretch fabric for elite tatami grappling."
    },
    {
        "id": "canon_02",
        "title": "Lauburu No-Gi Fight Shorts",
        "category": "Apparel",
        "price_aud": 90.00,
        "stock": 35,
        "sku": "LAU-SHT-NOGI-01",
        "description": "Ultra-light ripstop fabric with side slits and silicone waistband grip for submission grappling."
    },
    {
        "id": "canon_03",
        "title": "Lauburu Competition BJJ Gi 450 GSM",
        "category": "Apparel",
        "price_aud": 189.00,
        "stock": 18,
        "sku": "LAU-GI-COMP-450",
        "description": "Pearl weave jacket with 10oz twill cotton pants, IBJJF approved competition cut."
    },
    {
        "id": "canon_04",
        "title": "Lauburu Compression Spats",
        "category": "Apparel",
        "price_aud": 79.00,
        "stock": 50,
        "sku": "LAU-SPT-PRO-01",
        "description": "Sublimated graphics with ergonomic paneling to prevent mat burn and preserve joint warmth."
    },
    {
        "id": "canon_05",
        "title": "Lauburu Premium BJJ Rank Belt",
        "category": "Accessories",
        "price_aud": 45.00,
        "stock": 60,
        "sku": "LAU-BLT-RNK-01",
        "description": "100% heavy cotton weave with competition rank sleeve and embroidered branding."
    },
    {
        "id": "canon_06",
        "title": "Lauburu Tactical Combat Duffel 65L",
        "category": "Bags",
        "price_aud": 108.00,
        "stock": 25,
        "sku": "LAU-BAG-TAC-65L",
        "description": "Water-resistant 1000D Cordura with ventilated wet-gi compartment and laptop sleeve."
    },
    {
        "id": "canon_07",
        "title": "Lauburu Streetwear Oversized Mesh Hoodie",
        "category": "Apparel",
        "price_aud": 127.50,
        "stock": 30,
        "sku": "LAU-HOD-STR-01",
        "description": "Heavyweight 480 GSM French terry cotton with subtle high-density silicone chest crest."
    },
    {
        "id": "canon_08",
        "title": "Lauburu Core Heavyweight Tee",
        "category": "Apparel",
        "price_aud": 55.00,
        "stock": 80,
        "sku": "LAU-TEE-COR-WHT",
        "description": "260 GSM combed cotton tee designed for streetwear drape and gym durability."
    },
    {
        "id": "canon_09",
        "title": "Lauburu Low-Profile Structured Snapback",
        "category": "Accessories",
        "price_aud": 42.00,
        "stock": 45,
        "sku": "LAU-HAT-SNP-BLK",
        "description": "Wool-blend structured crown with moisture-wicking sweatband and matte black eyelets."
    },
    {
        "id": "canon_10",
        "title": "Movesense MD+ Medical ECG Sensor",
        "category": "Biometrics",
        "price_aud": 170.00,
        "stock": 14,
        "sku": "LAU-BIO-MOV-MD",
        "description": "512Hz raw ECG and 9-axis IMU medical sensor with Bluetooth BLE GATT data streaming."
    },
    {
        "id": "canon_11",
        "title": "Movesense Pro Dual-Snap Chest Strap",
        "category": "Biometrics",
        "price_aud": 39.00,
        "stock": 40,
        "sku": "LAU-BIO-STP-PRO",
        "description": "Washable conductive textile electrodes calibrated for low-artifact dynamic grappling capture."
    },
    {
        "id": "canon_12",
        "title": "Apple iPhone 16 Pro 512GB (Grade A Refurb)",
        "category": "Hardware",
        "price_aud": 1150.00,
        "stock": 5,
        "sku": "LAU-HW-IPH-16P",
        "description": "Unlocked Grade A certified device with titanium chassis, 48MP camera, and 100% battery health."
    },
    {
        "id": "canon_13",
        "title": "Lauburu Sovereign AI Monthly Subscription",
        "category": "Software",
        "price_aud": 99.00,
        "stock": 9999,
        "sku": "LAU-SUB-SOV-MON",
        "description": "Continuous access to Sovereign Local AI, zero-mock biometrics telemetry, and priority inference."
    },
    {
        "id": "canon_14",
        "title": "Pay-By-Compute 10M Token Pack",
        "category": "Software",
        "price_aud": 8.00,
        "stock": 9999,
        "sku": "LAU-TOK-10M-PCK",
        "description": "Decentralized mesh compute credits providing high-throughput local Qwen 3.8 Max generation."
    },
    {
        "id": "canon_15",
        "title": "Active Thunderbolt 4 40Gbps Cable 2.0m",
        "category": "Hardware",
        "price_aud": 85.00,
        "stock": 20,
        "sku": "LAU-CAB-TB4-2M",
        "description": "Certified Intel TB4/USB4 active cable delivering 0.27ms DMA ring latencies and 100W PD."
    },
    {
        "id": "canon_16",
        "title": "USB-C to 2.5GbE Ethernet Adapter (RTL8156B)",
        "category": "Hardware",
        "price_aud": 38.00,
        "stock": 25,
        "sku": "LAU-ADP-25G-ETH",
        "description": "Plug-and-play multi-gigabit adapter with aluminum enclosure for Android and Linux mesh nodes."
    },
    {
        "id": "canon_17",
        "title": "GL.iNet Wi-Fi 7 Router Clean-Room Node",
        "category": "Hardware",
        "price_aud": 229.00,
        "stock": 8,
        "sku": "LAU-NET-GLI-WF7",
        "description": "Tri-band Wi-Fi 7 router with dual 2.5GbE ports, OpenWrt OS, and ADB USB bridge passthrough."
    },
    {
        "id": "canon_18",
        "title": "Lauburu 3D Tatami Spatial Kinematics Kit",
        "category": "Hardware",
        "price_aud": 450.00,
        "stock": 6,
        "sku": "LAU-SPT-TAT-KIT",
        "description": "Ultra-wideband anchor nodes and spatial tags calibrated for real-time 3D submission tracking."
    }
]


class CustomerTier:
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"


def parse_customer_tier(tags: List[str]) -> str:
    """Derive membership tier from Shopify customer tags."""
    if not tags:
        return CustomerTier.FREE
    norm_tags = [t.lower().strip() for t in tags]
    for t in norm_tags:
        if "elite" in t or "lauburu_elite" in t:
            return CustomerTier.ELITE
    for t in norm_tags:
        if "pro" in t or "lauburu_pro" in t or "tier_pro" in t or "developer" in t:
            return CustomerTier.PRO
    return CustomerTier.FREE


def validate_dev_token(token: str) -> Optional[Dict[str, Any]]:
    """Opaque-box validator for zero-mock developer fallback tokens."""
    if not token or not isinstance(token, str):
        return None
    token_clean = token.strip()
    if token_clean.startswith(("tok_dev_", "shpat_dev_", "dev_aaron")):
        tier = CustomerTier.PRO
        if "elite" in token_clean:
            tier = CustomerTier.ELITE
        return {
            "id": "gid://shopify/Customer/dev_99999",
            "email": "dev.specialist@lauburu.mesh",
            "firstName": "Aaron",
            "lastName": "Specialist",
            "tags": ["developer", f"lauburu_{tier}"],
            "tier": tier,
            "isDevToken": True
        }
    return None


class PersistentSessionStore:
    """Emulates cross-restart persistent session storage (SharedPreferences contract)."""
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file
        self.data: Dict[str, Any] = {}
        if self.storage_file and self.storage_file.exists():
            try:
                with open(self.storage_file, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def save_session(self, access_token: str, expires_at: str, profile: Dict[str, Any]) -> None:
        self.data = {
            "accessToken": access_token,
            "expiresAt": expires_at,
            "customerProfile": profile,
            "savedAt": time.time()
        }
        if self.storage_file:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w") as f:
                json.dump(self.data, f)

    def load_session(self) -> Optional[Dict[str, Any]]:
        if not self.data or "accessToken" not in self.data:
            return None
        return self.data

    def clear_session(self) -> None:
        self.data = {}
        if self.storage_file and self.storage_file.exists():
            try:
                self.storage_file.unlink()
            except Exception:
                pass

    def is_expired(self, threshold_seconds: int = 60) -> bool:
        session = self.load_session()
        if not session:
            return True
        expires_at = session.get("expiresAt")
        if not expires_at:
            return False
        # Check ISO timestamp or numeric epoch
        try:
            if isinstance(expires_at, (int, float)):
                exp_epoch = float(expires_at)
            else:
                import datetime
                dt = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                exp_epoch = dt.timestamp()
            return (exp_epoch - time.time()) <= threshold_seconds
        except Exception:
            return False


def probe_socket(port: int, host: str = "127.0.0.1", timeout: float = PROBE_TIMEOUT) -> bool:
    """Probes whether a local TCP port is reachable within strict timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def query_local_ai_inference(
    prompt: str,
    max_tokens: int = 64,
    timeout: float = INFERENCE_TIMEOUT
) -> Tuple[bool, str, int]:
    """
    Executes resilient local AI query:
    1. Probes Port 8082 (Sovereign Master Orchestrator). If 503 / offline, fallback to Port 8083.
    2. Enforces strict timeouts and zero fake data.
    Returns (success: bool, content: str, status_code: int).
    """
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }).encode("utf-8")

    # Try Port 8082 first
    for port in [8082, 8083]:
        url = f"http://127.0.0.1:{port}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.getcode()
                body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices", [])
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "")
                    return True, content, status
        except urllib.error.HTTPError as e:
            # If 503 (e.g. Port 8082 Rule 3 RAM protection offline fallback), failover to 8083
            if e.code == 503 and port == 8082:
                continue
            return False, f"HTTPError {e.code}", e.code
        except (urllib.error.URLError, socket.timeout, OSError):
            continue

    return False, "--", 0


def generate_ecommerce_ad_prompt(item: Dict[str, Any]) -> str:
    """Builds direct-response ad copy prompt for a canonical catalog product."""
    return (
        f"Generate a high-converting, 2-sentence direct-response e-commerce hook for "
        f"'{item['title']}' priced at ${item['price_aud']} AUD. Highlight its category '{item['category']}'."
    )
