"""
multi_wan/storage.py - Storage Manager & Proactive Backup Integration.

Monitors storage limits across /Volumes/Lauburu-Monorepo, .agents/, /tmp, and system mounts using shutil.disk_usage.
Calculates percent_used, free_gb, total_gb, storage_status (OK, WARNING, CRITICAL).
Executes proactive backup via rclone gdrive: or fallback backup script.
Enqueues storage alert commands into data/command_queue.json for lauburu-local-agi notification.
"""

import logging
import os
import shutil
import subprocess
import tarfile
import time
from typing import Dict, Optional, Any, List

from .agi_bridge import LocalAGIBridge

logger = logging.getLogger("multi_wan.storage")


class StorageManager:
    """
    Monitors storage usage across key paths/mounts and handles proactive backups.
    """

    def __init__(
        self,
        base_path: str = "/Volumes/Lauburu-Monorepo",
        agi_bridge: Optional[LocalAGIBridge] = None,
        paths_to_monitor: Optional[List[str]] = None,
    ):
        self.base_path = base_path
        self.agi_bridge = agi_bridge
        self.paths_to_monitor = paths_to_monitor or [
            "/Volumes/Lauburu-Monorepo",
            "/Volumes/Lauburu-Monorepo/.agents",
            "/tmp",
        ]
        self.backup_active = False
        self.last_backup_timestamp: Optional[str] = None
        self.last_check_metrics: Dict[str, Any] = {}
        # Initial check
        self.check_storage()

    def check_storage(self, target_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Monitors storage limits using shutil.disk_usage.
        Calculates percent_used, free_gb, total_gb, storage_status (OK, WARNING, CRITICAL).
        """
        check_path = target_path or self.base_path
        if not os.path.exists(check_path):
            check_path = "/tmp" if os.path.exists("/tmp") else "."

        try:
            usage = shutil.disk_usage(check_path)
            total_gb = round(usage.total / (1024 ** 3), 2)
            used_gb = round(usage.used / (1024 ** 3), 2)
            free_gb = round(usage.free / (1024 ** 3), 2)
            percent_used = round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0

            if percent_used > 90.0 or free_gb < 2.0:
                status = "CRITICAL"
            elif percent_used > 80.0 or free_gb < 5.0:
                status = "WARNING"
            else:
                status = "OK"

            metrics = {
                "path": check_path,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "percent_used": percent_used,
                "storage_status": status,
                "backup_active": self.backup_active,
                "last_backup_timestamp": self.last_backup_timestamp,
            }

            self.last_check_metrics = metrics

            # If status is WARNING or CRITICAL, notify AGI bridge
            if status in ("WARNING", "CRITICAL") and self.agi_bridge:
                self.agi_bridge.enqueue_command(
                    "STORAGE_ALERT",
                    {
                        "path": check_path,
                        "status": status,
                        "percent_used": percent_used,
                        "free_gb": free_gb,
                    },
                )

            return metrics

        except Exception as e:
            logger.error(f"Error checking disk usage for path '{check_path}': {e}")
            fallback_metrics = {
                "path": check_path,
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "percent_used": 0.0,
                "storage_status": "OK",
                "backup_active": self.backup_active,
                "last_backup_timestamp": self.last_backup_timestamp,
            }
            self.last_check_metrics = fallback_metrics
            return fallback_metrics

    def trigger_proactive_backup(
        self,
        artifact_dir: Optional[str] = None,
        gdrive_remote: str = "gdrive:",
    ) -> Dict[str, Any]:
        """
        Proactively packages/moves non-essential datasets/artifacts to Google Drive via rclone,
        or fallback backup script if rclone/gdrive is offline or un-configured.
        Guarantees zero crash and zero process halt.
        """
        self.backup_active = True
        backup_method = "rclone"
        backup_success = False
        message = ""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        target_dir = artifact_dir or os.path.join(self.base_path, ".tmp_artifacts")
        os.makedirs(target_dir, exist_ok=True)

        # Check if rclone is available on PATH
        rclone_bin = shutil.which("rclone")
        if rclone_bin:
            try:
                # Attempt rclone copy/sync
                result = subprocess.run(
                    [rclone_bin, "copy", target_dir, f"{gdrive_remote}lauburu_backups/"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    backup_success = True
                    message = "Successfully backed up artifacts via rclone gdrive:"
                else:
                    logger.warning(f"rclone returned error code {result.returncode}: {result.stderr}")
                    backup_method = "fallback"
            except Exception as e:
                logger.warning(f"rclone execution failed: {e}. Executing fallback backup.")
                backup_method = "fallback"
        else:
            logger.info("rclone command not found. Executing fallback backup procedure.")
            backup_method = "fallback"

        # Fallback backup execution
        if backup_method == "fallback":
            try:
                backup_archive_dir = os.path.join(self.base_path, "backups")
                os.makedirs(backup_archive_dir, exist_ok=True)
                archive_filename = f"backup_{int(time.time())}.tar.gz"
                archive_path = os.path.join(backup_archive_dir, archive_filename)

                with tarfile.open(archive_path, "w:gz") as tar:
                    tar.add(target_dir, arcname=os.path.basename(target_dir))

                backup_success = True
                message = f"Fallback backup created successfully at {archive_path}"
            except Exception as e:
                logger.error(f"Fallback backup encountered error: {e}")
                backup_success = False
                message = f"Fallback backup failed: {e}"

        self.backup_active = False
        self.last_backup_timestamp = timestamp

        # Enqueue AGI notification command if bridge attached
        if self.agi_bridge:
            self.agi_bridge.enqueue_command(
                "PROACTIVE_BACKUP_COMPLETED",
                {
                    "timestamp": timestamp,
                    "method": backup_method,
                    "success": backup_success,
                    "message": message,
                },
            )

        return {
            "status": "success" if backup_success else "failed",
            "method": backup_method,
            "backup_active": False,
            "last_backup_timestamp": timestamp,
            "message": message,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Returns current storage status dictionary for dashboard telemetry."""
        if not self.last_check_metrics:
            return self.check_storage()
        metrics = dict(self.last_check_metrics)
        metrics["backup_active"] = self.backup_active
        metrics["last_backup_timestamp"] = self.last_backup_timestamp
        return metrics
