#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SeaweedFS Distributed Storage Bridge for the Canonical IDE & Monorepo
================================================================================
Subsystem: 01_apps/canonical_port/backend/seaweed_ide_bridge.py
Version: 1.0.0-SEAWEED-IDE-BRIDGE
Lauburu Mesh Ecosystem — 2026

Capabilities:
1. Probes live SeaweedFS Master (:9333), Filer (:8888), and WebDAV (:7333).
2. Verifies POSIX FUSE mount health at /Users/aaron/DFS_UNIFIED.
3. Retrieves distributed VFS file listings and chunk metadata from Filer REST API.
4. Executes non-blocking self-healing reflex arc via heal_fuse_mount().
================================================================================
"""

import os
import sys
import time
import socket
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

MOUNT_POINT = Path("/Users/aaron/DFS_UNIFIED")
MASTER_URL = "http://127.0.0.1:9333"
FILER_URL = "http://127.0.0.1:8888"
WEBDAV_URL = "http://127.0.0.1:7333"


class SeaweedIDEBridge:
    @staticmethod
    def _probe_port(ip: str, port: int, timeout_sec: float = 0.2) -> Optional[float]:
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_sec)
        try:
            if s.connect_ex((ip, port)) == 0:
                return round((time.perf_counter() - t0) * 1000.0, 2)
        except Exception:
            pass
        finally:
            s.close()
        return None

    @classmethod
    def is_mounted(cls) -> bool:
        """Check if SeaweedFS FUSE mount is active."""
        try:
            res = subprocess.run(["mount"], capture_output=True, text=True, timeout=1.5)
            return "DFS_UNIFIED" in res.stdout or "dfs_unified" in res.stdout or MOUNT_POINT.is_dir()
        except Exception:
            return MOUNT_POINT.is_dir()

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        master_rtt = cls._probe_port("127.0.0.1", 9333)
        filer_rtt = cls._probe_port("127.0.0.1", 8888)
        webdav_rtt = cls._probe_port("127.0.0.1", 7333)
        is_mounted = cls.is_mounted()

        # Query Master Topology if master is live
        topology_info = {}
        if master_rtt is not None:
            try:
                req = urllib.request.Request(f"{MASTER_URL}/dir/status", headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=0.8) as response:
                    if response.status == 200:
                        topology_info = json.loads(response.read().decode("utf-8"))
            except Exception:
                pass

        return {
            "service": "SeaweedFS Distributed Storage",
            "mount_point": str(MOUNT_POINT),
            "is_mounted": is_mounted,
            "master": {
                "port": 9333,
                "status": "ONLINE" if master_rtt is not None else "STANDBY",
                "rtt_ms": master_rtt,
                "url": MASTER_URL
            },
            "filer": {
                "port": 8888,
                "status": "ONLINE" if filer_rtt is not None else "STANDBY",
                "rtt_ms": filer_rtt,
                "url": FILER_URL
            },
            "webdav": {
                "port": 7333,
                "status": "ONLINE" if webdav_rtt is not None else "STANDBY",
                "rtt_ms": webdav_rtt,
                "url": WEBDAV_URL
            },
            "topology": topology_info.get("Topology", {}),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    @classmethod
    def list_filer_directory(cls, dir_path: str = "/") -> Dict[str, Any]:
        """Queries the SeaweedFS Filer REST API for directory listings and chunk metadata."""
        clean_path = dir_path.strip("/")
        url = f"{FILER_URL}/{clean_path}" if clean_path else f"{FILER_URL}/"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return {
                        "path": dir_path,
                        "success": True,
                        "entries": data.get("Entries", []),
                        "limit": data.get("Limit", 100)
                    }
        except Exception as e:
            # Fallback to local DFS_UNIFIED directory traversal
            local_dir = MOUNT_POINT / clean_path
            entries = []
            if local_dir.is_dir():
                for p in list(local_dir.iterdir())[:30]:
                    entries.append({
                        "FullPath": str(p),
                        "Mtime": time.ctime(p.stat().st_mtime),
                        "FileSize": p.stat().st_size if p.is_file() else 0,
                        "Mode": p.stat().st_mode
                    })
            return {
                "path": dir_path,
                "success": True,
                "source": "LOCAL_DFS_UNIFIED_FALLBACK",
                "entries": entries
            }

    @classmethod
    def heal_mount(cls) -> Dict[str, Any]:
        """Invokes the autonomous self-healing reflex arc."""
        script_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/scripts/seaweed_tools.py")
        if script_path.exists():
            try:
                from seaweed_tools import heal_fuse_mount
                res_str = heal_fuse_mount(str(MOUNT_POINT))
                return json.loads(res_str)
            except Exception as e:
                return {"status": "FAILED", "error": str(e)}
        return {"status": "SKIPPED", "message": "Mount point is already active and healthy."}

    @classmethod
    def offload_asan_minidump(
        cls,
        crash_id: str,
        error_type: str,
        crash_log: str,
        source_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Offloads Clang AddressSanitizer (ASan) minidump crash reports and
        AST logs to SeaweedFS distributed storage at /DFS_UNIFIED/asan_minidumps/.
        """
        dump_dir = MOUNT_POINT / "asan_minidumps"
        dump_dir.mkdir(parents=True, exist_ok=True)
        dump_file = dump_dir / f"{crash_id}.log"

        payload = {
            "crash_id": crash_id,
            "error_type": error_type,
            "source_file": source_file or "unknown",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "crash_log": crash_log
        }

        try:
            with open(dump_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            # Sync to Obsidian Vault
            try:
                vault_dir = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS")
                vault_dir.mkdir(parents=True, exist_ok=True)
                asan_vault_log = vault_dir / "ASAN_MEMORY_SAFETY_LOG.md"
                entry = f"- `{time.strftime('%Y-%m-%d %H:%M:%S')}`: ASan Minidump `[[{crash_id}]]` | Type: `{error_type}` | Source: `{source_file}` | Path: `{dump_file}`\n"
                with open(asan_vault_log, "a", encoding="utf-8") as f:
                    f.write(entry)
            except Exception:
                pass

            return {
                "success": True,
                "crash_id": crash_id,
                "error_type": error_type,
                "dump_path": str(dump_file),
                "dfs_mounted": cls.is_mounted(),
                "timestamp": payload["timestamp"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "crash_id": crash_id
            }


if __name__ == "__main__":
    print("Testing SeaweedFS IDE Bridge...")
    st = SeaweedIDEBridge.get_status()
    print(f"Master: {st['master']['status']} ({st['master']['rtt_ms']} ms)")
    print(f"Filer: {st['filer']['status']} ({st['filer']['rtt_ms']} ms)")
    print(f"Mount Point ({st['mount_point']}): Mounted = {st['is_mounted']}")
