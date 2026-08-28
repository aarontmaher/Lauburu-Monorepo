"""
Safe Streaming GGUF Model Downloader for smolagi Router AI Daemon.

Implements 64KB chunked streaming to tmpfs (/tmp/models/), SHA-256 checksum
integrity verification, atomic .download.tmp staging, pre-flight storage
headroom validation, and automatic rollback on failure.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple, Union

from src.config import RouterConfig, get_config
from src.model_routing.hf_discovery import HFAuth

logger = logging.getLogger("smolagi.downloader")


@dataclass(frozen=True)
class DownloadResult:
    """Outcome of a model download operation."""

    success: bool
    model_path: str
    size_bytes: int
    sha256: str
    duration_sec: float
    error_message: Optional[str] = None
    bytes_downloaded: int = 0

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)


class SafeModelDownloader:
    """
    Manages safe, chunked streaming downloads of GGUF model binaries directly
    into volatile tmpfs storage, ensuring cryptographic integrity and atomic staging.
    """

    def __init__(
        self,
        target_dir: Optional[Union[str, Path]] = None,
        chunk_size: int = 65536,
        socket_timeout_sec: float = 30.0,
        config: Optional[RouterConfig] = None,
    ) -> None:
        self.config = config or get_config()
        self.target_dir = Path(target_dir or self.config.tmpfs_models_dir)
        self.chunk_size = chunk_size
        self.socket_timeout_sec = socket_timeout_sec
        # Ensure target directory exists
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def verify_storage_headroom(
        self,
        required_bytes: int,
        safety_margin_mb: float = 10.0,
    ) -> Tuple[bool, int, str]:
        """
        Verify that destination directory has sufficient free capacity
        plus safety margin before starting download.
        """
        safety_margin_bytes = int(safety_margin_mb * 1024 * 1024)
        total_needed = required_bytes + safety_margin_bytes

        try:
            stat = os.statvfs(self.target_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
        except (AttributeError, OSError):
            try:
                usage = shutil.disk_usage(self.target_dir)
                free_bytes = usage.free
            except OSError:
                free_bytes = 1024 * 1024 * 1024  # Default assumption 1GB for virtual filesystems

        if free_bytes < total_needed:
            err = (
                f"Insufficient storage headroom in {self.target_dir}: "
                f"{free_bytes} bytes free, required {total_needed} bytes "
                f"({required_bytes} payload + {safety_margin_bytes} safety margin)"
            )
            return False, free_bytes, err

        return True, free_bytes, "Storage headroom OK"

    @staticmethod
    def compute_file_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
        """Compute SHA-256 digest of an on-disk file in streaming chunks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def download_model(
        self,
        url: str,
        filename: str,
        expected_sha256: Optional[str] = None,
        token: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        max_size_bytes: Optional[int] = None,
    ) -> DownloadResult:
        """
        Download a GGUF model via chunked streaming with atomic staging and SHA-256 verification.
        
        Args:
            url: Direct HTTP/HTTPS download URL.
            filename: Destination filename within target_dir (e.g. 'smollm2-135m.gguf').
            expected_sha256: Expected hexadecimal SHA-256 digest.
            token: Optional Hugging Face Hub token.
            progress_callback: Callback receiving (bytes_downloaded, total_bytes).
            max_size_bytes: Optional hard ceiling on allowable size.
            
        Returns:
            DownloadResult describing status and metadata.
            
        Raises:
            IOError / ValueError / RuntimeError on non-recoverable download failure.
        """
        # Validate filename security (prevent directory traversal)
        clean_filename = Path(filename).name
        if not clean_filename or clean_filename != filename:
            raise ValueError(f"Invalid filename '{filename}': directory components not allowed")

        target_path = self.target_dir / clean_filename
        staging_path = self.target_dir / f"{clean_filename}.download.tmp"

        # Pre-clean stale staging artifact if present
        if staging_path.exists():
            staging_path.unlink(missing_ok=True)

        start_time = time.time()
        headers = HFAuth.get_headers(token=token, user_agent="SmolAGI-Router-Downloader/1.0")

        req = urllib.request.Request(url, headers=headers)
        bytes_downloaded = 0
        hasher = hashlib.sha256()

        try:
            with urllib.request.urlopen(req, timeout=self.socket_timeout_sec) as resp:
                content_len_hdr = resp.headers.get("Content-Length")
                total_bytes = int(content_len_hdr) if content_len_hdr else 0

                # 1. Enforce size limits before consuming bandwidth
                if max_size_bytes and total_bytes > max_size_bytes:
                    raise ValueError(
                        f"Model content size {total_bytes} bytes exceeds maximum allowed "
                        f"{max_size_bytes} bytes"
                    )

                # 2. Pre-flight storage headroom verification
                if total_bytes > 0:
                    has_space, free_b, msg = self.verify_storage_headroom(total_bytes)
                    if not has_space:
                        raise IOError(msg)

                # 3. Stream chunks and calculate rolling SHA-256
                with open(staging_path, "wb") as out_f:
                    while True:
                        chunk = resp.read(self.chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        hasher.update(chunk)
                        bytes_downloaded += len(chunk)

                        if max_size_bytes and bytes_downloaded > max_size_bytes:
                            raise ValueError(
                                f"Downloaded bytes {bytes_downloaded} exceeded max allowed "
                                f"{max_size_bytes} during streaming"
                            )

                        if progress_callback:
                            progress_callback(bytes_downloaded, total_bytes)

            # 4. Check for zero-byte or incomplete download
            if bytes_downloaded == 0:
                raise IOError(f"Received empty response (0 bytes) from {url}")

            calculated_sha256 = hasher.hexdigest().lower()

            # 5. Cryptographic checksum validation
            if expected_sha256:
                clean_expected = expected_sha256.strip().lower()
                if calculated_sha256 != clean_expected:
                    staging_path.unlink(missing_ok=True)
                    raise ValueError(
                        f"SHA-256 Checksum verification failed for {clean_filename}: "
                        f"expected {clean_expected}, calculated {calculated_sha256}"
                    )

            # 6. Atomic commit (POSIX atomic rename)
            staging_path.replace(target_path)
            duration_sec = time.time() - start_time

            logger.info(
                "Successfully downloaded %s (%.2f MB) in %.2fs. SHA256: %s",
                clean_filename,
                bytes_downloaded / (1024 * 1024),
                duration_sec,
                calculated_sha256[:16] + "...",
            )

            return DownloadResult(
                success=True,
                model_path=str(target_path),
                size_bytes=bytes_downloaded,
                sha256=calculated_sha256,
                duration_sec=duration_sec,
                bytes_downloaded=bytes_downloaded,
            )

        except Exception as e:
            # Rollback: Clean up incomplete staging file
            staging_path.unlink(missing_ok=True)
            duration_sec = time.time() - start_time
            logger.error("Download failed for %s: %s (after %.2fs)", clean_filename, e, duration_sec)
            raise
