"""
canonical_sync_engine.sync.obsidian_syncer
Obsidian Knowledge Graph vault adapter: Markdown note generation with YAML frontmatter and Wikilinks.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.sync_result import VaultSyncResult
from canonical_sync_engine.sync.base import BaseVaultSyncer


class ObsidianVaultSyncer(BaseVaultSyncer):
    """
    Synchronizes TruthArtifacts to the Obsidian Knowledge Graph (obsidian_vault/).
    Generates Markdown notes with YAML frontmatter, cryptographic metadata, and
    bidirectional canonical Wikilinks ([[Index]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]]).
    """

    def __init__(self, config: Optional[SyncConfig] = None) -> None:
        super().__init__(config)

    @property
    def vault_name(self) -> str:
        return "obsidian"

    @property
    def notes_dir(self) -> Path:
        """Directory where artifact markdown notes are persisted."""
        return self.config.obsidian_vault_path / "truth_artifacts"

    def get_note_path(self, artifact_id: str) -> Path:
        """Returns target path for an artifact's Markdown note."""
        # Sanitize artifact_id for filesystem safety
        safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in artifact_id)
        return self.notes_dir / f"{safe_id}.md"

    def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
        """
        Generates and atomically writes an Obsidian Markdown note for the artifact.
        """
        with self._measure_time() as timer:
            note_path = self.get_note_path(artifact.artifact_id)

            try:
                # Generate Markdown content with YAML frontmatter and Wikilinks
                content = self._render_markdown(artifact)
                bytes_written = self._atomic_write_text(note_path, content)

                # Post-sync verification
                if not self.verify(artifact):
                    return VaultSyncResult.create_failure(
                        vault_name=self.vault_name,
                        target_path=str(note_path),
                        error="Post-sync verification failed: Obsidian note missing Wikilinks or hash parity mismatch.",
                        latency_ms=timer.elapsed_ms,
                    )

                return VaultSyncResult.create_success(
                    vault_name=self.vault_name,
                    target_path=str(note_path),
                    sha256_hash=artifact.sha256_hash,
                    bytes_written=bytes_written,
                    latency_ms=timer.elapsed_ms,
                    metadata={
                        "wikilinks": [
                            "[[Index]]",
                            "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
                            f"[[{artifact.artifact_type.value}]]",
                        ],
                        "note_file": str(note_path),
                    },
                )

            except Exception as e:
                return VaultSyncResult.create_failure(
                    vault_name=self.vault_name,
                    target_path=str(note_path),
                    error=f"Obsidian vault sync error: {type(e).__name__}: {str(e)}",
                    latency_ms=timer.elapsed_ms,
                )

    def verify(self, artifact: TruthArtifact) -> bool:
        """
        Verifies that the markdown note exists, contains required Wikilinks and metadata,
        and matches the canonical SHA-256 hash.
        """
        note_path = self.get_note_path(artifact.artifact_id)
        if not note_path.exists() or not note_path.is_file():
            # Check direct obsidian_vault_path fallback
            direct_path = self.config.obsidian_vault_path / f"{artifact.artifact_id}.md"
            if direct_path.exists() and direct_path.is_file():
                note_path = direct_path
            else:
                return False

        try:
            content = note_path.read_text(encoding="utf-8")

            # 1. Assert mandatory Wikilinks
            mandatory_wikilinks = [
                "[[Index]]",
                "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
                f"[[{artifact.artifact_type.value}]]",
            ]
            for link in mandatory_wikilinks:
                if link not in content:
                    return False

            # 2. Extract and verify SHA-256 hash in frontmatter / metadata
            hash_pattern = r'sha256_hash:\s*["\']?([a-fA-F0-9]{64})["\']?'
            match = re.search(hash_pattern, content)
            if not match:
                return False

            extracted_hash = match.group(1).lower()
            if extracted_hash != artifact.sha256_hash.lower():
                return False

            # 3. Parse and verify reconstructed artifact
            reconstructed = self._parse_markdown(content)
            if not reconstructed:
                return False

            return (
                reconstructed.artifact_id == artifact.artifact_id
                and reconstructed.sha256_hash == artifact.sha256_hash
                and reconstructed.verify_hash()
            )

        except Exception:
            return False

    def read(self, artifact_id: str) -> Optional[TruthArtifact]:
        """
        Reads and parses an Obsidian Markdown note, reconstructing the TruthArtifact.
        """
        note_path = self.get_note_path(artifact_id)
        if not note_path.exists() or not note_path.is_file():
            direct_path = self.config.obsidian_vault_path / f"{artifact_id}.md"
            if direct_path.exists() and direct_path.is_file():
                note_path = direct_path
            else:
                return None

        try:
            content = note_path.read_text(encoding="utf-8")
            return self._parse_markdown(content)
        except Exception:
            return None

    def _render_markdown(self, artifact: TruthArtifact) -> str:
        """
        Formats a TruthArtifact into standard Obsidian Markdown with YAML frontmatter
        and canonical bidirectional Wikilinks.
        """
        # Format tags
        tags_yaml = ""
        if artifact.tags:
            tags_yaml = "tags:\n" + "\n".join(f"  - {t}" for t in artifact.tags)
        else:
            tags_yaml = "tags: []"

        formatted_payload = json.dumps(
            artifact.payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )

        formatted_metadata = json.dumps(
            artifact.metadata,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )

        lines = [
            "---",
            f'title: "{artifact.title}"',
            f'artifact_id: "{artifact.artifact_id}"',
            f'artifact_type: "{artifact.artifact_type.value}"',
            f'source_node: "{artifact.source_node}"',
            f'timestamp: "{artifact.timestamp}"',
            f'sha256_hash: "{artifact.sha256_hash}"',
            tags_yaml,
            "---",
            "",
            f"# 🧠 {artifact.title}",
            "",
            "## 🧭 Master Navigation & Canonical Wikilinks",
            "- [[Index]]",
            "- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
            f"- [[{artifact.artifact_type.value}]]",
            "- [[04_data_and_memory]]",
            "",
            "## 📋 Cryptographic & Audit Metadata",
            f"- **Artifact ID**: `{artifact.artifact_id}`",
            f"- **Artifact Type**: `{artifact.artifact_type.value}`",
            f"- **Source Node**: `{artifact.source_node}`",
            f"- **Timestamp (UTC)**: `{artifact.timestamp}`",
            f"- **Canonical SHA-256 Hash**: `{artifact.sha256_hash}`",
            "",
            "## 📦 Payload Content",
            "```json",
            formatted_payload,
            "```",
            "",
            "## 🏷️ Metadata Envelope",
            "```json",
            formatted_metadata,
            "```",
            "",
        ]
        return "\n".join(lines)

    def _parse_markdown(self, content: str) -> Optional[TruthArtifact]:
        """
        Parses Markdown frontmatter, JSON payload block, and metadata envelope.
        """
        try:
            # Parse YAML frontmatter
            frontmatter_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not frontmatter_match:
                return None
            fm_text = frontmatter_match.group(1)

            fm_dict: Dict[str, Any] = {}
            current_tag_list: Optional[List[str]] = None

            for line in fm_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("tags:"):
                    if line == "tags: []":
                        fm_dict["tags"] = []
                    else:
                        current_tag_list = []
                        fm_dict["tags"] = current_tag_list
                    continue

                if current_tag_list is not None and line.startswith("- "):
                    current_tag_list.append(line[2:].strip())
                    continue
                else:
                    current_tag_list = None

                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    fm_dict[k] = v

            # Parse JSON payload block
            payload_match = re.search(
                r"## 📦 Payload Content\s*```json\s*\n(.*?)\n```",
                content,
                re.DOTALL,
            )
            if not payload_match:
                # Fallback for generic payload code block
                payload_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
            if not payload_match:
                return None

            payload_json = payload_match.group(1)
            payload = json.loads(payload_json)

            # Parse optional metadata envelope
            metadata_match = re.search(
                r"## 🏷️ Metadata Envelope\s*```json\s*\n(.*?)\n```",
                content,
                re.DOTALL,
            )
            metadata = {}
            if metadata_match:
                try:
                    metadata = json.loads(metadata_match.group(1))
                except Exception:
                    metadata = {}

            artifact = TruthArtifact(
                artifact_id=fm_dict.get("artifact_id", ""),
                artifact_type=ArtifactType.from_string(fm_dict.get("artifact_type", "truth_audit")),
                title=fm_dict.get("title", ""),
                payload=payload,
                source_node=fm_dict.get("source_node", "Mac_Node"),
                timestamp=fm_dict.get("timestamp", ""),
                sha256_hash=fm_dict.get("sha256_hash", ""),
                tags=fm_dict.get("tags", []),
                metadata=metadata,
            )
            return artifact
        except Exception:
            return None
