#!/usr/bin/env python3
"""
Syncthing Mesh Federation Engine — Lauburu Ecosystem
=====================================================
Automates cross-device Syncthing peering, folder configuration,
and synchronization status monitoring across the 7 mesh layers.

Nodes:
- Mac Mini (L1): W5KWZRZ-ZCIMXNW-4DL46C2-MRJLB24-L6LXIEX-GO4FNOX-QYLASSN-YHIHDA3
- Linux Mini (L3): C4LVDFV-WU52UP7-ZBFEJHJ-K6WRXYB-SG3CW3O-Y7JFF25-JM6HUM7-XQ223AD
- Pixel 10 Pro XL (L6): LNVQC7N-35SA4QV-PF3QUTH-4SE2ZSX-NAXP5SW-DYDM2E5-MACM7OE-CIXAEAY
- Samsung Galaxy S20+ (L7): BF6KFOQ-URV74DS-PXCLYCU-A34NV3T-4WJV4IJ-EWQGS4I-K3SQLIQ-5R2ZWA2
- MacBook Air (L5): 3WPP5UW-KZNTR2Y-FVK3BEO-E42GE3W-7LWGYW3-VLNIKHW-CHF3SRD-3F5VQAP
- Gateway Router: DP2ZXQV-YSMYYKX-TCANKQQ-6SAHL5L-7HDE4OU-LVMOSH7-CDS266U-BGGRBA3
"""

import sys
import os
import json
import subprocess
import urllib.request
import urllib.error

MAC_MINI_API = "http://127.0.0.1:8384"
MAC_MINI_KEY = "Gz6WJUd9GdCWUR3oYpQGYrgTHT4hDZy5"
MAC_MINI_ID = "W5KWZRZ-ZCIMXNW-4DL46C2-MRJLB24-L6LXIEX-GO4FNOX-QYLASSN-YHIHDA3"

LINUX_MINI_IP = "100.101.39.98"
LINUX_MINI_ID = "C4LVDFV-WU52UP7-ZBFEJHJ-K6WRXYB-SG3CW3O-Y7JFF25-JM6HUM7-XQ223AD"
LINUX_MINI_KEY = "F6ToKVTkoU3MVJF5jNRh5zWPhkdhocZP"

FOLDERS_TO_FEDERATE = [
    {
        "id": "lauburu-obsidian",
        "label": "Lauburu Obsidian Vault",
        "mac_path": "/Volumes/Lauburu-Monorepo/obsidian_vault",
        "linux_path": "/home/linux/lauburu_sync/obsidian_vault"
    },
    {
        "id": "lauburu-core-infra",
        "label": "Lauburu Core Infrastructure",
        "mac_path": "/Volumes/Lauburu-Monorepo/00_core_infrastructure",
        "linux_path": "/home/linux/lauburu_sync/00_core_infrastructure"
    },
    {
        "id": "lauburu-scripts",
        "label": "Lauburu Scripts and Tooling",
        "mac_path": "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling",
        "linux_path": "/home/linux/lauburu_sync/06_scripts_and_tooling"
    },
    {
        "id": "unified_workspace",
        "label": "Unified Workspace",
        "mac_path": "/Volumes/Lauburu-Monorepo/unified_workspace",
        "linux_path": "/home/linux/lauburu_sync/unified_workspace"
    }
]

def syncthing_req(base_url, api_key, path, method="GET", data=None):
    url = f"{base_url}{path}"
    headers = {"X-API-Key": api_key}
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except Exception as e:
        print(f"[-] Error calling {url}: {e}", file=sys.stderr)
        return None

def configure_mac_mini():
    print("[+] Querying Mac Mini Syncthing configuration...")
    cfg = syncthing_req(MAC_MINI_API, MAC_MINI_KEY, "/rest/config")
    if not cfg:
        print("[-] Failed to retrieve Mac Mini configuration")
        return False

    # 1. Add Linux Mini device if missing
    existing_dev_ids = {d["deviceID"] for d in cfg.get("devices", [])}
    if LINUX_MINI_ID not in existing_dev_ids:
        print(f"[+] Adding Linux Mini ({LINUX_MINI_ID[:12]}...) to Mac Mini devices...")
        cfg.setdefault("devices", []).append({
            "deviceID": LINUX_MINI_ID,
            "name": "Linux-Mini-L3",
            "addresses": ["dynamic", f"tcp://{LINUX_MINI_IP}:22000", "tcp://192.168.8.225:22000"],
            "compression": "metadata",
            "certName": "",
            "introducer": False,
            "skipIntroductionRemovals": False,
            "introducedBy": "",
            "paused": False,
            "allowedNetworks": [],
            "autoAcceptFolders": True,
            "maxSendKbps": 0,
            "maxRecvKbps": 0,
            "ignoredFolders": []
        })

    # 2. Add/update folders
    existing_folders = {f["id"]: f for f in cfg.get("folders", [])}
    for item in FOLDERS_TO_FEDERATE:
        f_id = item["id"]
        if f_id in existing_folders:
            folder = existing_folders[f_id]
            dev_ids = {d["deviceID"] for d in folder.get("devices", [])}
            if LINUX_MINI_ID not in dev_ids:
                folder.setdefault("devices", []).append({"deviceID": LINUX_MINI_ID, "introducedBy": ""})
                print(f"[+] Shared folder '{f_id}' with Linux Mini on Mac Mini")
        else:
            print(f"[+] Registering new folder '{f_id}' on Mac Mini...")
            os.makedirs(item["mac_path"], exist_ok=True)
            cfg.setdefault("folders", []).append({
                "id": f_id,
                "label": item["label"],
                "path": item["mac_path"],
                "type": "sendreceive",
                "devices": [
                    {"deviceID": MAC_MINI_ID, "introducedBy": ""},
                    {"deviceID": LINUX_MINI_ID, "introducedBy": ""},
                    {"deviceID": "LNVQC7N-35SA4QV-PF3QUTH-4SE2ZSX-NAXP5SW-DYDM2E5-MACM7OE-CIXAEAY", "introducedBy": ""},
                    {"deviceID": "BF6KFOQ-URV74DS-PXCLYCU-A34NV3T-4WJV4IJ-EWQGS4I-K3SQLIQ-5R2ZWA2", "introducedBy": ""}
                ],
                "rescanIntervalS": 60,
                "fsWatcherEnabled": True,
                "fsWatcherDelayS": 10,
                "ignorePerms": False,
                "autoNormalize": True
            })

    print("[+] Updating Mac Mini configuration via PUT /rest/config...")
    res = syncthing_req(MAC_MINI_API, MAC_MINI_KEY, "/rest/config", method="PUT", data=cfg)
    return res is not None

def configure_linux_mini():
    print("[+] Querying Linux Mini Syncthing configuration over SSH...")
    cmd_get = (
        f"curl -s -H 'X-API-Key: {LINUX_MINI_KEY}' http://127.0.0.1:8384/rest/config"
    )
    res = subprocess.run(["ssh", "-o", "BatchMode=yes", f"linux@{LINUX_MINI_IP}", cmd_get],
                         capture_output=True, text=True, timeout=15)
    if res.returncode != 0 or not res.stdout.strip():
        print(f"[-] Failed to get Linux Mini config: {res.stderr}")
        return False

    try:
        cfg = json.loads(res.stdout)
    except Exception as e:
        print(f"[-] Failed to parse Linux config: {e}")
        return False

    # 1. Add Mac Mini device if missing
    existing_dev_ids = {d["deviceID"] for d in cfg.get("devices", [])}
    if MAC_MINI_ID not in existing_dev_ids:
        print(f"[+] Adding Mac Mini ({MAC_MINI_ID[:12]}...) to Linux Mini devices...")
        cfg.setdefault("devices", []).append({
            "deviceID": MAC_MINI_ID,
            "name": "Mac-Mini-L1",
            "addresses": ["dynamic", "tcp://100.119.199.76:22000", "tcp://192.168.8.230:22000"],
            "compression": "metadata",
            "certName": "",
            "introducer": False,
            "skipIntroductionRemovals": False,
            "introducedBy": "",
            "paused": False,
            "allowedNetworks": [],
            "autoAcceptFolders": True,
            "maxSendKbps": 0,
            "maxRecvKbps": 0,
            "ignoredFolders": []
        })

    # 2. Add/update folders on Linux Mini
    existing_folders = {f["id"]: f for f in cfg.get("folders", [])}
    for item in FOLDERS_TO_FEDERATE:
        f_id = item["id"]
        # Ensure directory exists on Linux Mini
        mkdir_cmd = f"mkdir -p {item['linux_path']}"
        subprocess.run(["ssh", "-o", "BatchMode=yes", f"linux@{LINUX_MINI_IP}", mkdir_cmd], capture_output=True)

        if f_id in existing_folders:
            folder = existing_folders[f_id]
            dev_ids = {d["deviceID"] for d in folder.get("devices", [])}
            if MAC_MINI_ID not in dev_ids:
                folder.setdefault("devices", []).append({"deviceID": MAC_MINI_ID, "introducedBy": ""})
                print(f"[+] Shared folder '{f_id}' with Mac Mini on Linux Mini")
        else:
            print(f"[+] Registering folder '{f_id}' on Linux Mini at {item['linux_path']}...")
            cfg.setdefault("folders", []).append({
                "id": f_id,
                "label": item["label"],
                "path": item["linux_path"],
                "type": "sendreceive",
                "devices": [
                    {"deviceID": LINUX_MINI_ID, "introducedBy": ""},
                    {"deviceID": MAC_MINI_ID, "introducedBy": ""}
                ],
                "rescanIntervalS": 60,
                "fsWatcherEnabled": True,
                "fsWatcherDelayS": 10,
                "ignorePerms": False,
                "autoNormalize": True
            })

    # Write updated config to Linux Mini
    payload = json.dumps(cfg)
    escaped_payload = payload.replace("'", "'\\''")
    cmd_put = (
        f"curl -s -X PUT -H 'Content-Type: application/json' "
        f"-H 'X-API-Key: {LINUX_MINI_KEY}' -d '{escaped_payload}' "
        f"http://127.0.0.1:8384/rest/config"
    )
    res_put = subprocess.run(["ssh", "-o", "BatchMode=yes", f"linux@{LINUX_MINI_IP}", cmd_put],
                             capture_output=True, text=True, timeout=20)
    print(f"[+] Linux Mini PUT result: returncode={res_put.returncode}")
    return res_put.returncode == 0

def get_cluster_status():
    print("\n================== SYNCTHING MESH CLUSTER STATUS ==================")
    sys_status = syncthing_req(MAC_MINI_API, MAC_MINI_KEY, "/rest/system/status")
    conn_status = syncthing_req(MAC_MINI_API, MAC_MINI_KEY, "/rest/system/connections")
    if not sys_status or not conn_status:
        print("[-] Unable to query cluster status")
        return

    conns = conn_status.get("connections", {})
    devices = {
        MAC_MINI_ID: "Mac-Mini-Host (L1)",
        LINUX_MINI_ID: "Linux-Mini (L3)",
        "LNVQC7N-35SA4QV-PF3QUTH-4SE2ZSX-NAXP5SW-DYDM2E5-MACM7OE-CIXAEAY": "Pixel-10-Pro-XL (L6)",
        "BF6KFOQ-URV74DS-PXCLYCU-A34NV3T-4WJV4IJ-EWQGS4I-K3SQLIQ-5R2ZWA2": "Samsung-Galaxy-S20 (L7)",
        "3WPP5UW-KZNTR2Y-FVK3BEO-E42GE3W-7LWGYW3-VLNIKHW-CHF3SRD-3F5VQAP": "MacBook-Air (L5)",
        "DP2ZXQV-YSMYYKX-TCANKQQ-6SAHL5L-7HDE4OU-LVMOSH7-CDS266U-BGGRBA3": "Gateway Router"
    }

    for dev_id, name in devices.items():
        if dev_id == MAC_MINI_ID:
            print(f"• {name} [{dev_id[:10]}...]: LOCAL HOST (Uptime: {sys_status.get('uptime', 0)}s)")
            continue
        c = conns.get(dev_id)
        if c and c.get("connected"):
            addr = c.get("address", "N/A")
            in_bps = c.get("inBytesTotal", 0) / 1024
            out_bps = c.get("outBytesTotal", 0) / 1024
            print(f"• {name} [{dev_id[:10]}...]: CONNECTED via {addr} (In: {in_bps:.1f} KB, Out: {out_bps:.1f} KB)")
        else:
            print(f"• {name} [{dev_id[:10]}...]: DISCONNECTED / STANDBY")
    print("===================================================================\n")

if __name__ == "__main__":
    mac_ok = configure_mac_mini()
    linux_ok = configure_linux_mini()
    print(f"[+] Federation Setup Result: Mac={mac_ok}, Linux={linux_ok}")
    get_cluster_status()
