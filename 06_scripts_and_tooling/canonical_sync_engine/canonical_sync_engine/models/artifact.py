"""
canonical_sync_engine.models.artifact
Defines TruthArtifact, ArtifactType, deterministic SHA-256 hashing, and Obsidian Markdown formatting.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ArtifactType(str, Enum):
    """Canonical artifact types supported across the Quad-Vault ecosystem."""
    TRUTH_AUDIT = "truth_audit"
    AI_DEBATE_CONSENSUS = "ai_debate_consensus"
    ARCHITECTURAL_DECISION = "architectural_decision"
    TELEMETRY_RECORD = "telemetry_record"
    LORA_PAIR = "lora_pair"
    BENCHMARK_RESULT = "benchmark_result"

    @classmethod
    def from_string(cls, value: Union[str, ArtifactType]) -> ArtifactType:
        """Case-insensitive parser for ArtifactType."""
        if isinstance(value, cls):
            return value
        val_str = str(value).strip().lower()
        for member in cls:
            if member.value.lower() == val_str:
                return member
        # Fallback support for uppercase / enum name strings
        val_upper = str(value).strip().upper()
        if val_upper in cls.__members__:
            return cls[val_upper]
        raise ValueError(
            f"Unknown ArtifactType '{value}'. Valid types: {[m.value for m in cls]}"
        )


@dataclass
class TruthArtifact:
    """
    Canonical representation of a verified truth artifact.
    Guarantees deterministic SHA-256 hashing and cross-target format generation.
    """
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    payload: Dict[str, Any]
    source_node: str = "Mac_Node"
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    sha256_hash: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate and coerce artifact_type
        if not isinstance(self.artifact_type, ArtifactType):
            self.artifact_type = ArtifactType.from_string(self.artifact_type)

        # Validate mandatory string fields
        if not self.artifact_id or not isinstance(self.artifact_id, str):
            raise ValueError("artifact_id must be a non-empty string.")
        if not self.title or not isinstance(self.title, str):
            raise ValueError("title must be a non-empty string.")
        if not self.source_node or not isinstance(self.source_node, str):
            raise ValueError("source_node must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise TypeError(f"payload must be a Dict[str, Any], got {type(self.payload).__name__}.")

        # Auto-compute SHA-256 hash if absent
        if not self.sha256_hash:
            self.sha256_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """
        Computes a deterministic, canonical SHA-256 hash over the normalized JSON representation.
        Sorts all dictionary keys recursively to guarantee hash invariance across platforms.
        """
        canonical_envelope = {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "title": self.title,
            "payload": self.payload,
            "source_node": self.source_node,
            "timestamp": self.timestamp,
            "tags": sorted(self.tags) if self.tags else [],
            "metadata": self.metadata,
        }
        # Compact canonical JSON with sorted keys
        canonical_bytes = json.dumps(
            canonical_envelope,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_hash(self) -> bool:
        """Asserts whether the current sha256_hash matches the computed canonical hash."""
        return self.sha256_hash == self.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the artifact to a standard dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "title": self.title,
            "payload": self.payload,
            "source_node": self.source_node,
            "timestamp": self.timestamp,
            "sha256_hash": self.sha256_hash,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TruthArtifact:
        """Reconstructs a TruthArtifact from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")

        required_fields = ["artifact_id", "artifact_type", "title", "payload"]
        for req in required_fields:
            if req not in data:
                raise KeyError(f"Missing required field '{req}' in artifact data.")

        return cls(
            artifact_id=data["artifact_id"],
            artifact_type=ArtifactType.from_string(data["artifact_type"]),
            title=data["title"],
            payload=data["payload"],
            source_node=data.get("source_node", "Mac_Node"),
            timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            sha256_hash=data.get("sha256_hash", ""),
            tags=list(data.get("tags", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializes the artifact to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> TruthArtifact:
        """Parses a TruthArtifact from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_markdown_frontmatter(self, custom_body: Optional[str] = None) -> str:
        """
        Generates standard Obsidian Markdown with YAML frontmatter and bidirectional Wikilinks.
        """
        # Format tags for YAML
        if self.tags:
            tags_yaml = "tags:\n" + "\n".join(f"  - {t}" for t in self.tags)
        else:
            tags_yaml = "tags: []"

        formatted_payload = json.dumps(self.payload, indent=2, sort_keys=True, ensure_ascii=False)

        md_lines = [
            "---",
            f'title: "{self.title}"',
            f'artifact_id: "{self.artifact_id}"',
            f'artifact_type: "{self.artifact_type.value}"',
            f'source_node: "{self.source_node}"',
            f'timestamp: "{self.timestamp}"',
            f'sha256_hash: "{self.sha256_hash}"',
            tags_yaml,
            "---",
            "",
            f"# {self.title}",
            "",
            "## Metadata",
            f"- **Artifact ID**: `{self.artifact_id}`",
            f"- **Artifact Type**: `{self.artifact_type.value}`",
            f"- **Source Node**: `{self.source_node}`",
            f"- **Timestamp**: `{self.timestamp}`",
            f"- **Canonical Hash (SHA-256)**: `{self.sha256_hash}`",
            f"- **Knowledge Links**: [[Index]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[{self.artifact_type.value}]]",
            "",
            "## Payload Content",
            "```json",
            formatted_payload,
            "```",
        ]

        if custom_body:
            md_lines.extend(["", "## Discussion & Context", custom_body.strip()])

        return "\n".join(md_lines) + "\n"
