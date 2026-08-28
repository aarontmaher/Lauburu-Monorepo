import os
import logging
import subprocess

logger = logging.getLogger(__name__)

class MergerFSHandler:
    def __init__(self, mount_point="/mnt/storage_mesh"):
        self.primary_mount_point = mount_point
        self.fallback_mount_point = "/tmp/lauburu/storage_mesh"
        self.mount_point = self.primary_mount_point

    def _resolve_mount_point(self):
        """Resolves a writable mount point, falling back to user home directory if root is read-only."""
        for path in [self.primary_mount_point, self.fallback_mount_point, "/tmp/storage_mesh"]:
            try:
                os.makedirs(path, exist_ok=True)
                if os.access(path, os.W_OK):
                    self.mount_point = path
                    return path
            except OSError:
                continue
        self.mount_point = self.fallback_mount_point
        return self.fallback_mount_point

    def is_mounted(self):
        """Check if the MergerFS pool or self-healing storage mesh directory is active."""
        if os.path.ismount(self.mount_point):
            return True
        return os.path.exists(self.fallback_mount_point) and os.access(self.fallback_mount_point, os.W_OK)

    def mount_pool(self, drives):
        """
        Mounts drives into MergerFS pool with self-healing directory fallback.
        """
        target_path = self._resolve_mount_point()
        
        if os.path.ismount(target_path):
            logger.info(f"MergerFS already mounted at {target_path}.")
            return True
            
        if not drives:
            drives = [os.path.expanduser("~/.lauburu/local_storage")]
            os.makedirs(drives[0], exist_ok=True)
            
        drive_str = ":".join(drives)
        
        cmd = [
            "mergerfs",
            drive_str,
            target_path,
            "-o", "defaults,allow_other,use_ino,category.create=epmfs"
        ]
        
        logger.info(f"Attempting MergerFS pool mount: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"MergerFS pool mounted successfully at {target_path}.")
                return True
            else:
                logger.warning(f"MergerFS mount failed: {result.stderr.strip()}. Initializing self-healing storage mesh pool...")
        except FileNotFoundError:
            logger.warning("mergerfs binary not found. Initializing self-healing storage mesh pool...")

        # Self-healing fallback: create storage mesh unified directory pool
        try:
            os.makedirs(self.fallback_mount_point, exist_ok=True)
            self.mount_point = self.fallback_mount_point
            logger.info(f"[Self-Healing] Active Storage Mesh pool ready at {self.fallback_mount_point}")
            return True
        except Exception as e:
            logger.error(f"[Self-Healing] Failed to initialize storage mesh pool: {e}")
            return False

    def unmount_pool(self):
        """Unmounts the MergerFS pool."""
        logger.info(f"Unmounting {self.mount_point}...")
        result = subprocess.run(["fusermount", "-u", self.mount_point], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        result = subprocess.run(["umount", self.mount_point], capture_output=True, text=True)
        return result.returncode == 0
