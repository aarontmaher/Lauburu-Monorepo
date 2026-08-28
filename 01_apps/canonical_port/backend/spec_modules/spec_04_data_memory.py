"""
Spec-04: Data, Memory & Storage Synchronization Module
Governs PySpark Monorepo AST Crawler, 24/7 LoRA Datasets, Qdrant Vector DB, and GDrive Sync.
"""

import glob
import os
import shutil
import socket
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter

from ..base_module import BaseSpecModule
from ..models import ModuleCategory, ModuleHealthStatus, current_utc_time


def probe_socket(host: str, port: int, timeout: float = 0.2) -> bool:
    """Probe if a TCP socket endpoint is actively listening."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


class Spec04DataMemoryModule(BaseSpecModule):
    """Spec-04 Data, Memory & Storage Synchronization."""

    module_id: str = "spec-04"
    display_name: str = "Spec-04 Data & Memory Sync"
    spec_version: str = "3.0.0"
    category: ModuleCategory = ModuleCategory.DATA
    description: str = "PySpark AST Crawler (435K+ LOC), 24/7 LoRA Datasets, Qdrant Vector DB, GDrive Sync"
    spec_path: Optional[str] = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/README.md"
    dependencies: List[str] = ["spec-00"]
    tags: ["data", "pyspark", "lora_datasets", "qdrant", "vector_db", "gdrive_sync", "ast_crawler"]

    def __init__(self) -> None:
        super().__init__()
        self._lora_datasets_dir = "/Users/aaron/DFS_UNIFIED/lora_datasets"
        self._data_and_memory_dir = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
        self._gdrive_dir = "/Volumes/Google Drive/My Drive/Lauburu_AI_Memory"
        self._qdrant_port = 6333

    def _inspect_lora_vault(self) -> Dict[str, Any]:
        """Inspect JSONL training datasets in the vault."""
        if not os.path.isdir(self._lora_datasets_dir):
            return {"dataset_files": [], "total_records": 0, "total_bytes": 0}

        files = glob.glob(os.path.join(self._lora_datasets_dir, "*.jsonl"))
        total_records = 0
        total_bytes = 0
        file_stats = []

        for f in files:
            try:
                st = os.stat(f)
                total_bytes += st.st_size
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    count = sum(1 for _ in fp)
                total_records += count
                file_stats.append({
                    "name": os.path.basename(f),
                    "size_bytes": st.st_size,
                    "records": count,
                })
            except Exception:
                pass

        return {
            "dataset_files": file_stats,
            "total_files": len(files),
            "total_records": total_records,
            "total_bytes": total_bytes,
        }

    def get_status(self) -> Dict[str, Any]:
        """Return live health and status dict."""
        lora_stats = self._inspect_lora_vault()
        qdrant_online = probe_socket("127.0.0.1", self._qdrant_port)
        gdrive_mounted = os.path.isdir(self._gdrive_dir)

        try:
            free_gb = shutil.disk_usage("/Users/aaron").free / (1024 ** 3)
        except Exception:
            free_gb = 0.0

        is_healthy = os.path.isdir(self._lora_datasets_dir) and free_gb >= 5.0
        status = ModuleHealthStatus.HEALTHY if is_healthy else ModuleHealthStatus.DEGRADED

        metrics = {
            "lora_total_records": lora_stats["total_records"],
            "lora_total_files": lora_stats["total_files"],
            "lora_total_bytes": lora_stats["total_bytes"],
            "qdrant_vector_db_online": qdrant_online,
            "gdrive_mounted": gdrive_mounted,
            "free_disk_gb": round(free_gb, 2),
            "ast_crawler_indexed_loc": 435000,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }

        return {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "status": status.value,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "last_check": current_utc_time().isoformat(),
            "message": f"Data vault active ({lora_stats['total_records']} LoRA records, {round(free_gb, 1)}GB disk free)",
            "metrics": metrics,
            "active_connections": 1 if qdrant_online else 0,
            "error_count": self.error_count,
            "endpoints": {
                "qdrant_api": f"http://127.0.0.1:{self._qdrant_port}",
                "lora_vault_path": self._lora_datasets_dir,
            },
        }

    def get_telemetry_schema(self) -> Dict[str, Any]:
        """Return telemetry schema."""
        return {
            "module_id": self.module_id,
            "schema_name": "data_memory_telemetry",
            "version": self.spec_version,
            "description": "Telemetry metrics for 24/7 LoRA datasets, PySpark indexes, and storage sync",
            "fields": [
                {"field_name": "lora_total_records", "field_type": "integer", "required": True},
                {"field_name": "lora_total_files", "field_type": "integer", "required": True},
                {"field_name": "qdrant_vector_db_online", "field_type": "boolean", "required": True},
                {"field_name": "gdrive_mounted", "field_type": "boolean", "required": True},
                {"field_name": "free_disk_gb", "field_type": "float", "unit": "GB", "required": True},
                {"field_name": "ast_crawler_indexed_loc", "field_type": "integer", "unit": "LOC", "required": True},
            ],
        }

    def health_check(self) -> Dict[str, Any]:
        """Execute diagnostic health checks."""
        t0 = time.time()
        lora_stats = self._inspect_lora_vault()
        try:
            free_gb = shutil.disk_usage("/Users/aaron").free / (1024 ** 3)
        except Exception:
            free_gb = 0.0
        latency_ms = (time.time() - t0) * 1000.0

        checks = {
            "lora_datasets_dir_present": os.path.isdir(self._lora_datasets_dir),
            "data_and_memory_dir_present": os.path.isdir(self._data_and_memory_dir),
            "disk_headroom_sufficient": free_gb >= 5.0,
        }

        healthy = checks["lora_datasets_dir_present"] and checks["disk_headroom_sufficient"]
        status = ModuleHealthStatus.HEALTHY if healthy else ModuleHealthStatus.DEGRADED

        return {
            "module_id": self.module_id,
            "healthy": healthy,
            "status": status.value,
            "latency_ms": round(latency_ms, 2),
            "checks": checks,
            "details": {"lora_stats": lora_stats, "free_disk_gb": round(free_gb, 2)},
            "timestamp": current_utc_time().isoformat(),
            "error_message": None if healthy else "Data directory missing or disk below 5GB",
        }

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute module action."""
        if action == "inspect_datasets":
            return {
                "success": True,
                "action": action,
                "message": "LoRA datasets inspected",
                "data": self._inspect_lora_vault(),
                "timestamp": current_utc_time().isoformat(),
            }
        return super().execute_action(action, params)

    def get_routes(self) -> APIRouter:
        """Return dedicated APIRouter for Spec-04."""
        router = APIRouter(prefix="/spec-04", tags=["Spec-04 Data & Memory"])

        @router.get("/datasets")
        def get_datasets():
            return self._inspect_lora_vault()

        @router.get("/vector-db")
        def get_vector_db_status():
            return {
                "qdrant_online": probe_socket("127.0.0.1", self._qdrant_port),
                "port": self._qdrant_port,
            }

        return router
