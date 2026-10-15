#!/usr/bin/env python3
"""
Screen Lens Sovereign: Canonical Storage Governor
=================================================
Enforces the Universal SeaweedFS and Router Unified Namespace across the Lauburu Mesh.
Manages the unified storage hierarchy (/mnt/lauburu_storage and ~/Network_Storage/Router_Unified),
organizing distributed SeaweedFS DFS and router local flash tiers.
Autonomously sorts incoming telemetry, datasets, biometrics, and captures into canonical directories.
"""
import os
import sys
import json
import shutil
import hashlib
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA256 checksum for data integrity verification."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


class CanonicalStorageGovernor:
    def __init__(self, custom_router_mount: Optional[Path] = None):
        self.mac_mount = Path("/Users/aaron/DFS_UNIFIED")
        self.linux_mount = Path("/mnt/dfs_unified")
        self.router_native_mount = Path("/mnt/lauburu_storage")
        
        # Primary client mount location for unified network storage
        if custom_router_mount:
            self.router_mount = Path(custom_router_mount)
        elif os.environ.get("ROUTER_UNIFIED_MOUNT"):
            self.router_mount = Path(os.environ["ROUTER_UNIFIED_MOUNT"])
        elif self.router_native_mount.exists():
            self.router_mount = self.router_native_mount
        else:
            self.router_mount = Path.home() / "Network_Storage/Router_Unified"

        self.filer_url = "http://100.101.39.98:8888"

        # Define canonical local DFS structure
        self.structure = [
            "core_infrastructure",
            "ai_models",
            "biometrics",
            "lora_datasets",
            "obsidian_vault",
            "edge_mounts/pixel_10_dcim",
            "edge_mounts/samsung_s20_ui"
        ]

        # Define canonical router unified hierarchy
        self.router_dfs_structure = [
            "distributed_dfs/04_data_and_memory",
            "distributed_dfs/lora_datasets",
            "distributed_dfs/obsidian_vault",
            "distributed_dfs/biometrics",
            "distributed_dfs/buckets",
            "distributed_dfs/ai_models"
        ]

        self.router_flash_structure = [
            "local_flash/scratch",
            "local_flash/staging",
            "local_flash/telemetry",
            "local_flash/edge_mounts/pixel_10_dcim",
            "local_flash/edge_mounts/samsung_s20_ui"
        ]

    def enforce_local_structure(self) -> Dict[str, Any]:
        """Validates and provisions canonical local SeaweedFS DFS structure."""
        print("================================================================================")
        print("🗂️ SCREEN LENS: CANONICAL STORAGE GOVERNOR - LOCAL DFS")
        print("================================================================================")

        base = self.mac_mount
        if not base.exists():
            print(f"[!] Warning: Base mount {base} not found. Checking Linux node mount...")
            if self.linux_mount.exists():
                base = self.linux_mount
            else:
                print("[!] Warning: No local DFS mount found. Proceeding with network inspection.")
                return {"healthy": False, "error": "No DFS base mount found"}

        print(f"[*] Validating Canonical Structure at {base}...")
        verified = []
        provisioned = []
        for folder in self.structure:
            target = base / folder
            if not target.exists():
                print(f"  [+] Provisioning missing canonical path: seaweedfs://{folder}")
                target.mkdir(parents=True, exist_ok=True)
                provisioned.append(folder)
            else:
                print(f"  [✓] Verified: seaweedfs://{folder}")
                verified.append(folder)

        return {
            "healthy": True,
            "base": str(base),
            "verified": verified,
            "provisioned": provisioned
        }

    def enforce_router_unified_structure(self) -> Dict[str, Any]:
        """Validates and provisions unified storage hierarchy on router network mount."""
        print("================================================================================")
        print("🌐 SCREEN LENS: ROUTER UNIFIED NETWORK STORAGE GOVERNOR")
        print(f"Target Mount: {self.router_mount}")
        print("================================================================================")

        if not self.router_mount.exists():
            print(f"[!] Router unified mount point does not exist: {self.router_mount}")
            return {"active": False, "error": "Mount point does not exist"}

        # Check if the mount directory is accessible
        is_mounted = (
            (self.router_mount / "distributed_dfs").exists() and 
            (self.router_mount / "local_flash").exists()
        )

        verified = []
        provisioned = []

        if not is_mounted:
            print(f"[!] Warning: Unified storage subdirectories not present at {self.router_mount}.")
            # Attempt to create root subdirs if writable
            try:
                (self.router_mount / "distributed_dfs").mkdir(parents=True, exist_ok=True)
                (self.router_mount / "local_flash").mkdir(parents=True, exist_ok=True)
                is_mounted = True
            except Exception as e:
                print(f"[!] Could not initialize root subdirectories on {self.router_mount}: {e}")
                return {"active": False, "error": str(e)}

        print("[*] Validating Distributed DFS Storage Pool (SeaweedFS 900 GB virtual)...")
        for sub in self.router_dfs_structure:
            target = self.router_mount / sub
            if not target.exists():
                print(f"  [+] Provisioning router DFS path: {sub}")
                target.mkdir(parents=True, exist_ok=True)
                provisioned.append(sub)
            else:
                print(f"  [✓] Verified router DFS path: {sub}")
                verified.append(sub)

        print("[*] Validating Local Flash Storage Pool (eMMC 58 GB F2FS)...")
        for sub in self.router_flash_structure:
            target = self.router_mount / sub
            if not target.exists():
                print(f"  [+] Provisioning router Flash path: {sub}")
                target.mkdir(parents=True, exist_ok=True)
                provisioned.append(sub)
            else:
                print(f"  [✓] Verified router Flash path: {sub}")
                verified.append(sub)

        # Write health check verification token
        token_path = self.router_mount / ".governor_beacon"
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            with open(token_path, "w") as f:
                f.write(f"Screen Lens Storage Governor Active - {now_iso}\n")
            print(f"  [✓] Verified read/write access to unified network mount (beacon: {token_path})")
            writable = True
        except Exception as e:
            print(f"  [!] Write test failed on unified network mount: {e}")
            writable = False

        return {
            "active": True,
            "path": str(self.router_mount),
            "writable": writable,
            "verified": verified,
            "provisioned": provisioned
        }

    def auto_organize_storage(self, source_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Autonomously sorts unorganized telemetry, datasets, biometrics, and media
        from a staging or scratch directory into canonical storage tiers.
        """
        print("\n[*] SCREEN LENS: Autonomous Storage Auto-Organization...")
        
        # Determine source directory
        if source_dir:
            src = Path(source_dir)
        elif (self.router_mount / "local_flash/staging").exists():
            src = self.router_mount / "local_flash/staging"
        elif (self.router_mount / "local_flash/scratch").exists():
            src = self.router_mount / "local_flash/scratch"
        else:
            src = self.router_mount / "staging"

        if not src.exists():
            print(f"  [i] Staging source directory {src} does not exist. Creating staging directory.")
            src.mkdir(parents=True, exist_ok=True)
            return {"organized_count": 0, "items": [], "source": str(src)}

        organized = []
        # Walk source directory (excluding hidden files and subdirectories)
        for item in list(src.iterdir()):
            if item.is_dir() or item.name.startswith("."):
                continue

            name_lower = item.name.lower()
            target_dest: Optional[Path] = None

            # Classification logic based on content type and naming convention
            if name_lower.endswith((".csv", ".bin")) or any(k in name_lower for k in ("ecg", "movesense", "qrs", "biometrics")):
                target_dest = self.router_mount / "distributed_dfs/biometrics"
            elif name_lower.endswith((".parquet",)) or any(k in name_lower for k in ("lora", "dpo", "sft", "dataset", "dataset.jsonl")):
                target_dest = self.router_mount / "distributed_dfs/lora_datasets"
            elif any(k in name_lower for k in ("telemetry", "observation", "ping", "arp", "dhcp", "healer", "beacon")) or (name_lower.endswith(".jsonl") and "lora" not in name_lower):
                target_dest = self.router_mount / "local_flash/telemetry"
            elif name_lower.endswith((".jpg", ".jpeg", ".png", ".mp4", ".webp")):
                if "pixel" in name_lower or "camera" in name_lower or "dcim" in name_lower:
                    target_dest = self.router_mount / "local_flash/edge_mounts/pixel_10_dcim"
                else:
                    target_dest = self.router_mount / "local_flash/edge_mounts/samsung_s20_ui"
            elif name_lower.endswith((".md", ".txt")) and not name_lower.startswith("test"):
                target_dest = self.router_mount / "distributed_dfs/obsidian_vault"

            if target_dest:
                target_dest.mkdir(parents=True, exist_ok=True)
                dest_file = target_dest / item.name

                # Checksum before move
                src_hash = calculate_sha256(item)
                shutil.move(str(item), str(dest_file))
                dest_hash = calculate_sha256(dest_file)

                if src_hash == dest_hash:
                    print(f"  [✓] Auto-Organized: {item.name} -> {target_dest.relative_to(self.router_mount)} (SHA256: {src_hash[:12]}...)")
                    organized.append({
                        "filename": item.name,
                        "source": str(item),
                        "destination": str(dest_file),
                        "sha256": dest_hash
                    })
                else:
                    print(f"  [!] Checksum mismatch for {item.name}! Source: {src_hash} != Dest: {dest_hash}")

        # Update organization log in 04_data_and_memory
        manifest_dir = self.router_mount / "distributed_dfs/04_data_and_memory"
        if manifest_dir.exists() and organized:
            manifest_file = manifest_dir / "storage_auto_organization_log.jsonl"
            with open(manifest_file, "a") as f:
                for entry in organized:
                    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
                    f.write(json.dumps(entry) + "\n")

        print(f"  -> Total files auto-organized: {len(organized)}")
        return {
            "organized_count": len(organized),
            "items": organized,
            "source": str(src)
        }

    def optimize_edge_mounts(self) -> Dict[str, Any]:
        """Optimizes edge device mounts and synchronizes with canonical hierarchies."""
        print("\n[*] Optimizing Edge Device Storage Mounts via EdgeStorageSyncBridge...")
        sync_report = {}
        try:
            # Import and run genuine edge storage synchronization bridge
            bridge_script = Path(__file__).parent / "lens_edge_storage_sync_bridge.py"
            if bridge_script.exists():
                sys.path.insert(0, str(Path(__file__).parent))
                from lens_edge_storage_sync_bridge import EdgeStorageSyncBridge
                storage_target = self.router_mount if self.router_mount.exists() else Path("/Volumes/seaweed_network")
                bridge = EdgeStorageSyncBridge(storage_root=storage_target)
                sync_report = bridge.sync_all_active()
            else:
                print("  [!] Warning: lens_edge_storage_sync_bridge.py not found.")
        except Exception as e:
            print(f"  [!] Edge sync bridge execution notice: {e}")
            sync_report = {"error": str(e)}
        return sync_report

    def get_unified_storage_report(self) -> Dict[str, Any]:
        """Compiles a complete audit report of storage pools across the mesh."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "local_dfs": self.enforce_local_structure(),
            "router_unified": self.enforce_router_unified_structure(),
        }

        if self.router_mount.exists():
            try:
                usage = shutil.disk_usage(self.router_mount)
                report["router_storage_stats"] = {
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent_free": round((usage.free / usage.total) * 100, 1)
                }
            except Exception as e:
                report["router_storage_stats"] = {"error": str(e)}

        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Screen Lens Canonical Storage Governor")
    parser.add_argument("--mount", type=str, default=None, help="Custom router unified mount path")
    parser.add_argument("--source", type=str, default=None, help="Source directory for auto-organization")
    parser.add_argument("--organize-only", action="store_true", help="Only run auto-organization")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    args = parser.parse_args()

    gov = CanonicalStorageGovernor(custom_router_mount=Path(args.mount) if args.mount else None)

    if args.organize_only:
        res = gov.auto_organize_storage(source_dir=Path(args.source) if args.source else None)
        if args.json:
            print(json.dumps(res, indent=2))
    else:
        gov.enforce_local_structure()
        gov.enforce_router_unified_structure()
        gov.auto_organize_storage(source_dir=Path(args.source) if args.source else None)
        gov.optimize_edge_mounts()
        if args.json:
            print(json.dumps(gov.get_unified_storage_report(), indent=2))
