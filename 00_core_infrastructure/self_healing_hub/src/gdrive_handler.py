import os
import logging
import subprocess

logger = logging.getLogger(__name__)

class GDriveHandler:
    def __init__(self, remote_name="gdrive", mount_point="/mnt/gdrive_cache"):
        self.remote_name = remote_name
        self.primary_mount_point = mount_point
        # Standard macOS Google Drive client path
        self.native_macos_gdrive = "/Volumes/Google Drive/My Drive/Lauburu_AI_Memory"
        # Dynamic fallback path if /mnt or root is read-only
        self.fallback_mount_point = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache"
        self.mount_point = self.primary_mount_point

    def _resolve_mount_point(self):
        """Resolves a writable mount point, checking native macOS Google Drive first."""
        # 1. Check if native macOS Google Drive directory exists and is accessible
        if os.path.exists(self.native_macos_gdrive) and os.access(self.native_macos_gdrive, os.W_OK):
            self.mount_point = self.native_macos_gdrive
            logger.info(f"Using native macOS Google Drive directory: {self.native_macos_gdrive}")
            return self.native_macos_gdrive

        # 2. Check primary mount point (/mnt/gdrive_cache)
        for path in [self.primary_mount_point, self.fallback_mount_point, "/tmp/lauburu/gdrive_cache"]:
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
        """Check if the Google Drive rclone mount, native macOS Google Drive, or local fallback is active."""
        if os.path.exists(self.native_macos_gdrive) and os.access(self.native_macos_gdrive, os.W_OK):
            return True
        if os.path.ismount(self.mount_point):
            return True
        fallback_dir = self.fallback_mount_point
        return os.path.exists(fallback_dir) and os.access(fallback_dir, os.W_OK)

    def mount(self):
        """Self-healing mount for Google Drive via native macOS path, rclone daemon, or local VFS fallback."""
        target_path = self._resolve_mount_point()
        
        if target_path == self.native_macos_gdrive or os.path.ismount(target_path):
            logger.info(f"Google Drive is active at {target_path}.")
            return True

        # Attempt rclone mount
        cmd = [
            "rclone", "mount", 
            f"{self.remote_name}:", 
            target_path, 
            "--daemon", 
            "--vfs-cache-mode", "full"
        ]
        
        logger.info(f"Attempting rclone mount: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Google Drive mounted successfully at {target_path}.")
                return True
            else:
                logger.warning(f"Rclone mount failed: {result.stderr.strip()}. Initializing self-healing local VFS cache...")
        except FileNotFoundError:
            logger.warning("Rclone binary not found. Initializing self-healing local VFS cache...")

        # Self-healing fallback: ensure local cache directory exists so storage pipeline never crashes
        try:
            os.makedirs(self.fallback_mount_point, exist_ok=True)
            self.mount_point = self.fallback_mount_point
            logger.info(f"[Self-Healing] Active Google Drive VFS fallback directory ready at {self.fallback_mount_point}")
            return True
        except Exception as e:
            logger.error(f"[Self-Healing] Failed to initialize fallback VFS: {e}")
            return False

    def unmount(self):
        """Unmounts the Google Drive rclone mount."""
        logger.info(f"Unmounting {self.mount_point}...")
        result = subprocess.run(["fusermount", "-u", self.mount_point], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        result = subprocess.run(["umount", self.mount_point], capture_output=True, text=True)
        return result.returncode == 0
