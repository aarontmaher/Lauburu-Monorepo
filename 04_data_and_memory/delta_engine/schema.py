"""
Canonical PyArrow and Delta Lake schemas for Lauburu Monorepo.
Defines schemas for TruthAudit, SFT Training, DPO Preference Pairs, and Mesh Telemetry Streams.
"""
from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional, Sequence, Union
import pyarrow as pa


TRUTH_AUDIT_ARROW_SCHEMA = pa.schema([
    ("artifact_id", pa.string()),
    ("artifact_type", pa.string()),
    ("title", pa.string()),
    ("source_node", pa.string()),
    ("timestamp", pa.timestamp("us", tz="UTC")),
    ("tags", pa.list_(pa.string())),
    ("payload_json", pa.string()),          # Serialized JSON string for schema elasticity
    ("sha256_hash", pa.string()),           # 64-char hex
    ("metadata_json", pa.string()),
    ("created_at_epoch_ms", pa.int64()),
])

SFT_TRAINING_ARROW_SCHEMA = pa.schema([
    ("pair_id", pa.string()),
    ("dataset_name", pa.string()),          # e.g. 'tri_orchestrator_debate', 'antigravity_sdk'
    ("format", pa.string()),                # 'messages' or 'alpaca'
    ("instruction", pa.string()),
    ("thought", pa.string()),
    ("solution", pa.string()),
    ("messages_json", pa.string()),         # Serialized OpenAI messages array
    ("system_prompt", pa.string()),
    ("consensus_score", pa.float64()),
    ("pillar", pa.string()),
    ("source_node", pa.string()),
    ("timestamp", pa.timestamp("us", tz="UTC")),
    ("metadata_json", pa.string()),
])

DPO_PREFERENCE_ARROW_SCHEMA = pa.schema([
    ("pair_id", pa.string()),
    ("category", pa.string()),              # e.g. 'multi_path_interconnect_physics'
    ("dimension", pa.string()),             # e.g. 'V2_multi_path_physics'
    ("prompt", pa.string()),
    ("chosen", pa.string()),
    ("rejected", pa.string()),
    ("consensus_score", pa.float64()),
    ("source", pa.string()),
    ("timestamp", pa.timestamp("us", tz="UTC")),
    ("metadata_json", pa.string()),
])

MESH_TELEMETRY_ARROW_SCHEMA = pa.schema([
    ("timestamp", pa.timestamp("us", tz="UTC")),
    ("node_name", pa.string()),
    ("ip_address", pa.string()),
    ("latency_ms", pa.float64()),           # Nullable when offline
    ("status", pa.string()),                # 'ONLINE' or 'OFFLINE'
    ("transport", pa.string()),             # 'TB4_10G', 'TAILSCALE', 'WIFI_MLO', etc.
    ("jitter_ms", pa.float64()),
    ("packet_loss_pct", pa.float64()),
])

SCHEMA_REGISTRY: Dict[str, pa.Schema] = {
    "truth_audit": TRUTH_AUDIT_ARROW_SCHEMA,
    "truth_audit_debate": TRUTH_AUDIT_ARROW_SCHEMA,
    "sft_training": SFT_TRAINING_ARROW_SCHEMA,
    "sft_training_pairs": SFT_TRAINING_ARROW_SCHEMA,
    "sft_router_orchestrator_debate": SFT_TRAINING_ARROW_SCHEMA,
    "dpo_preference": DPO_PREFERENCE_ARROW_SCHEMA,
    "dpo_preference_pairs": DPO_PREFERENCE_ARROW_SCHEMA,
    "dpo_router_orchestrator_pairs": DPO_PREFERENCE_ARROW_SCHEMA,
    "mesh_telemetry": MESH_TELEMETRY_ARROW_SCHEMA,
    "mesh_telemetry_stream": MESH_TELEMETRY_ARROW_SCHEMA,
}


def parse_timestamp_to_datetime(val: Any) -> Optional[datetime.datetime]:
    """Parse various timestamp representations into UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime.datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=datetime.timezone.utc)
        return val.astimezone(datetime.timezone.utc)
    if isinstance(val, (int, float)):
        # Handle seconds vs milliseconds vs microseconds
        if val > 1e14:  # microseconds
            val_sec = val / 1e6
        elif val > 1e11:  # milliseconds
            val_sec = val / 1e3
        else:  # seconds
            val_sec = val
        return datetime.datetime.fromtimestamp(val_sec, tz=datetime.timezone.utc)
    if isinstance(val, str):
        val_clean = val.strip()
        if not val_clean:
            return None
        # Try numeric string
        try:
            val_num = float(val_clean)
            return parse_timestamp_to_datetime(val_num)
        except ValueError:
            pass
        # Try ISO format
        try:
            if val_clean.endswith("Z"):
                val_clean = val_clean[:-1] + "+00:00"
            dt = datetime.datetime.fromisoformat(val_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)


def normalize_record(record: Dict[str, Any], schema: pa.Schema) -> Dict[str, Any]:
    """
    Normalizes a dictionary record to strictly match the target PyArrow schema.
    Converts types, serializes nested structures to JSON strings where required,
    and fills missing fields with None or defaults.
    """
    normalized: Dict[str, Any] = {}

    for field in schema:
        name = field.name
        ftype = field.type
        raw_val = record.get(name)

        if raw_val is None:
            normalized[name] = None
            continue

        if pa.types.is_timestamp(ftype):
            normalized[name] = parse_timestamp_to_datetime(raw_val)
        elif pa.types.is_string(ftype):
            if isinstance(raw_val, (dict, list)):
                normalized[name] = json.dumps(raw_val, ensure_ascii=False)
            else:
                normalized[name] = str(raw_val)
        elif pa.types.is_list(ftype):
            if isinstance(raw_val, list):
                # Ensure elements are strings if list of string
                if pa.types.is_string(ftype.value_type):
                    normalized[name] = [str(x) if x is not None else "" for x in raw_val]
                else:
                    normalized[name] = raw_val
            elif isinstance(raw_val, (str, bytes)):
                try:
                    parsed = json.loads(raw_val)
                    if isinstance(parsed, list):
                        normalized[name] = [str(x) for x in parsed]
                    else:
                        normalized[name] = [str(raw_val)]
                except Exception:
                    normalized[name] = [str(raw_val)]
            else:
                normalized[name] = [str(raw_val)]
        elif pa.types.is_integer(ftype):
            try:
                normalized[name] = int(raw_val)
            except (ValueError, TypeError):
                normalized[name] = None
        elif pa.types.is_floating(ftype):
            try:
                normalized[name] = float(raw_val)
            except (ValueError, TypeError):
                normalized[name] = None
        elif pa.types.is_boolean(ftype):
            normalized[name] = bool(raw_val)
        else:
            normalized[name] = raw_val

    return normalized


def records_to_arrow_table(
    records: Sequence[Dict[str, Any]],
    schema: Optional[pa.Schema] = None
) -> pa.Table:
    """
    Converts a sequence of dictionary records to a PyArrow Table,
    applying schema normalization if a schema is provided.
    """
    if not records:
        if schema is not None:
            return schema.empty_table()
        return pa.Table.from_batches([], schema=pa.schema([]))

    if schema is not None:
        normalized_records = [normalize_record(r, schema) for r in records]
        return pa.Table.from_pylist(normalized_records, schema=schema)
    else:
        return pa.Table.from_pylist(list(records))


def get_schema_by_name(name: str) -> Optional[pa.Schema]:
    """Lookup canonical schema by table or topic name."""
    clean_name = name.lower().strip().replace("-", "_")
    return SCHEMA_REGISTRY.get(clean_name)
