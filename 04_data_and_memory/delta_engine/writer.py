"""
Thread-safe Delta Lake dataset writer with Rust-native delta-rs backend.
Supports ACID appends, micro-batch buffering, schema evolution, and PyArrow integration.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import pyarrow as pa
try:
    import pandas as pd
except ImportError:
    pd = None

from deltalake import DeltaTable, write_deltalake

from .schema import get_schema_by_name, normalize_record, records_to_arrow_table


class DeltaDatasetWriter:
    """
    Thread-safe ACID-compliant dataset writer targeting Delta Lake tables using delta-rs.
    Supports single-record streaming, micro-batch buffering, and bulk table writes.
    """

    def __init__(
        self,
        table_uri: Union[str, Path],
        schema: Optional[pa.Schema] = None,
        schema_name: Optional[str] = None,
        mode: str = "append",
        schema_mode: str = "merge",
        buffer_size: int = 1,
        engine: str = "rust",
        storage_options: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize the DeltaDatasetWriter.

        Args:
            table_uri: Path or URI to the Delta table directory.
            schema: Optional explicit PyArrow schema.
            schema_name: Optional schema name lookup from canonical registry.
            mode: Write mode ('append' or 'overwrite'). Default is 'append'.
            schema_mode: Schema evolution mode ('merge' or 'error'). Default is 'merge'.
            buffer_size: Number of records to buffer before auto-flushing. Default is 1 (immediate).
            engine: Delta engine ('rust' or 'pyarrow'). Default is 'rust'.
            storage_options: Optional storage options dictionary for cloud/filesystem storage.
        """
        self.table_uri = str(Path(table_uri).resolve()) if not str(table_uri).startswith(("s3://", "r2://", "gcs://")) else str(table_uri)
        self.schema = schema or (get_schema_by_name(schema_name) if schema_name else None)
        self.mode = mode
        self.schema_mode = schema_mode
        self.buffer_size = max(1, buffer_size)
        self.engine = engine
        self.storage_options = storage_options or {}

        self._lock = threading.RLock()
        self._buffer: List[Dict[str, Any]] = []
        self._table: Optional[DeltaTable] = None

        # Ensure parent directory exists for local paths
        if not self.table_uri.startswith(("s3://", "r2://", "gcs://")):
            os.makedirs(self.table_uri, exist_ok=True)

    @property
    def table_path(self) -> Path:
        return Path(self.table_uri)

    def write(
        self,
        data: Union[Sequence[Dict[str, Any]], Dict[str, Any], pa.Table, Any],
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Writes data directly to the Delta table with ACID transactional guarantees.

        Args:
            data: Single record dict, list of dicts, PyArrow Table, or pandas DataFrame.
            mode: Optional write mode override ('append' or 'overwrite').

        Returns:
            Dict containing commit metadata: status, version, rows_written, table_uri.
        """
        write_mode = mode or self.mode
        arrow_table: pa.Table

        if isinstance(data, dict):
            arrow_table = records_to_arrow_table([data], schema=self.schema)
        elif isinstance(data, (list, tuple)):
            if len(data) > 0 and isinstance(data[0], dict):
                arrow_table = records_to_arrow_table(data, schema=self.schema)
            else:
                arrow_table = pa.Table.from_pylist(list(data))
        elif isinstance(data, pa.Table):
            arrow_table = data
        elif pd is not None and isinstance(data, pd.DataFrame):
            arrow_table = pa.Table.from_pandas(data, schema=self.schema)
        else:
            raise TypeError(f"Unsupported data type for DeltaDatasetWriter.write: {type(data)}")

        if arrow_table.num_rows == 0:
            return {
                "status": "noop",
                "version": self.get_version(),
                "rows_written": 0,
                "table_uri": self.table_uri,
            }

        with self._lock:
            write_deltalake(
                table_or_uri=self.table_uri,
                data=arrow_table,
                mode=write_mode,
                schema_mode=self.schema_mode,
                storage_options=self.storage_options if self.storage_options else None,
            )

            # Invalidate cached table handle
            self._table = None
            current_version = self.get_version()
            total_rows = self.count_rows()

            return {
                "status": "success",
                "version": current_version,
                "rows_written": arrow_table.num_rows,
                "total_rows": total_rows,
                "table_uri": self.table_uri,
            }

    def append(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Appends a single record to the internal micro-batch buffer.
        Automatically flushes when buffer reaches buffer_size.
        """
        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) >= self.buffer_size:
                return self.flush()
        return None

    def flush(self) -> Optional[Dict[str, Any]]:
        """Flushes any buffered records to the Delta Lake table."""
        with self._lock:
            if not self._buffer:
                return None
            records_to_flush = list(self._buffer)
            self._buffer.clear()
            return self.write(records_to_flush, mode="append")

    def get_table(self) -> Optional[DeltaTable]:
        """Returns the active DeltaTable instance, or None if table does not exist yet."""
        with self._lock:
            if self._table is None:
                try:
                    if DeltaTable.is_deltatable(self.table_uri):
                        self._table = DeltaTable(self.table_uri, storage_options=self.storage_options)
                    else:
                        return None
                except Exception:
                    return None
            return self._table

    def get_version(self) -> int:
        """Returns current Delta table version (-1 if not yet created)."""
        dt = self.get_table()
        return dt.version() if dt is not None else -1

    def count_rows(self) -> int:
        """Returns the total number of rows in the active Delta table."""
        dt = self.get_table()
        if dt is None:
            return 0
        try:
            return dt.to_pyarrow_dataset().count_rows()
        except Exception:
            return len(dt.to_pyarrow_table())

    def close(self) -> None:
        """Flushes remaining records and closes the writer."""
        self.flush()

    def __enter__(self) -> DeltaDatasetWriter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
