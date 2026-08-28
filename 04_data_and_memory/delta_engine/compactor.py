"""
Automated Delta Lake compaction and optimization engine.
Bin-packs small Parquet files into optimal 64MB-128MB chunks, executes Z-Ordering clustering,
and runs transactional VACUUM cleanup.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from deltalake import DeltaTable


class DeltaCompactor:
    """
    Manages compaction, Z-Ordering, and VACUUM pruning on Delta Lake tables.
    Prevents storage fragmentation and small-file proliferation during 24/7 continuous data ingestion.
    """

    def __init__(
        self,
        table_uri: Union[str, Path],
        storage_options: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize the DeltaCompactor.

        Args:
            table_uri: Path or URI to the Delta table.
            storage_options: Optional storage backend options.
        """
        self.table_uri = str(Path(table_uri).resolve()) if not str(table_uri).startswith(("s3://", "r2://", "gcs://")) else str(table_uri)
        self.storage_options = storage_options or {}

    def get_table(self) -> DeltaTable:
        """Loads and returns the DeltaTable instance."""
        if not DeltaTable.is_deltatable(self.table_uri):
            raise FileNotFoundError(f"No valid Delta table found at {self.table_uri}")
        return DeltaTable(self.table_uri, storage_options=self.storage_options)

    def get_stats(self) -> Dict[str, Any]:
        """
        Computes table statistics including file count, sizes, version, and active files.
        """
        dt = self.get_table()
        files = dt.file_uris()
        total_bytes = 0

        # Sum file sizes if accessible locally
        for fpath in files:
            if os.path.exists(fpath):
                total_bytes += os.path.getsize(fpath)

        return {
            "table_uri": self.table_uri,
            "version": dt.version(),
            "file_count": len(files),
            "total_bytes": total_bytes,
            "files": files,
        }

    def compact(
        self,
        target_size_bytes: int = 128 * 1024 * 1024,
        max_file_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Bin-packs small Parquet ingestion files into target chunk sizes (e.g. 64MB-128MB).

        Args:
            target_size_bytes: Target file size in bytes (default 128MB).
            max_file_size: Optional upper limit for file size.

        Returns:
            Dictionary containing compaction results and file metrics.
        """
        dt = self.get_table()
        version_before = dt.version()
        files_before = len(dt.file_uris())

        # Execute Rust-native Delta Lake compaction optimization
        compact_kwargs: Dict[str, Any] = {"target_size": target_size_bytes}
        if max_file_size is not None:
            compact_kwargs["max_file_size"] = max_file_size

        metrics = dt.optimize.compact(**compact_kwargs)

        # Refresh table state
        dt = self.get_table()
        version_after = dt.version()
        files_after = len(dt.file_uris())

        return {
            "status": "success",
            "table_uri": self.table_uri,
            "version_before": version_before,
            "version_after": version_after,
            "files_before": files_before,
            "files_after": files_after,
            "files_reduced": max(0, files_before - files_after),
            "metrics": metrics,
        }

    def z_order(self, columns: Sequence[str]) -> Dict[str, Any]:
        """
        Executes multidimensional Z-Ordering clustering along specified columns.
        Accelerates predicate pushdown queries.

        Args:
            columns: List of column names to Z-Order by.

        Returns:
            Dictionary containing optimization metrics.
        """
        if not columns:
            raise ValueError("Must specify at least one column for Z-Ordering")

        dt = self.get_table()
        version_before = dt.version()
        metrics = dt.optimize.z_order(columns=list(columns))

        dt = self.get_table()
        version_after = dt.version()

        return {
            "status": "success",
            "table_uri": self.table_uri,
            "z_order_columns": list(columns),
            "version_before": version_before,
            "version_after": version_after,
            "metrics": metrics,
        }

    def vacuum(
        self,
        retention_hours: int = 24,
        enforce_retention_duration: bool = False,
        dry_run: bool = False,
    ) -> List[str]:
        """
        Purges obsolete / tombstoned Parquet files older than retention period.

        Args:
            retention_hours: Number of hours to retain historical files.
            enforce_retention_duration: If False, allows retention < 168 hours.
            dry_run: If True, lists files that would be deleted without deleting.

        Returns:
            List of deleted file paths.
        """
        dt = self.get_table()
        deleted_files = dt.vacuum(
            retention_hours=retention_hours,
            enforce_retention_duration=enforce_retention_duration,
            dry_run=dry_run,
        )
        return list(deleted_files)

    @classmethod
    def compact_all(
        cls,
        table_uris: Sequence[Union[str, Path]],
        target_size_bytes: int = 128 * 1024 * 1024,
    ) -> List[Dict[str, Any]]:
        """Batch compacts multiple Delta tables."""
        results = []
        for uri in table_uris:
            try:
                compactor = cls(uri)
                res = compactor.compact(target_size_bytes=target_size_bytes)
                results.append(res)
            except Exception as e:
                results.append({
                    "status": "error",
                    "table_uri": str(uri),
                    "error": str(e),
                })
        return results
