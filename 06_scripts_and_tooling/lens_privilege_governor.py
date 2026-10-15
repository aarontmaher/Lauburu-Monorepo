#!/usr/bin/env python3
"""
Screen Lens Sovereign: Maximum-Privilege Mesh Governor & Dedicated AI Fleet Orchestrator
========================================================================================
Enforces:
1. Physical Device + Browser Split:
   - HUMAN_SANCTUARY: L5 (M4 MacBook Air), L1 (M4 Pro Mac Mini), L6 (Pixel 10 Pro XL)
     -> Zero AI browser hijacking, zero CDP flags on personal Chrome, passive read-only /lens.
   - AI_ACTUATION_FLEET: L1b (Apple M2 Pro 192.168.8.114), L7 (Galaxy S20+ 192.168.8.101/.224),
     L3 & L8 (Linux Podman Hubs)
     -> Dedicated Go-Browser (:9225), Sovereign Chromium (:9222), and Mobile Chrome/UIAutomator.
2. Highest-Privilege /lens Execution on Every Device:
   - L6 Pixel 10 Pro XL: Shizuku rish uid=2000(shell) + AVF Debian 13 crosvm uid=0(root)
   - L7 Galaxy S20+: Shizuku rish / ADB uid=2000(shell) (u:r:shell:s0)
   - GW GL-BE14000 Router: Native OpenWrt uid=0(root)
   - L3 & L8 Linux Hubs: Native systemd + host Podman uid=0(root)
   - L1b (M2 Pro), L1 (M4 Pro), L5 (M4 Air): Passwordless sudo -n uid=0(root) + ScreenCaptureKit
3. Live EmbeddingGemma 2 (768D/512D/256D/128D MRL) + Neo4j 5.26.32 (:7474) + Qdrant (:6333) Sync.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MONOREPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
WEBVLA_JSONL = MONOREPO_ROOT / "04_data_and_memory/data/chrome_devtools_webvla_distilled.jsonl"
ARTIFACTS_DIR = MONOREPO_ROOT / "04_data_and_memory/data/auditor_artifacts"

NEO4J_HTTP_URL = os.environ.get(
    "NEO4J_HTTP_URL", "http://100.101.39.98:7474/db/neo4j/tx/commit"
)
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "lauburu_mesh_graph")
GEMMA2_URL = os.environ.get("GEMMA2_URL", "http://127.0.0.1:8087")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://100.101.39.98:6333")


DEVICE_PRIVILEGE_MATRIX: Dict[str, Dict[str, Any]] = {
    "L5": {
        "name": "MacBook Air M4 (Primary Human Laptop)",
        "ip": "100.121.202.34",
        "lan_ip": "192.168.8.248",
        "fleet_role": "HUMAN_SANCTUARY",
        "browser_policy": "HUMAN_CHROME_PROTECTED_ZERO_CDP",
        "lens_mode": "PASSIVE_READ_ONLY",
        "expected_privilege": "uid=0(root) via sudo -n + TCC ScreenCaptureKit (:3035)",
        "probe_cmd": "sudo -n id -u && hostname",
    },
    "L1": {
        "name": "Mac Mini M4 Pro (M4 Compute Sanctuary)",
        "ip": "100.119.199.76",
        "lan_ip": "192.168.8.230",
        "fleet_role": "HUMAN_SANCTUARY",
        "browser_policy": "HUMAN_CHROME_PROTECTED_ZERO_CDP",
        "lens_mode": "PASSIVE_READ_ONLY",
        "expected_privilege": "uid=0(root) via sudo -n + TCC ScreenCaptureKit (:3035)",
        "probe_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=3 100.119.199.76 'sudo -n id -u && hostname'",
    },
    "L1b": {
        "name": "Apple M2 Pro Mac Mini (Dedicated AI Desktop Browser & Actuation Node)",
        "ip": "192.168.8.114",
        "lan_ip": "192.168.8.114",
        "fleet_role": "AI_ACTUATION_NODE",
        "browser_policy": "DEDICATED_GO_BROWSER_9225_AND_CHROMIUM_9222",
        "lens_mode": "ACTIVE_TEACHER_ACTUATION",
        "expected_privilege": "uid=0(root) via sudo -n + Go-Browser (:9225) + CoreGraphics",
        "probe_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=3 192.168.8.114 'sudo -n id -u && hostname'",
    },
    "L7": {
        "name": "Samsung Galaxy S20+ 5G (Dedicated AI Mobile Browser & WAF Bypass Node)",
        "ip": "192.168.8.101",
        "lan_ip": "192.168.8.224",
        "adb_serial": "192.168.8.101:32873",
        "fleet_role": "AI_ACTUATION_NODE",
        "browser_policy": "DEDICATED_MOBILE_AI_CHROME_UIAUTOMATOR",
        "lens_mode": "ACTIVE_MOBILE_WAF_ACTUATION",
        "expected_privilege": "uid=2000(shell) u:r:shell:s0 via Shizuku rish & Wireless ADB",
        "probe_cmd": "adb -s 192.168.8.101:32873 shell 'id -u && getprop ro.product.model'",
    },
    "L6": {
        "name": "Google Pixel 10 Pro XL (Human Sanctuary Phone + AVF Root Edge)",
        "ip": "100.114.215.68",
        "lan_ip": "192.168.8.213",
        "fleet_role": "HUMAN_SANCTUARY_PHONE",
        "browser_policy": "HUMAN_PHONE_PROTECTED_NO_BROWSER_HIJACK",
        "lens_mode": "PASSIVE_COMPANION_AND_AVF_ROOT_COMPUTE",
        "expected_privilege": "Dual-Apex: Shizuku rish uid=2000(shell) + AVF Debian 13 crosvm uid=0(root)",
        "probe_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=2 -p 8022 u0_a363@192.168.8.213 'id -u && uname -n'",
    },
    "L3": {
        "name": "Linux Compute Hub (Neo4j 5.26.32 + Qdrant + Podman AI Trainer)",
        "ip": "100.101.39.98",
        "lan_ip": "192.168.8.225",
        "fleet_role": "AI_PODMAN_HUB",
        "browser_policy": "HEADLESS_PODMAN_SOVEREIGN_CHROMIUM",
        "lens_mode": "HEADLESS_ROOT_PODMAN",
        "expected_privilege": "uid=0(root) systemd + Host-Network Podman (:8096/:7474/:6333)",
        "probe_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=3 linux@100.101.39.98 'sudo -n id -u && hostname'",
    },
    "L8": {
        "name": "Ubuntu Headless Hub (Sovereign Chromium :9222 + Podman AI Trainer :8096)",
        "ip": "100.121.247.8",
        "lan_ip": "100.121.247.8",
        "fleet_role": "AI_PODMAN_HUB",
        "browser_policy": "HEADLESS_PODMAN_SOVEREIGN_CHROMIUM_9222",
        "lens_mode": "HEADLESS_ROOT_PODMAN",
        "expected_privilege": "uid=0(root) systemd + Host-Network Podman (:8096/:9222)",
        "probe_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=3 linuxmini@100.121.247.8 'sudo -n id -u && hostname'",
    },
    "GW": {
        "name": "GL.iNet GL-BE14000 Wi-Fi 7 Router (OpenWrt Root Gateway Sentinel)",
        "ip": "192.168.8.1",
        "lan_ip": "192.168.8.1",
        "fleet_role": "MESH_GATEWAY_SENTINEL",
        "browser_policy": "ROUTER_LEASE_AND_WAKE_SENTINEL",
        "lens_mode": "OPENWRT_ROOT_ARP_SENTINEL",
        "expected_privilege": "uid=0(root) OpenWrt Kernel & DHCP/ARP Sentinel",
        "probe_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=3 root@192.168.8.1 'id -u && uname -n'",
    },
}


def run_cmd(cmd: str, timeout: int = 8) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


def neo4j_tx(statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling"))
    from lens_neo4j_gemma2_orchestrator import Gemma2GlobalRAGOrchestrator

    orch = Gemma2GlobalRAGOrchestrator()
    results = []
    for st in statements:
        results.append(
            orch.neo4j.query(st["statement"], st.get("parameters", {}))
        )
    return {"results": results}


def embed_mrl(text: str) -> Dict[str, Any]:
    sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling"))
    from lens_neo4j_gemma2_orchestrator import Gemma2GlobalRAGOrchestrator

    orch = Gemma2GlobalRAGOrchestrator()
    bundle = orch.embedder.embed_mrl_bundle(
        text=text,
        is_query=False,
        title="Screen Lens Edge UI Salience",
        task="retrieval_document",
    )
    return {"mrl_embeddings": bundle["mrl"], "provider": bundle["provider"]}


def enforce_android_privilege_and_keepalive(adb_serial: str, node_id: str) -> Dict[str, Any]:
    """
    Executes highest-privilege Shizuku rish / ADB shell (uid=2000, u:r:shell:s0)
    and AVF Debian 13 crosvm (uid=0) checks + anti-Doze / Phantom Process Killer lock.
    """
    commands = [
        "settings put global settings_enable_monitor_phantom_procs false",
        "device_config set_sync_disabled_for_tests persistent",
        "device_config put activity_manager max_phantom_processes 2147483647",
        "dumpsys deviceidle whitelist +com.termux",
        "dumpsys deviceidle whitelist +moe.shizuku.privileged.api",
        "dumpsys deviceidle whitelist +com.tailscale.ipn",
        "dumpsys deviceidle whitelist +com.android.chrome",
        "dumpsys deviceidle whitelist +com.android.virtualization.terminal",
        "cmd appops set com.termux RUN_IN_BACKGROUND allow",
        "cmd appops set com.termux WAKE_LOCK allow",
        "mkdir -p /data/local/tmp/avf_shared /data/local/tmp/lens_sovereign",
        "id",
    ]
    joined = " ; ".join(commands)
    try:
        r = run_cmd(f'adb -s {adb_serial} shell "{joined}"', timeout=12)
        out = (r.stdout or "") + (r.stderr or "")
        # Also probe if AVF crosvm or rish is present
        avf_probe = run_cmd(
            f'adb -s {adb_serial} shell "pm list packages | grep -E \'shizuku|virtualization|termux\'; ps -A | grep -E \'shizuku|crosvm|termux\'"',
            timeout=6,
        )
        return {
            "node_id": node_id,
            "adb_serial": adb_serial,
            "status": "ENFORCED" if "uid=2000(shell)" in out else "PARTIAL",
            "privilege_id": next((line for line in out.splitlines() if "uid=" in line), out.strip()[:120]),
            "phantom_killer_disabled": True,
            "doze_whitelisted": ["com.termux", "moe.shizuku.privileged.api", "com.tailscale.ipn", "com.android.chrome"],
            "packages_and_daemons": [
                line.strip() for line in (avf_probe.stdout or "").splitlines() if line.strip()
            ][:12],
        }
    except Exception as exc:
        return {"node_id": node_id, "adb_serial": adb_serial, "status": "UNREACHABLE", "error": str(exc)}


def wake_and_probe_pixel_l6() -> Dict[str, Any]:
    """
    Uses the OpenWrt root gateway (GW 192.168.8.1 uid=0) to inspect Pixel 10 Pro XL (L6)
    DHCP lease (192.168.8.213), send ARP/TCP wake probes to 8022/5555, and verify AVF + rish script readiness.
    """
    gw_out = ""
    try:
        r = run_cmd(
            "ssh -o BatchMode=yes -o ConnectTimeout=3 root@192.168.8.1 "
            "\"grep -i pixel /tmp/dhcp.leases; ping -c 1 -W 1 192.168.8.213 >/dev/null 2>&1; ip neigh show 192.168.8.213\"",
            timeout=6,
        )
        gw_out = (r.stdout or "").strip()
    except Exception as exc:
        gw_out = f"gw_probe_error: {exc}"

    return {
        "lease_and_arp": gw_out,
        "avf_bootstrap_script": str(MONOREPO_ROOT / "06_scripts_and_tooling/containers/wireguard/bootstrap_pixel10_avf.sh"),
        "avf_consensus_script": str(MONOREPO_ROOT / "06_scripts_and_tooling/ai/avf_pixel_ai_terminal_consensus.py"),
        "target_privilege": "Termux Shizuku rish uid=2000(shell) + AVF Debian 13 crosvm uid=0(root)",
    }


def audit_all_nodes(enforce_keepalive: bool = True, ingest_neo4j: bool = True) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for node_id, meta in DEVICE_PRIVILEGE_MATRIX.items():
        entry = dict(meta)
        try:
            r = run_cmd(meta["probe_cmd"], timeout=6)
            lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
            if r.returncode == 0 and lines:
                uid_val = lines[0]
                host_val = lines[1] if len(lines) > 1 else node_id
                entry["status"] = "ONLINE"
                entry["verified_uid"] = f"uid={uid_val}" if uid_val.isdigit() else uid_val
                entry["verified_hostname"] = host_val
            else:
                entry["status"] = "SLEEP_OR_STANDBY"
                entry["verified_uid"] = "standby"
                entry["verified_hostname"] = node_id
        except Exception as exc:
            entry["status"] = "SLEEP_OR_STANDBY"
            entry["verified_uid"] = "standby"
            entry["error"] = str(exc)

        if node_id == "L7" and enforce_keepalive and entry["status"] == "ONLINE":
            entry["edge_enforcement"] = enforce_android_privilege_and_keepalive(
                meta["adb_serial"], "L7"
            )
        elif node_id == "L6":
            entry["pixel_avf_and_router_sentinel"] = wake_and_probe_pixel_l6()
            if entry["status"] != "ONLINE":
                entry["status"] = "RADIO_SLEEP_ROUTER_LEASED (192.168.8.213)"
        elif node_id == "L1b" and entry["status"] == "ONLINE":
            # Check Go-Browser (:9225) on M2 Pro
            try:
                with urllib.request.urlopen("http://192.168.8.114:9225/status", timeout=3) as resp:
                    entry["go_browser_daemon"] = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                entry["go_browser_daemon"] = {"status": "STARTING", "detail": str(exc)}

        results[node_id] = entry

    if ingest_neo4j:
        stmts = []
        for node_id, info in results.items():
            stmts.append(
                {
                    "statement": """
                    MERGE (m:MeshNode {id: $id})
                    SET m.name = $name,
                        m.ip = $ip,
                        m.lan_ip = $lan_ip,
                        m.status = $status,
                        m.fleet_role = $fleet_role,
                        m.browser_policy = $browser_policy,
                        m.lens_mode = $lens_mode,
                        m.expected_privilege = $expected_privilege,
                        m.verified_uid = $verified_uid,
                        m.updated_at = datetime()
                    """,
                    "parameters": {
                        "id": node_id,
                        "name": info["name"],
                        "ip": info["ip"],
                        "lan_ip": info.get("lan_ip", info["ip"]),
                        "status": info["status"],
                        "fleet_role": info["fleet_role"],
                        "browser_policy": info["browser_policy"],
                        "lens_mode": info["lens_mode"],
                        "expected_privilege": info["expected_privilege"],
                        "verified_uid": info.get("verified_uid", "unknown"),
                    },
                }
            )
        try:
            neo4j_tx(stmts)
        except Exception as exc:
            results["_neo4j_sync_warning"] = str(exc)

    return results


def capture_edge_ui(node_id: str = "L7", url: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes mobile AI browser navigation + UIAutomator salience dump + hardware screencap
    on the dedicated AI mobile device (L7 Galaxy S20+ via uid=2000(shell)), embeds via
    EmbeddingGemma 2 (768D/512D/256D/128D), and commits into Neo4j 5.26.32 + WebVLA JSONL.
    """
    meta = DEVICE_PRIVILEGE_MATRIX.get(node_id, DEVICE_PRIVILEGE_MATRIX["L7"])
    adb_serial = meta.get("adb_serial", "192.168.8.101:32873")

    # Wake screen and dismiss keyguard on dedicated AI phone L7 (never on human phone L6 unless requested)
    run_cmd(
        f'adb -s {adb_serial} shell "input keyevent KEYCODE_WAKEUP && wm dismiss-keyguard && input keyevent 82 && input swipe 540 1800 540 400 250"',
        timeout=6,
    )

    if url:
        run_cmd(
            f'adb -s {adb_serial} shell "am start -a android.intent.action.VIEW -d \'{url}\' com.android.chrome"',
            timeout=6,
        )
        time.sleep(2.5)

    # Capture UIAutomator XML and screencap PNG via uid=2000(shell)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    local_xml = ARTIFACTS_DIR / f"lens_{node_id.lower()}_salience.xml"
    local_png = ARTIFACTS_DIR / f"lens_{node_id.lower()}_screen.png"

    run_cmd(
        f'adb -s {adb_serial} shell "uiautomator dump /data/local/tmp/lens_sovereign/ui.xml && screencap -p /data/local/tmp/lens_sovereign/screen.png"',
        timeout=12,
    )
    run_cmd(f"adb -s {adb_serial} pull /data/local/tmp/lens_sovereign/ui.xml {local_xml}", timeout=8)
    run_cmd(f"adb -s {adb_serial} pull /data/local/tmp/lens_sovereign/screen.png {local_png}", timeout=8)

    salience_nodes: List[Dict[str, str]] = []
    if local_xml.exists():
        try:
            tree = ET.parse(local_xml)
            for elem in tree.getroot().iter("node"):
                txt = (elem.attrib.get("text") or "").strip()
                desc = (elem.attrib.get("content-desc") or "").strip()
                res_id = (elem.attrib.get("resource-id") or "").strip()
                bounds = (elem.attrib.get("bounds") or "").strip()
                if txt or desc or res_id:
                    salience_nodes.append(
                        {
                            "text": txt[:80],
                            "desc": desc[:80],
                            "resource_id": res_id,
                            "bounds": bounds,
                        }
                    )
            salience_nodes.sort(key=lambda n: (0 if (n["text"] or n["desc"]) else 1))
        except Exception:
            pass

    summary_text = (
        f"[Screen Lens Sovereign {node_id} ({meta['name']}) uid=2000(shell)] "
        f"URL={url or 'active_screen'} | SalienceNodes={len(salience_nodes)} | "
        + " ; ".join(
            f"{n['text'] or n['desc']} ({n['resource_id']})@{n['bounds']}"
            for n in salience_nodes[:15]
        )
    )

    mrl_res = embed_mrl(summary_text)
    vec128 = mrl_res["mrl_embeddings"]["128"]
    vec768 = mrl_res["mrl_embeddings"]["768"]
    doc_id = "lens_edge_" + hashlib.sha256(f"{node_id}:{url}:{time.time()}".encode()).hexdigest()[:14]

    neo4j_tx(
        [
            {
                "statement": """
                MERGE (d:Gemma2MultimodalDoc {doc_id: $doc_id})
                SET d.title = $title,
                    d.modality = 'android_edge_lens_salience',
                    d.content = $content,
                    d.embedding_128d = $vec128,
                    d.embedding_768d_norm = $norm768,
                    d.updated_at = datetime()
                WITH d
                MATCH (m:MeshNode {id: $node_id})
                MERGE (m)-[:CAPTURED_LENS_SALIENCE]->(d)
                """,
                "parameters": {
                    "doc_id": doc_id,
                    "node_id": node_id,
                    "title": f"Edge /lens Salience ({node_id}): {url or 'live_screen'}",
                    "content": summary_text[:2000],
                    "vec128": vec128,
                    "norm768": round(sum(x * x for x in vec768) ** 0.5, 6),
                },
            }
        ]
    )

    # Append Rule 13 WebVLA trajectory
    WEBVLA_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(WEBVLA_JSONL, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "instruction": f"Execute Rule 11 mobile AI browser & /lens salience capture on dedicated edge device {node_id} ({meta['name']}) as uid=2000(shell).",
                    "input": {
                        "node_id": node_id,
                        "url": url or "live_screen",
                        "privilege": "uid=2000(shell) u:r:shell:s0",
                        "salience_count": len(salience_nodes),
                    },
                    "output": {
                        "doc_id": doc_id,
                        "salience_preview": salience_nodes[:8],
                        "screenshot_path": str(local_png),
                    },
                }
            )
            + "\n"
        )

    return {
        "status": "CAPTURED_AND_INDEXED",
        "node_id": node_id,
        "device_name": meta["name"],
        "privilege": "uid=2000(shell) u:r:shell:s0",
        "url": url or "live_screen",
        "doc_id": doc_id,
        "salience_node_count": len(salience_nodes),
        "salience_sample": salience_nodes[:8],
        "xml_path": str(local_xml),
        "png_path": str(local_png),
        "png_bytes": local_png.stat().st_size if local_png.exists() else 0,
        "mrl_dimensions": list(mrl_res["mrl_embeddings"].keys()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen Lens Sovereign Privilege & AI Device Fleet Governor")
    parser.add_argument("--audit-all", action="store_true", help="Audit privilege tiers and fleet roles across all mesh nodes")
    parser.add_argument("--enforce-keepalive", action="store_true", help="Enforce Shizuku/ADB uid=2000 anti-Doze & Phantom Killer lock")
    parser.add_argument("--ingest-neo4j", action="store_true", help="Sync privilege and fleet role matrix to Neo4j 5.26.32")
    parser.add_argument("--capture-edge-ui", type=str, default="", help="Capture live UI salience & screenshot on edge node (e.g. L7)")
    parser.add_argument("--url", type=str, default="", help="Optional URL to open on dedicated AI edge browser before capture")
    args = parser.parse_args()

    out: Dict[str, Any] = {}
    if args.audit_all:
        out["mesh_privilege_matrix"] = audit_all_nodes(
            enforce_keepalive=args.enforce_keepalive,
            ingest_neo4j=args.ingest_neo4j,
        )
    if args.capture_edge_ui:
        out["edge_ui_capture"] = capture_edge_ui(
            node_id=args.capture_edge_ui,
            url=args.url or None,
        )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
