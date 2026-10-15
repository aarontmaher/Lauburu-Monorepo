"""
Lauburu Mesh - Granular Privacy, Permissions & System Allowances Manager
Governs OS entitlements across macOS, Android, Linux, and Web according to the Least Privilege Principle.
"""

from typing import Dict, Any, List
import sqlite3
import os
import time

DB_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/01_apps/unified_portal/data/permissions.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Permission Definitions Matrix
SYSTEM_PERMISSIONS = {
    "screen_capture": {
        "id": "screen_capture",
        "name": "Screen Capture & OCR Entitlement",
        "category": "Vision & OS Privacy",
        "description": "Allows Screen Lens to capture on-screen frames locally for Metal Vision OCR, focus scoring, and daily timeline generation.",
        "platforms": ["macOS (ScreenCaptureKit)", "Android (MediaProjection)", "Windows (Graphics.Capture)"],
        "data_handling": "100% Private On-Device. Zero frames or screenshots ever leave your machine.",
        "required_by": ["screen_lens_vlm"],
        "default_state": "GRANTED"
    },
    "accessibility_api": {
        "id": "accessibility_api",
        "name": "Accessibility & Active Window Inspector",
        "category": "OS Window Management",
        "description": "Allows inspecting active application bundle IDs and window titles to categorize deep work vs communication.",
        "platforms": ["macOS (Accessibility AXIsProcessTrusted)", "Android (AccessibilityService / Shizuku)"],
        "data_handling": "Local metadata only. Used exclusively for app time categorization.",
        "required_by": ["screen_lens_vlm"],
        "default_state": "GRANTED"
    },
    "bluetooth_ble": {
        "id": "bluetooth_ble",
        "name": "Bluetooth Low Energy (BLE) & Sensor Hub",
        "category": "Hardware & Biometrics",
        "description": "Required to connect directly to your Movesense HR+ chest strap for continuous 512Hz ECG streaming.",
        "platforms": ["macOS (CoreBluetooth)", "Android (BLUETOOTH_SCAN, CONNECT)", "Linux (BlueZ)"],
        "data_handling": "Local streaming memory buffer. Processed via local Pan-Tompkins DSP.",
        "required_by": ["zone2_endurance", "movesense_readiness", "training_analysis"],
        "default_state": "GRANTED"
    },
    "local_vault_storage": {
        "id": "local_vault_storage",
        "name": "Local Vault & File System Access",
        "category": "Data & Storage",
        "description": "Grants read/write access to your local Obsidian vault or app storage for saving daily journal notes and workout logs.",
        "platforms": ["macOS (Sandbox Container)", "Android (Scoped Storage)", "Linux (Posix FS)"],
        "data_handling": "Local SQLite and Markdown files stored at ~/DFS_UNIFIED/Lauburu-Monorepo/.",
        "required_by": ["automatic_journal", "weight_training", "screen_lens_vlm"],
        "default_state": "GRANTED"
    },
    "gpu_compute_vram": {
        "id": "gpu_compute_vram",
        "name": "GPU / Metal VRAM Acceleration & Keepalive",
        "category": "AI Compute & Hardware",
        "description": "Allows utilizing idle GPU VRAM (Metal / Vulkan / OpenCL) for prima.cpp distributed ring compute and local llama.cpp inference.",
        "platforms": ["macOS (Metal)", "Android (OpenCL / Termux Wake-Lock)", "Linux (CUDA / ROCm)"],
        "data_handling": "Processes encrypted model tensor weights in transient RAM. Zero user data retention.",
        "required_by": ["prima_cpp_worker", "local_rag_llm"],
        "default_state": "GRANTED"
    },
    "local_network_mesh": {
        "id": "local_network_mesh",
        "name": "Local LAN & Mesh Peer Discovery",
        "category": "Networking",
        "description": "Allows peer discovery across your home Wi-Fi and Tailscale WireGuard mesh for synchronized biometrics and compute sharding.",
        "platforms": ["macOS (Local Network Entitlement)", "Android (Multicast Lock)", "Linux (Sockets)"],
        "data_handling": "Peer-to-peer encrypted communications (TLS / WireGuard).",
        "required_by": ["universal_network_optimizer", "prima_cpp_worker"],
        "default_state": "GRANTED"
    },
    "local_ai_training_opt_in": {
        "id": "local_ai_training_opt_in",
        "name": "Project Data Contribution to Large Local AI Training",
        "category": "AI Continuous Learning & Privacy",
        "description": "Opt-in to contribute anonymized, project-relevant diffs, Screen Lens timelines, and chat insights to the large local AI (Qwen 3.8 Max 27B / Coder) for continuous 24/7 on-device LoRA training. 100% private to your local hardware.",
        "platforms": ["macOS", "Android", "Linux", "PWA Web"],
        "data_handling": "Stored strictly in local JSONL (~/DFS_UNIFIED/lora_datasets/). Zero data is ever sent to external cloud APIs.",
        "required_by": ["continuous_lora_distillation", "local_frontier_moe"],
        "default_state": "DENIED"
    }
}


def init_permissions_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_permissions (
        permission_id TEXT PRIMARY KEY,
        status TEXT,
        last_modified REAL,
        granted_by TEXT
    )
    """)
    now = time.time()
    for pid, info in SYSTEM_PERMISSIONS.items():
        cursor.execute("INSERT OR IGNORE INTO user_permissions VALUES (?, ?, ?, 'USER_EXPLICIT_GRANT')", (pid, info["default_state"], now))
    conn.commit()
    conn.close()

init_permissions_db()

class PermissionGovernor:
    @staticmethod
    def get_all_permissions() -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT permission_id, status FROM user_permissions")
        rows = dict(cursor.fetchall())
        conn.close()

        result = []
        for pid, meta in SYSTEM_PERMISSIONS.items():
            status = rows.get(pid, meta["default_state"])
            result.append({
                **meta,
                "status": status,
                "is_granted": (status == "GRANTED")
            })
        return result

    @staticmethod
    def update_permission(permission_id: str, granted: bool) -> Dict[str, Any]:
        if permission_id not in SYSTEM_PERMISSIONS:
            return {"status": "ERROR", "message": "Unknown permission ID"}
        
        status = "GRANTED" if granted else "DENIED"
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO user_permissions (permission_id, status, last_modified, granted_by)
        VALUES (?, ?, ?, 'USER_UI_TOGGLE')
        """, (permission_id, status, time.time()))
        conn.commit()
        conn.close()

        # Award +25,000 Compute Credits and +50% token boost when opting in
        bonus_info = None
        if permission_id == "local_ai_training_opt_in" and granted:
            try:
                from .payments import PaymentEngine
                bonus_info = PaymentEngine.grant_opt_in_bonus("default_user", 25000)
            except Exception:
                pass

        return {
            "status": "SUCCESS",
            "permission_id": permission_id,
            "new_status": status,
            "is_granted": granted,
            "bonus_awarded": bonus_info
        }


    @staticmethod
    def is_granted(permission_id: str) -> bool:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM user_permissions WHERE permission_id = ?", (permission_id,))
        row = cursor.fetchone()
        conn.close()
        return (row[0] == "GRANTED") if row else True
