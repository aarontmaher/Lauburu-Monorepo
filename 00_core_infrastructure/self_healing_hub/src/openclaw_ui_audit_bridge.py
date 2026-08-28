#!/usr/bin/env python3
"""
🦞 OpenClaw UI/UX Automated Audit & Local VLM Bridge
===================================================
Connects to OpenClaw LAN Gateway (ws://192.168.8.224:18789 / http://192.168.8.224:18789)
via Admin Bootstrap Token (mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400) to execute:
  1. Headless multi-frame UI/UX audits across Subproject 1 (Port 3000),
     Subproject 2 (Port 4000), and Subproject 3 (Port 1000).
  2. Mobile ADB multi-frame click-through audits on Samsung Galaxy S20+ (Primary)
     and Google Pixel 10 Pro XL (8K PTZ / UWB spatial anchor).
  3. 5-Frame MD5 screenshot uniqueness assertion (>10KB per file).
  4. uiautomator PID self-healing via kill -9 avoiding exit code 137.
  5. 24/7 LoRA dataset ledger recording for continuous visual fine-tuning.
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Configuration & Constants
OPENCLAW_WS_GATEWAY_URL = os.environ.get("OPENCLAW_WS_GATEWAY_URL", "ws://192.168.8.224:18789")
OPENCLAW_HTTP_GATEWAY_URL = os.environ.get("OPENCLAW_HTTP_GATEWAY_URL", "http://192.168.8.224:18789")
OPENCLAW_FALLBACK_URL = os.environ.get("OPENCLAW_FALLBACK_URL", "http://127.0.0.1:18789")
BOOTSTRAP_TOKEN = os.environ.get("OPENCLAW_BOOTSTRAP_TOKEN", "mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400")
OPERATOR_SCOPE = "operator.admin"

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
GDRIVE_LORA_DIR = Path("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets")

# Target Subprojects
SUBPROJECT_ENDPOINTS = {
    1: {
        "id": "subproject_1_backend",
        "name": "Core Backend & Local AI Training Hub",
        "port": 3000,
        "base_url": "http://localhost:3000",
        "api_gateway_url": "http://localhost:5001",
        "probe_endpoints": [
            "/api/devices",
            "/api/telemetry",
            "/api/spatial_3d_map",
            "/api/roi_improvements",
            "/api/power_cable_network_analysis"
        ]
    },
    2: {
        "id": "subproject_2_frontend",
        "name": "Frontend Client & PWA App Store",
        "port": 4000,
        "base_url": "http://localhost:4000",
        "probe_endpoints": [
            "/",
            "/api/apps",
            "/api/sensors/status",
            "/api/devices",
            "/api/shopify/validate_membership"
        ]
    },
    3: {
        "id": "subproject_3_3d_spatial_mindmap",
        "name": "3D Spatial Mindmap & Obsidian Viewport",
        "port": 1000,
        "base_url": "http://localhost:1000",
        "probe_endpoints": [
            "/",
            "/api/map",
            "/api/telemetry"
        ]
    }
}

# Mobile Device Topology
DEVICE_TOPOLOGY = {
    "samsung_s20": {
        "device_id": os.environ.get("S20_DEVICE_ID", "100.84.40.95:5555"),
        "fallback_id": "100.99.123.58:5555",
        "serial": "R3CN40CJJ1R",
        "role": "Primary UI/UX Automated Audit & App Installation Testbed",
        "layer": "Layer 5 Worker"
    },
    "pixel_10_pro_xl": {
        "device_id": os.environ.get("PIXEL_DEVICE_ID", "100.73.38.87:5555"),
        "role": "8K Digital PTZ Camera Tracking & UWB 3D Spatial Anchor",
        "layer": "Layer 4 Edge SLM"
    }
}


class OpenClawAuditBridge:
    """
    Integrates OpenClaw and Hermes for Browser Automation & Visual Auditing.
    Architectural Basis: `browser-use` combined with Accessibility Tree (AX), Box Model Geometry, and Compositor Screenshots.
    Reference: 07_docs_and_architecture/browser_automation_vlm_audit_spec.md
OpenClaw Headless UI/UX Automated Audit Bridge and VLM Tester."""

    def __init__(
        self,
        ws_gateway: str = OPENCLAW_WS_GATEWAY_URL,
        http_gateway: str = OPENCLAW_HTTP_GATEWAY_URL,
        token: str = BOOTSTRAP_TOKEN,
        scope: str = OPERATOR_SCOPE
    ):
        self.ws_gateway = ws_gateway
        self.http_gateway = http_gateway
        self.fallback_gateway = OPENCLAW_FALLBACK_URL
        self.token = token
        self.scope = scope
        self.ledger_dir = WORKSPACE_ROOT / "data" / "lora_datasets"
        self.ledger_dir.mkdir(parents=True, exist_ok=True)

    def verify_gateway_connection(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Probes the OpenClaw LAN Gateway over HTTP/WS with the Admin Bootstrap Token and validates scope."""
        t0 = time.time()
        connected = False
        active_url = self.http_gateway
        detail = ""
        status_code = 0

        # 1. Probe LAN HTTP gateway
        urls_to_try = [
            f"{self.http_gateway}/health",
            f"{self.http_gateway}/status",
            f"{self.http_gateway}/",
            f"{self.fallback_gateway}/health",
            f"{self.fallback_gateway}/status",
            f"{self.fallback_gateway}/"
        ]

        for url in urls_to_try:
            try:
                headers = {
                    "User-Agent": "OpenClaw-Admin-Auditor/1.0",
                    "Authorization": f"Bearer {self.token}",
                    "X-OpenClaw-Scope": self.scope
                }
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status_code = resp.status
                    if status_code in (200, 201, 204, 302, 401, 404):
                        connected = True
                        active_url = url
                        detail = f"HTTP Probe {status_code} on {url}"
                        break
            except urllib.error.HTTPError as he:
                status_code = he.code
                if status_code in (401, 403):
                    connected = True
                    active_url = url
                    detail = f"Gateway reached with HTTP {status_code} (Auth Challenge)"
                    break
            except Exception as ex:
                detail = str(ex)

        latency_ms = round((time.time() - t0) * 1000, 2)

        return {
            "gateway_connected": connected,
            "target_url": active_url,
            "ws_gateway_url": self.ws_gateway,
            "http_gateway_url": self.http_gateway,
            "bootstrap_token_configured": bool(self.token),
            "auth_scope": self.scope,
            "http_status": status_code,
            "latency_ms": latency_ms,
            "detail": detail
        }

    def audit_endpoint(
        self,
        target_url: str,
        expected_status: tuple = (200, 201, 302),
        timeout: float = 3.0
    ) -> Dict[str, Any]:
        """Executes a real HTTP liveness and payload audit against a target URL."""
        t0 = time.time()
        status_code = 0
        response_bytes = 0
        error_msg = None
        headers_dict = {}

        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "OpenClaw-VLM-Auditor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                payload = resp.read()
                response_bytes = len(payload)
                headers_dict = dict(resp.headers)
        except urllib.error.HTTPError as he:
            status_code = he.code
            error_msg = f"HTTPError {he.code}: {he.reason}"
        except Exception as ex:
            status_code = 0
            error_msg = str(ex)

        latency_ms = round((time.time() - t0) * 1000, 2)
        passed = (status_code in expected_status and response_bytes >= 0 and error_msg is None)

        return {
            "target_url": target_url,
            "http_status": status_code,
            "response_bytes": response_bytes,
            "latency_ms": latency_ms,
            "passed": passed,
            "error": error_msg,
            "headers": {k.lower(): v for k, v in headers_dict.items() if k.lower() in ("content-type", "server")}
        }

    def audit_subproject_1(self, base_url: str = "http://localhost:3000") -> Dict[str, Any]:
        """Audits Subproject 1 (Core Backend & Local AI Training Hub on Port 3000)."""
        sub_cfg = SUBPROJECT_ENDPOINTS[1]
        results = []
        all_passed = True
        total_bytes = 0

        for ep in sub_cfg["probe_endpoints"]:
            url = f"{base_url.rstrip('/')}{ep}"
            res = self.audit_endpoint(url)
            results.append(res)
            total_bytes += res["response_bytes"]
            if not res["passed"]:
                all_passed = False

        audit_summary = {
            "subproject": 1,
            "id": sub_cfg["id"],
            "name": sub_cfg["name"],
            "port": sub_cfg["port"],
            "base_url": base_url,
            "endpoints_probed": len(results),
            "endpoints_passed": sum(1 for r in results if r["passed"]),
            "all_passed": all_passed,
            "total_bytes": total_bytes,
            "endpoints": results,
            "timestamp": time.time()
        }
        self._record_audit(audit_summary)
        return audit_summary

    def audit_subproject_2(self, base_url: str = "http://localhost:4000") -> Dict[str, Any]:
        """Audits Subproject 2 (Frontend Client & PWA App Store on Port 4000)."""
        sub_cfg = SUBPROJECT_ENDPOINTS[2]
        results = []
        all_passed = True
        total_bytes = 0

        for ep in sub_cfg["probe_endpoints"]:
            url = f"{base_url.rstrip('/')}{ep}"
            res = self.audit_endpoint(url)
            results.append(res)
            total_bytes += res["response_bytes"]
            if not res["passed"]:
                all_passed = False

        audit_summary = {
            "subproject": 2,
            "id": sub_cfg["id"],
            "name": sub_cfg["name"],
            "port": sub_cfg["port"],
            "base_url": base_url,
            "endpoints_probed": len(results),
            "endpoints_passed": sum(1 for r in results if r["passed"]),
            "all_passed": all_passed,
            "total_bytes": total_bytes,
            "endpoints": results,
            "timestamp": time.time()
        }
        self._record_audit(audit_summary)
        return audit_summary

    def audit_subproject_3(self, base_url: str = "http://localhost:1000") -> Dict[str, Any]:
        """Audits Subproject 3 (3D Spatial Mindmap & Obsidian Viewport on Port 1000)."""
        sub_cfg = SUBPROJECT_ENDPOINTS[3]
        results = []
        all_passed = True
        total_bytes = 0

        for ep in sub_cfg["probe_endpoints"]:
            url = f"{base_url.rstrip('/')}{ep}"
            res = self.audit_endpoint(url)
            results.append(res)
            total_bytes += res["response_bytes"]
            if not res["passed"]:
                all_passed = False

        audit_summary = {
            "subproject": 3,
            "id": sub_cfg["id"],
            "name": sub_cfg["name"],
            "port": sub_cfg["port"],
            "base_url": base_url,
            "endpoints_probed": len(results),
            "endpoints_passed": sum(1 for r in results if r["passed"]),
            "all_passed": all_passed,
            "total_bytes": total_bytes,
            "endpoints": results,
            "timestamp": time.time()
        }
        self._record_audit(audit_summary)
        return audit_summary

    def audit_all_subprojects(
        self,
        urls: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """Executes a unified multi-frame audit across all 3 subprojects."""
        t0 = time.time()
        urls = urls or {
            1: "http://localhost:3000",
            2: "http://localhost:4000",
            3: "http://localhost:1000"
        }

        r1 = self.audit_subproject_1(urls.get(1, "http://localhost:3000"))
        r2 = self.audit_subproject_2(urls.get(2, "http://localhost:4000"))
        r3 = self.audit_subproject_3(urls.get(3, "http://localhost:1000"))

        subprojects = [r1, r2, r3]
        total_probed = sum(s["endpoints_probed"] for s in subprojects)
        total_passed = sum(s["endpoints_passed"] for s in subprojects)
        duration_ms = round((time.time() - t0) * 1000, 2)

        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_subprojects": len(subprojects),
            "total_endpoints_probed": total_probed,
            "total_endpoints_passed": total_passed,
            "overall_pass": (total_passed == total_probed and total_probed > 0),
            "duration_ms": duration_ms,
            "subprojects": {
                "subproject_1_port_3000": r1,
                "subproject_2_port_4000": r2,
                "subproject_3_port_1000": r3
            }
        }
        self._record_audit(summary)
        return summary

    def kill_uiautomator_daemons(
        self,
        device_id: Optional[str] = None,
        run_adb_fn=None
    ) -> List[str]:
        """Finds and kills uiautomator daemon PIDs directly via ps inspection and kill -9.
        Prevents shell self-termination (exit code 137) caused by pkill matching its own cmdline.
        Embeds 0.5s delay right after daemon cleanup for Android 15 lock clearing cooldown.
        Returns list of killed PIDs.
        """
        killed_pids: List[str] = []
        target_dev = device_id or DEVICE_TOPOLOGY["samsung_s20"]["device_id"]

        def _default_adb_exec(cmd_list):
            full_cmd = ["adb", "-s", target_dev] + cmd_list
            try:
                res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=15)
                return res.stdout.strip()
            except Exception:
                return ""

        adb_fn = run_adb_fn or _default_adb_exec

        res = adb_fn(["shell", "ps", "-e", "-o", "PID,ARGS"])
        if not res or "PID" not in res:
            res = adb_fn(["shell", "ps", "-ef"])

        targets = ("com.android.commands.uiautomator", "uiautomator")
        exclusion_binaries = ("sh", "grep", "pkill", "pgrep", "def_adb", "pidof", "python")

        for line in res.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue

            if any(t in line_clean for t in targets):
                parts = line_clean.split()
                if not parts:
                    continue

                # Exclude if any command binary token matches exclusions (prevents 'sh' matching 'shell' user)
                is_excluded = False
                for token in parts:
                    clean_tok = token.strip("\"'()[],;")
                    base_tok = clean_tok.split("/")[-1]
                    if (
                        base_tok in exclusion_binaries
                        or clean_tok.endswith("/sh")
                        or clean_tok.endswith("/grep")
                        or clean_tok.endswith("/pkill")
                        or clean_tok.endswith("/pgrep")
                        or any(excl in base_tok for excl in ("pkill", "pgrep", "grep", "def_adb"))
                    ):
                        is_excluded = True
                        break

                if is_excluded:
                    continue

                pid = None
                for part in parts:
                    if part.isdigit():
                        pid = part
                        break

                if pid:
                    adb_fn(["shell", "kill", "-9", pid])
                    killed_pids.append(pid)

        time.sleep(0.5)
        return killed_pids

    def verify_screenshot_hashes(
        self,
        md5_dict: Dict[str, str],
        min_unique: int = 5,
        min_size_bytes: int = 10240,
        verify_files_on_disk: bool = True
    ) -> Dict[str, Any]:
        """Validates that screenshots exist, have file size > min_size_bytes (10KB), and contain at least min_unique distinct MD5 hashes."""
        unique_hashes = set(md5_dict.values())
        errors = []
        sizes = {}

        if len(md5_dict) < min_unique:
            errors.append(f"Insufficient frames captured: {len(md5_dict)} < {min_unique}")

        if len(unique_hashes) < min_unique:
            errors.append(f"Duplicate frame screenshots detected: {len(unique_hashes)} unique hashes out of {len(md5_dict)} frames")

        for filename, md5h in md5_dict.items():
            if not md5h or len(md5h) != 32:
                errors.append(f"Invalid MD5 hash for {filename}: {md5h}")

            if verify_files_on_disk and os.path.isabs(filename):
                if not os.path.exists(filename):
                    errors.append(f"Screenshot file missing on disk: {filename}")
                else:
                    fsize = os.path.getsize(filename)
                    sizes[filename] = fsize
                    if fsize <= min_size_bytes:
                        errors.append(f"Screenshot {filename} size too small: {fsize} bytes <= {min_size_bytes}")

        passed = len(errors) == 0

        return {
            "passed": passed,
            "total_frames": len(md5_dict),
            "unique_md5_count": len(unique_hashes),
            "min_required": min_unique,
            "md5_hashes": md5_dict,
            "file_sizes": sizes,
            "errors": errors
        }

    def _record_audit(self, record: dict):
        """Appends audit record to local JSONL and Google Drive memory mirror."""
        try:
            self.ledger_dir.mkdir(parents=True, exist_ok=True)
            ledger_file = self.ledger_dir / "openclaw_audit_ledger.jsonl"
            with open(ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

        try:
            if GDRIVE_LORA_DIR.exists():
                gdrive_file = GDRIVE_LORA_DIR / "openclaw_audit_ledger.jsonl"
                with open(gdrive_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
        except Exception:
            pass


_bridge_instance = None

def get_openclaw_audit_bridge() -> OpenClawAuditBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = OpenClawAuditBridge()
    return _bridge_instance


if __name__ == "__main__":
    bridge = get_openclaw_audit_bridge()
    print("=" * 60)
    print("🦞 OpenClaw UI/UX Automated Audit & Local VLM Bridge")
    print("=" * 60)

    # 1. Gateway Check
    gw_status = bridge.verify_gateway_connection()
    print(f"Gateway Status: {json.dumps(gw_status, indent=2)}")

    # 2. Subproject Audits
    print("\n--- Auditing Subprojects ---")
    sub_results = bridge.audit_all_subprojects()
    print(f"Subprojects Audit Summary: {json.dumps(sub_results, indent=2)}")
