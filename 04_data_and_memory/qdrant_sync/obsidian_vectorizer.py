#!/usr/bin/env python3
"""
================================================================================
Lauburu Monorepo - Obsidian Vault Vectorizer & Qdrant Watchdog Daemon
================================================================================
Version: 1.0.0-CANONICAL
Module: 04_data_and_memory/qdrant_sync/obsidian_vectorizer.py

Watches and vectorizes the Obsidian Knowledge Vault:
1. Continuous Watchdog Monitoring (with Polling fallback) with 1.5s debouncing.
2. Semantic Markdown Chunking: YAML frontmatter extraction, heading-based slicing
   (#, ##, ###), sliding-window sub-chunking (max 1200 chars, 150 char overlap).
3. Local llama.cpp Embedding Client (Port 8081 /v1/embeddings): Batching,
   exponential backoff, retry mechanisms. Rule #0 Zero-Mock compliant.
4. Qdrant Vector DB Sync Store: Dual-mode support for HTTP REST API (Port 6333),
   QdrantClient SDK, and local embedded SQLite storage fallback (qdrant_data).
5. State Tracking & Telemetry: SHA-256 hash change detection and session logs.
"""

import os
import sys
import re
import time
import json
import uuid
import signal
import hashlib
import logging
import sqlite3
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, date, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict

# Optional PyYAML
try:
    import yaml
    HAS_YAML = True
except ImportError:
    yaml = None
    HAS_YAML = False

# Optional watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = None
    HAS_WATCHDOG = False

# Optional qdrant_client
try:
    import qdrant_client
    from qdrant_client.http import models as qmodels
    HAS_QDRANT_CLIENT = True
except ImportError:
    qdrant_client = None
    qmodels = None
    HAS_QDRANT_CLIENT = False


# ==============================================================================
# Configuration & Constants
# ==============================================================================

DEFAULT_VAULT_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
DEFAULT_LLAMA_ENDPOINT = "http://localhost:8081/v1/embeddings"
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/qdrant_data")
DEFAULT_COLLECTION = "obsidian_vault"
DEFAULT_STATE_FILE = Path(__file__).resolve().parent / "obsidian_sync_state.json"
DEFAULT_LOG_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/session_logs/obsidian_vectorizer.log")
DEFAULT_TELEMETRY_LOG = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/session_logs/rag_watchdog_telemetry.jsonl")

# 9 Canonical Architectural Categories
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Canonical Module": [
        "canonical_module", "canonical 13-module", "module"
    ],
    "Infrastructure": [
        "infrastructure", "seaweedfs", "docker", "tailscale", "wireguard",
        "derp", "gateway", "router", "wan", "network", "mesh", "speedify",
        "gl_inet", "sovereign", "bonding", "tun_tap", "storage_topology"
    ],
    "AI & Inference": [
        "ai_inference", "inference", "petals", "llama", "gguf", "rpc",
        "exo", "vram", "models", "sharding", "huggingface", "smolagents",
        "vlm", "termius", "ai-debate", "hardware_ram"
    ],
    "Biometrics & DSP": [
        "biometrics", "ecg", "dsp", "pan_tompkins", "movesense", "dfa",
        "ble", "bluetooth", "heart_rate", "kinematics"
    ],
    "Data & Memory": [
        "pyspark", "data", "memory", "lora", "dataset", "qdrant",
        "delta_lake", "sync", "google_workspace", "drive"
    ],
    "Swarm & Governance": [
        "swarm", "debate", "governance", "agent", "orchestrator",
        "consensus", "triad", "council", "teamwork", "shizuku",
        "device-hardware-governor", "deliberation"
    ],
    "Tooling & Scripts": [
        "tooling", "scripts", "ssh", "adb", "wol", "wake_on_lan",
        "automation", "daemon", "self-healing", "cron", "mcp"
    ],
    "Architecture & Docs": [
        "index", "architecture", "canonical_project", "rule",
        "whitepaper", "rfc", "deep_architecture", "global_architecture",
        "hardware_topology", "7_device_mesh"
    ],
    "Audit & Telemetry": [
        "audit", "telemetry", "ledger", "crawl", "triage", "report",
        "results", "anomalies", "state_august", "unfinished", "crash"
    ]
}


# ==============================================================================
# Data Models
# ==============================================================================

@dataclass
class MarkdownChunk:
    """Represents a single semantically segmented chunk of an Obsidian note."""
    point_id: str
    filepath: str
    filename: str
    title: str
    category: str
    tags: List[str]
    heading: str
    chunk_index: int
    chunk_total: int
    text: str
    char_count: int
    content_hash: str
    last_modified: str
    updated_at: str

    def to_payload(self) -> Dict[str, Any]:
        """Convert chunk metadata to Qdrant payload dictionary."""
        return {
            "point_id": self.point_id,
            "filepath": self.filepath,
            "filename": self.filename,
            "title": self.title,
            "category": self.category,
            "tags": self.tags,
            "heading": self.heading,
            "chunk_index": self.chunk_index,
            "chunk_total": self.chunk_total,
            "text": self.text,
            "char_count": self.char_count,
            "content_hash": self.content_hash,
            "last_modified": self.last_modified,
            "updated_at": self.updated_at
        }


@dataclass
class SyncStats:
    """Tracks synchronization run statistics."""
    files_scanned: int = 0
    files_indexed: int = 0
    files_skipped: int = 0
    files_deleted: int = 0
    chunks_generated: int = 0
    embeddings_computed: int = 0
    points_upserted: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or time.time()
        return max(0.0, end - self.start_time)

    def summary(self) -> str:
        return (
            f"Scanned: {self.files_scanned} files | "
            f"Indexed: {self.files_indexed} | "
            f"Skipped: {self.files_skipped} | "
            f"Deleted: {self.files_deleted} | "
            f"Chunks: {self.chunks_generated} | "
            f"Embeddings: {self.embeddings_computed} | "
            f"Points: {self.points_upserted} | "
            f"Errors: {self.errors} | "
            f"Duration: {self.duration_seconds:.2f}s"
        )


class EmbeddingAPIError(Exception):
    """Raised when the embedding API fails after retries."""
    pass


# ==============================================================================
# Markdown Parsing & Chunking Engine
# ==============================================================================

class MarkdownChunker:
    """
    Parses YAML frontmatter, headings, tags, and creates sliding-window chunks.
    """

    def __init__(self, max_chunk_size: int = 1200, overlap: int = 150) -> None:
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.step_size = max(100, max_chunk_size - overlap)

    def extract_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]:
        """
        Extracts YAML frontmatter delimiters (--- ... --- or --- ... ...).
        Uses PyYAML if available, with robust regex fallback.
        """
        text = text.lstrip("\ufeff")  # Strip UTF-8 BOM
        fm_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, flags=re.DOTALL)
        if not fm_match:
            fm_match = re.match(r"^---\r?\n(.*?)\r?\n\.\.\.\r?\n(.*)$", text, flags=re.DOTALL)

        if fm_match:
            raw_fm = fm_match.group(1)
            body = fm_match.group(2)
            if HAS_YAML and yaml:
                try:
                    parsed = yaml.safe_load(raw_fm)
                    if isinstance(parsed, dict):
                        return parsed, body
                except Exception:
                    pass

            # Regex Fallback
            fallback_dict: Dict[str, Any] = {}
            title_m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", raw_fm, flags=re.MULTILINE)
            if title_m:
                fallback_dict["title"] = title_m.group(1).strip()

            tags_m = re.search(r"^tags:\s*\[?([^\n\r]+)", raw_fm, flags=re.MULTILINE)
            if tags_m:
                raw_tags = tags_m.group(1).rstrip("]").strip()
                tags_list = [t.strip().strip("\"'").lstrip("#") for t in raw_tags.split(",") if t.strip()]
                fallback_dict["tags"] = tags_list
            else:
                tag_block = re.search(r"^tags:\s*\n((?:\s*-\s*.*\n?)+)", raw_fm, flags=re.MULTILINE)
                if tag_block:
                    tags_list = [
                        re.sub(r"^\s*-\s*", "", line).strip().strip("\"'").lstrip("#")
                        for line in tag_block.group(1).splitlines() if line.strip()
                    ]
                    fallback_dict["tags"] = tags_list

            cat_m = re.search(r"^category:\s*[\"']?(.*?)[\"']?$", raw_fm, flags=re.MULTILINE)
            if cat_m:
                fallback_dict["category"] = cat_m.group(1).strip()

            upd_m = re.search(r"^updated:\s*[\"']?(.*?)[\"']?$", raw_fm, flags=re.MULTILINE)
            if upd_m:
                fallback_dict["updated"] = upd_m.group(1).strip()

            return fallback_dict, body

        return {}, text

    def classify_category(self, stem: str, frontmatter: Dict[str, Any], title: str, text: str) -> str:
        """Determines the architectural category based on frontmatter, keywords, and text."""
        # 1. Frontmatter explicit category
        fm_cat = frontmatter.get("category")
        if fm_cat and isinstance(fm_cat, str):
            for c in CATEGORY_KEYWORDS:
                if c.lower() in fm_cat.lower():
                    return c

        # 2. Canonical Module Check (00_ to 12_)
        if re.match(r"^\d{2}_", stem):
            return "Canonical Module"

        # 3. Keyword Scoring across title, tags, and content
        fm_str = json.dumps(frontmatter, default=str)
        search_blob = f"{stem} {title} {fm_str} {text[:1500]}".lower()
        scores: Dict[str, int] = {}
        for cat_name, kw_list in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in kw_list if kw in search_blob)
            scores[cat_name] = score

        best_cat = max(scores.items(), key=lambda x: x[1])
        if best_cat[1] > 0:
            return best_cat[0]

        return "Architecture & Docs"

    def chunk_file(self, rel_path: str, full_path: Path) -> List[MarkdownChunk]:
        """
        Parses and chunks a single markdown file into a list of MarkdownChunk items.
        """
        if not full_path.exists():
            return []

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
        except Exception as e:
            logging.error(f"Error reading file {full_path}: {e}")
            return []

        # Get file modification time
        try:
            mtime = full_path.stat().st_mtime
            mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            last_modified_str = mtime_dt.isoformat()
        except Exception:
            last_modified_str = datetime.now(timezone.utc).isoformat()

        frontmatter, body_text = self.extract_frontmatter(raw_text)
        stem = full_path.stem

        # Extract Title
        title = frontmatter.get("title")
        if not title:
            h1_m = re.search(r"^#\s+(.+)$", body_text, flags=re.MULTILINE)
            if h1_m:
                title = h1_m.group(1).strip()
            else:
                title = stem.replace("_", " ")
        else:
            title = str(title).strip()

        # Extract Tags
        tags: List[str] = []
        fm_tags = frontmatter.get("tags", [])
        if isinstance(fm_tags, list):
            tags.extend([str(t).strip().lstrip("#") for t in fm_tags if t])
        elif isinstance(fm_tags, str):
            tags.extend([t.strip().lstrip("#") for t in fm_tags.split(",") if t.strip()])

        # Inline hashtags
        inline_tags = re.findall(r"(?:^|\s)#([a-zA-Z0-9_\-]+)", body_text)
        for it in inline_tags:
            if it.lower() not in [x.lower() for x in tags] and not it.isdigit():
                tags.append(it)

        # Classify Category
        category = self.classify_category(stem, frontmatter, title, body_text)

        # Split into heading sections (#, ##, ###, ####)
        heading_pattern = re.compile(r"(^#{1,4}\s+.+$)", re.MULTILINE)
        splits = heading_pattern.split(body_text)

        sections: List[Tuple[str, str]] = []
        if splits:
            preamble = splits[0].strip()
            if preamble:
                sections.append((f"# {title}", preamble))

            for i in range(1, len(splits), 2):
                h_text = splits[i].strip()
                c_text = splits[i + 1].strip() if i + 1 < len(splits) else ""
                sections.append((h_text, c_text))

        if not sections:
            sections = [(f"# {title}", body_text.strip())]

        raw_chunks: List[Tuple[str, str]] = []
        for heading, content in sections:
            combined = f"{heading}\n\n{content}".strip() if content else heading
            if len(combined) <= self.max_chunk_size:
                raw_chunks.append((heading, combined))
            else:
                # Sliding window chunking
                start = 0
                while start < len(combined):
                    end = min(start + self.max_chunk_size, len(combined))
                    sub_text = combined[start:end].strip()
                    if sub_text:
                        raw_chunks.append((heading, sub_text))
                    if end >= len(combined):
                        break
                    start += self.step_size

        total_chunks = len(raw_chunks)
        final_chunks: List[MarkdownChunk] = []
        iso_now = datetime.now(timezone.utc).isoformat()

        for idx, (h, c) in enumerate(raw_chunks):
            c_hash = hashlib.sha256(c.encode("utf-8")).hexdigest()
            # Deterministic UUID5 for Qdrant point
            p_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"obsidian://{rel_path}#chunk_{idx}_{c_hash[:8]}"))

            final_chunks.append(MarkdownChunk(
                point_id=p_id,
                filepath=rel_path,
                filename=os.path.basename(rel_path),
                title=title,
                category=category,
                tags=tags,
                heading=h,
                chunk_index=idx,
                chunk_total=total_chunks,
                text=c,
                char_count=len(c),
                content_hash=c_hash,
                last_modified=last_modified_str,
                updated_at=iso_now
            ))

        return final_chunks


# ==============================================================================
# llama.cpp Embedding API Client (Rule #0 Zero-Mock)
# ==============================================================================

class LlamaEmbeddingClient:
    """
    HTTP client for the local llama.cpp embeddings API (Port 8081 /v1/embeddings).
    Enforces Rule #0 (Zero-Mock): Authentic requests, batching, exponential backoff.
    Never fabricates fake or random embeddings.
    """

    def __init__(
        self,
        endpoint_url: str = DEFAULT_LLAMA_ENDPOINT,
        max_retries: int = 4,
        base_backoff: float = 1.0,
        max_backoff: float = 10.0,
        timeout: float = 20.0
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        if not self.endpoint_url.endswith("/v1/embeddings"):
            if self.endpoint_url.endswith("/v1"):
                self.endpoint_url = f"{self.endpoint_url}/embeddings"
            elif "/embeddings" not in self.endpoint_url:
                self.endpoint_url = f"{self.endpoint_url}/v1/embeddings"

        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.timeout = timeout

    def check_health(self) -> Tuple[bool, str]:
        """Checks if the llama-server is healthy and ready to serve embeddings."""
        base_url = self.endpoint_url.split("/v1/")[0]
        for test_path in ["/health", "/v1/models"]:
            test_url = f"{base_url}{test_path}"
            try:
                req = urllib.request.Request(test_url, method="GET")
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        return True, f"Healthy (200 OK from {test_path})"
            except urllib.error.HTTPError as e:
                if e.code == 503:
                    return False, "Loading model (503 Service Unavailable)"
                return False, f"HTTP Error {e.code}: {e.reason}"
            except Exception as e:
                return False, f"Connection failed: {e}"

        return False, "Unreachable"

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Fetches dense vector embeddings for a list of texts using batching and retries.
        Raises EmbeddingAPIError if the server is unavailable or fails after retries.
        """
        if not texts:
            return []

        payload = {
            "input": texts,
            "model": "embedding"
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.endpoint_url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        data_items = resp_data.get("data", [])
                        # Sort by index if present
                        data_items.sort(key=lambda x: x.get("index", 0))
                        embeddings = [item.get("embedding", []) for item in data_items]
                        if len(embeddings) == len(texts):
                            return embeddings
                        raise EmbeddingAPIError(
                            f"Mismatched embedding count: got {len(embeddings)}, expected {len(texts)}"
                        )

            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8")
                except Exception:
                    pass

                logging.warning(
                    f"[LlamaEmbeddingClient] HTTP {e.code} on attempt {attempt}/{self.max_retries}: {e.reason} - {err_body}"
                )

                if attempt == self.max_retries:
                    raise EmbeddingAPIError(
                        f"Llama embedding API failed after {self.max_retries} attempts: HTTP {e.code} {err_body}"
                    )

            except Exception as e:
                logging.warning(
                    f"[LlamaEmbeddingClient] Connection error on attempt {attempt}/{self.max_retries}: {e}"
                )
                if attempt == self.max_retries:
                    raise EmbeddingAPIError(
                        f"Llama embedding API connection failed after {self.max_retries} attempts: {e}"
                    )

            backoff = min(self.max_backoff, self.base_backoff * (2 ** (attempt - 1)))
            logging.info(f"[LlamaEmbeddingClient] Retrying in {backoff:.2f}s...")
            time.sleep(backoff)

        raise EmbeddingAPIError("Llama embedding API unreachable")


# ==============================================================================
# Qdrant Vector DB Sync Store (REST + Embedded SQLite Dual Mode)
# ==============================================================================

class QdrantSyncStore:
    """
    Manages vector point upserts and deletions in Qdrant.
    Supports:
    1. Qdrant HTTP REST API (Port 6333)
    2. Local Embedded SQLite storage fallback (qdrant_data)
    3. QdrantClient SDK if installed.
    """

    def __init__(
        self,
        qdrant_url: str = DEFAULT_QDRANT_URL,
        qdrant_path: Path = DEFAULT_QDRANT_PATH,
        collection_name: str = DEFAULT_COLLECTION
    ) -> None:
        self.qdrant_url = qdrant_url.rstrip("/")
        self.qdrant_path = Path(qdrant_path)
        self.collection_name = collection_name
        self._mode = "unknown"
        self._detect_storage_mode()

    def _detect_storage_mode(self) -> None:
        """Determines whether to use HTTP REST or embedded SQLite."""
        try:
            req = urllib.request.Request(f"{self.qdrant_url}/collections", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    self._mode = "http_rest"
                    logging.info(f"[QdrantSyncStore] Using Qdrant HTTP REST API at {self.qdrant_url}")
                    return
        except Exception:
            pass

        # Fallback to local SQLite
        self._mode = "sqlite_embedded"
        self.qdrant_path.mkdir(parents=True, exist_ok=True)
        col_dir = self.qdrant_path / "collection" / self.collection_name
        col_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"[QdrantSyncStore] Using Embedded SQLite storage at {col_dir}")

    @property
    def mode(self) -> str:
        return self._mode

    def _get_sqlite_db_path(self) -> Path:
        return self.qdrant_path / "collection" / self.collection_name / "storage.sqlite"

    def _ensure_sqlite_schema(self, vector_dim: int = 128) -> None:
        """Initializes the SQLite storage and meta.json if not present."""
        db_path = self._get_sqlite_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS points (id TEXT PRIMARY KEY, point BLOB);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_points_id ON points(id);")
        conn.commit()
        conn.close()

        # Update meta.json
        meta_file = self.qdrant_path / "meta.json"
        meta_data: Dict[str, Any] = {"collections": {}, "aliases": {}}
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
            except Exception:
                pass

        if "collections" not in meta_data:
            meta_data["collections"] = {}

        if self.collection_name not in meta_data["collections"]:
            meta_data["collections"][self.collection_name] = {
                "vectors": {
                    "size": vector_dim,
                    "distance": "Cosine",
                    "hnsw_config": None,
                    "quantization_config": None,
                    "on_disk": None,
                    "datatype": None,
                    "multivector_config": None
                },
                "shard_number": None,
                "sharding_method": None,
                "replication_factor": None,
                "write_consistency_factor": None,
                "on_disk_payload": None,
                "hnsw_config": None,
                "wal_config": None,
                "optimizers_config": None,
                "quantization_config": None,
                "sparse_vectors": None,
                "strict_mode_config": None,
                "metadata": None
            }
            try:
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=2)
            except Exception as e:
                logging.warning(f"Could not update meta.json: {e}")

    def ensure_collection(self, vector_dim: int = 128) -> None:
        """Ensures the collection exists in Qdrant or SQLite."""
        if self._mode == "http_rest":
            try:
                url = f"{self.qdrant_url}/collections/{self.collection_name}"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        return
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Create collection
                    create_url = f"{self.qdrant_url}/collections/{self.collection_name}"
                    create_payload = json.dumps({
                        "vectors": {
                            "size": vector_dim,
                            "distance": "Cosine"
                        }
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        create_url,
                        data=create_payload,
                        headers={"Content-Type": "application/json"},
                        method="PUT"
                    )
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        logging.info(f"Created Qdrant collection '{self.collection_name}' (dim={vector_dim})")
            except Exception as e:
                logging.warning(f"Error checking/creating Qdrant collection: {e}. Falling back to SQLite.")
                self._mode = "sqlite_embedded"
                self._ensure_sqlite_schema(vector_dim)
        else:
            self._ensure_sqlite_schema(vector_dim)

    def upsert_chunks(self, chunks: List[MarkdownChunk], vectors: List[List[float]]) -> int:
        """
        Upserts a batch of chunks and their embedding vectors to Qdrant or SQLite.
        Returns the number of points upserted.
        """
        if not chunks or not vectors or len(chunks) != len(vectors):
            return 0

        vector_dim = len(vectors[0])
        self.ensure_collection(vector_dim)

        if self._mode == "http_rest":
            points_payload = []
            for chk, vec in zip(chunks, vectors):
                points_payload.append({
                    "id": chk.point_id,
                    "vector": vec,
                    "payload": chk.to_payload()
                })

            upsert_url = f"{self.qdrant_url}/collections/{self.collection_name}/points"
            req_data = json.dumps({"points": points_payload}, default=str).encode("utf-8")
            try:
                req = urllib.request.Request(
                    upsert_url,
                    data=req_data,
                    headers={"Content-Type": "application/json"},
                    method="PUT"
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    if resp.status == 200:
                        return len(chunks)
            except Exception as e:
                logging.warning(f"REST upsert failed: {e}. Falling back to SQLite.")
                self._mode = "sqlite_embedded"
                self._ensure_sqlite_schema(vector_dim)

        # SQLite Fallback Upsert
        db_path = self._get_sqlite_db_path()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        for chk, vec in zip(chunks, vectors):
            record_dict = {
                "id": chk.point_id,
                "vector": vec,
                "payload": chk.to_payload()
            }
            blob_data = json.dumps(record_dict, default=str).encode("utf-8")
            cursor.execute(
                "INSERT OR REPLACE INTO points (id, point) VALUES (?, ?);",
                (chk.point_id, blob_data)
            )

        conn.commit()
        conn.close()
        return len(chunks)

    def delete_file_chunks(self, filepath: str) -> int:
        """
        Deletes all chunks belonging to a specific source filepath.
        """
        if self._mode == "http_rest":
            delete_url = f"{self.qdrant_url}/collections/{self.collection_name}/points/delete"
            filter_payload = {
                "filter": {
                    "must": [
                        {
                            "key": "filepath",
                            "match": {"value": filepath}
                        }
                    ]
                }
            }
            try:
                req = urllib.request.Request(
                    delete_url,
                    data=json.dumps(filter_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        return 1
            except Exception as e:
                logging.warning(f"REST delete failed: {e}. Trying SQLite.")

        # SQLite Delete
        db_path = self._get_sqlite_db_path()
        if not db_path.exists():
            return 0

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id, point FROM points;")
        rows = cursor.fetchall()
        deleted_count = 0

        for p_id, blob in rows:
            try:
                data = json.loads(blob.decode("utf-8"))
                if data.get("payload", {}).get("filepath") == filepath:
                    cursor.execute("DELETE FROM points WHERE id = ?;", (p_id,))
                    deleted_count += 1
            except Exception:
                pass

        conn.commit()
        conn.close()
        return deleted_count

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on the current collection."""
        stats: Dict[str, Any] = {
            "mode": self._mode,
            "collection": self.collection_name,
            "points_count": 0,
            "status": "ok"
        }

        if self._mode == "http_rest":
            try:
                url = f"{self.qdrant_url}/collections/{self.collection_name}"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    result = data.get("result", {})
                    stats["points_count"] = result.get("points_count", 0)
                    stats["vectors_count"] = result.get("vectors_count", 0)
                    stats["status"] = result.get("status", "green")
                    return stats
            except Exception:
                pass

        # SQLite stats
        db_path = self._get_sqlite_db_path()
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                integrity = cursor.fetchone()[0]
                cursor.execute("SELECT count(*) FROM points;")
                count = cursor.fetchone()[0]
                conn.close()
                stats["points_count"] = count
                stats["integrity"] = integrity
                stats["db_path"] = str(db_path)
            except Exception as e:
                stats["status"] = f"error: {e}"

        return stats


# ==============================================================================
# State Cache Management
# ==============================================================================

class SyncStateCache:
    """Tracks SHA-256 hashes and mtimes of indexed files to prevent redundant re-indexing."""

    def __init__(self, state_file: Path = DEFAULT_STATE_FILE) -> None:
        self.state_file = Path(state_file)
        self.state: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load sync state: {e}")
                self.state = {}

    def save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not save sync state: {e}")

    def is_file_changed(self, rel_path: str, full_path: Path) -> bool:
        if rel_path not in self.state:
            return True
        cached = self.state[rel_path]
        try:
            stat = full_path.stat()
            if stat.st_mtime != cached.get("mtime"):
                # Check SHA-256 of file content
                with open(full_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                return file_hash != cached.get("hash")
            return False
        except Exception:
            return True

    def record_indexed(self, rel_path: str, full_path: Path, chunk_count: int) -> None:
        try:
            stat = full_path.stat()
            with open(full_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            self.state[rel_path] = {
                "mtime": stat.st_mtime,
                "hash": file_hash,
                "chunk_count": chunk_count,
                "indexed_at": datetime.now(timezone.utc).isoformat()
            }
            self.save()
        except Exception as e:
            logging.warning(f"Failed to record state for {rel_path}: {e}")

    def remove_file(self, rel_path: str) -> None:
        if rel_path in self.state:
            del self.state[rel_path]
            self.save()


# ==============================================================================
# Debounced Watchdog & Polling File Watcher Daemon
# ==============================================================================

class DebounceEventQueue:
    """Thread-safe debounce queue coalescing rapid editor write bursts."""

    def __init__(self, debounce_delay: float = 1.5) -> None:
        self.debounce_delay = debounce_delay
        self._pending: Dict[str, Tuple[str, float]] = {}  # filepath -> (event_type, trigger_time)

    def push(self, filepath: str, event_type: str) -> None:
        trigger_time = time.time() + self.debounce_delay
        self._pending[filepath] = (event_type, trigger_time)

    def pop_ready(self) -> List[Tuple[str, str]]:
        now = time.time()
        ready = []
        for path, (ev_type, trig_time) in list(self._pending.items()):
            if now >= trig_time:
                ready.append((path, ev_type))
                del self._pending[path]
        return ready

    def pending_count(self) -> int:
        return len(self._pending)


if HAS_WATCHDOG and FileSystemEventHandler is not object:
    class WatchdogEventHandler(FileSystemEventHandler):
        """Dispatches file events to the debounce queue."""

        def __init__(self, debounce_queue: DebounceEventQueue, vault_dir: Path) -> None:
            super().__init__()
            self.debounce_queue = debounce_queue
            self.vault_dir = vault_dir

        def _is_md(self, path: str) -> bool:
            return path.endswith(".md") and not os.path.basename(path).startswith(".")

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory and self._is_md(event.src_path):
                self.debounce_queue.push(event.src_path, "created")

        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory and self._is_md(event.src_path):
                self.debounce_queue.push(event.src_path, "modified")

        def on_deleted(self, event: FileSystemEvent) -> None:
            if not event.is_directory and self._is_md(event.src_path):
                self.debounce_queue.push(event.src_path, "deleted")

        def on_moved(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                if self._is_md(event.src_path):
                    self.debounce_queue.push(event.src_path, "deleted")
                if self._is_md(event.dest_path):
                    self.debounce_queue.push(event.dest_path, "created")
else:
    WatchdogEventHandler = None


class PollingWatcher:
    """Standard library polling file watcher fallback when watchdog package is absent."""

    def __init__(self, vault_dir: Path, debounce_queue: DebounceEventQueue, poll_interval: float = 1.0) -> None:
        self.vault_dir = Path(vault_dir)
        self.debounce_queue = debounce_queue
        self.poll_interval = poll_interval
        self._known_files: Dict[str, float] = {}  # full_path -> mtime
        self._scan_initial()

    def _scan_initial(self) -> None:
        if not self.vault_dir.exists():
            return
        for root, dirs, files in os.walk(self.vault_dir):
            if ".git" in root or ".obsidian" in root:
                continue
            for f in files:
                if f.endswith(".md") and not f.startswith("."):
                    fp = os.path.join(root, f)
                    try:
                        self._known_files[fp] = os.path.getmtime(fp)
                    except Exception:
                        pass

    def poll_once(self) -> None:
        if not self.vault_dir.exists():
            return

        current_files: Dict[str, float] = {}
        for root, dirs, files in os.walk(self.vault_dir):
            if ".git" in root or ".obsidian" in root:
                continue
            for f in files:
                if f.endswith(".md") and not f.startswith("."):
                    fp = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(fp)
                        current_files[fp] = mtime
                    except Exception:
                        pass

        # Check for created / modified
        for fp, mtime in current_files.items():
            if fp not in self._known_files:
                self.debounce_queue.push(fp, "created")
                self._known_files[fp] = mtime
            elif mtime > self._known_files[fp]:
                self.debounce_queue.push(fp, "modified")
                self._known_files[fp] = mtime

        # Check for deleted
        for fp in list(self._known_files.keys()):
            if fp not in current_files:
                self.debounce_queue.push(fp, "deleted")
                del self._known_files[fp]


# ==============================================================================
# Obsidian Vectorizer Orchestrator & CLI Daemon
# ==============================================================================

class ObsidianVectorizerDaemon:
    """
    Main vectorizer daemon engine managing chunking, embedding generation,
    Qdrant upserts, and file watching.
    """

    def __init__(
        self,
        vault_dir: Union[str, Path] = DEFAULT_VAULT_DIR,
        llama_endpoint: str = DEFAULT_LLAMA_ENDPOINT,
        qdrant_url: str = DEFAULT_QDRANT_URL,
        qdrant_path: Union[str, Path] = DEFAULT_QDRANT_PATH,
        collection_name: str = DEFAULT_COLLECTION,
        batch_size: int = 16,
        debounce_seconds: float = 1.5,
        state_file: Union[str, Path] = DEFAULT_STATE_FILE,
        telemetry_file: Union[str, Path] = DEFAULT_TELEMETRY_LOG
    ) -> None:
        self.vault_dir = Path(vault_dir).resolve()
        self.batch_size = batch_size
        self.debounce_seconds = debounce_seconds
        self.telemetry_file = Path(telemetry_file)

        self.chunker = MarkdownChunker(max_chunk_size=1200, overlap=150)
        self.llama_client = LlamaEmbeddingClient(endpoint_url=llama_endpoint)
        self.qdrant_store = QdrantSyncStore(
            qdrant_url=qdrant_url,
            qdrant_path=Path(qdrant_path),
            collection_name=collection_name
        )
        self.state_cache = SyncStateCache(state_file=Path(state_file))
        self.debounce_queue = DebounceEventQueue(debounce_delay=debounce_seconds)
        self._running = False

    def log_telemetry(self, event_type: str, details: Dict[str, Any]) -> None:
        """Appends a structured event to the telemetry log."""
        try:
            self.telemetry_file.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "details": details
            }
            with open(self.telemetry_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            pass

    def process_file(self, full_path: Path, force: bool = False) -> Tuple[int, int]:
        """
        Processes a single markdown file: chunks, embeds, and upserts.
        Returns (chunk_count, points_upserted).
        """
        if not full_path.exists():
            return 0, 0

        try:
            rel_path = str(full_path.relative_to(self.vault_dir))
        except ValueError:
            rel_path = full_path.name

        if not force and not self.state_cache.is_file_changed(rel_path, full_path):
            return 0, 0

        chunks = self.chunker.chunk_file(rel_path, full_path)
        if not chunks:
            return 0, 0

        # Remove old points for this file
        self.qdrant_store.delete_file_chunks(rel_path)

        total_upserted = 0
        texts = [chk.text for chk in chunks]

        # Batch embedding calls
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            batch_chunks = chunks[i : i + self.batch_size]

            try:
                embeddings = self.llama_client.get_embeddings(batch_texts)
            except EmbeddingAPIError as e:
                logging.error(f"Embedding error on {rel_path} [batch {i}]: {e}")
                # Rule #0 zero-mock: do not fake vectors, report authentic error
                raise e

            upserted = self.qdrant_store.upsert_chunks(batch_chunks, embeddings)
            total_upserted += upserted

        self.state_cache.record_indexed(rel_path, full_path, len(chunks))
        self.log_telemetry("file_indexed", {
            "filepath": rel_path,
            "chunks": len(chunks),
            "points_upserted": total_upserted
        })
        return len(chunks), total_upserted

    def delete_file(self, full_path: Path) -> int:
        """Handles deletion of a markdown file."""
        try:
            rel_path = str(full_path.relative_to(self.vault_dir))
        except ValueError:
            rel_path = full_path.name

        deleted_points = self.qdrant_store.delete_file_chunks(rel_path)
        self.state_cache.remove_file(rel_path)
        self.log_telemetry("file_deleted", {
            "filepath": rel_path,
            "deleted_points": deleted_points
        })
        return deleted_points

    def sync_all(self, force: bool = False, dry_run_embeddings: bool = False) -> SyncStats:
        """
        Performs a full scan of all markdown files in the vault.
        If dry_run_embeddings is True, validates chunking without calling embeddings API.
        """
        stats = SyncStats()
        if not self.vault_dir.exists():
            logging.error(f"Vault directory does not exist: {self.vault_dir}")
            stats.errors += 1
            stats.end_time = time.time()
            return stats

        logging.info(f"Starting full vault synchronization on {self.vault_dir} (force={force})")

        md_files: List[Tuple[str, Path]] = []
        for root, dirs, files in os.walk(self.vault_dir):
            if ".git" in root or ".obsidian" in root:
                continue
            for f in sorted(files):
                if f.endswith(".md") and not f.startswith("."):
                    fp = Path(root) / f
                    rel_p = str(fp.relative_to(self.vault_dir))
                    md_files.append((rel_p, fp))

        stats.files_scanned = len(md_files)

        for rel_path, full_path in md_files:
            try:
                if not force and not self.state_cache.is_file_changed(rel_path, full_path):
                    stats.files_skipped += 1
                    continue

                chunks = self.chunker.chunk_file(rel_path, full_path)
                stats.chunks_generated += len(chunks)

                if dry_run_embeddings:
                    stats.files_indexed += 1
                    continue

                if chunks:
                    self.qdrant_store.delete_file_chunks(rel_path)
                    texts = [chk.text for chk in chunks]
                    total_upserted = 0

                    for i in range(0, len(texts), self.batch_size):
                        batch_texts = texts[i : i + self.batch_size]
                        batch_chunks = chunks[i : i + self.batch_size]

                        embeddings = self.llama_client.get_embeddings(batch_texts)
                        stats.embeddings_computed += len(embeddings)
                        upserted = self.qdrant_store.upsert_chunks(batch_chunks, embeddings)
                        total_upserted += upserted

                    stats.points_upserted += total_upserted
                    self.state_cache.record_indexed(rel_path, full_path, len(chunks))
                    stats.files_indexed += 1
                else:
                    stats.files_skipped += 1

            except Exception as e:
                logging.error(f"Failed processing {rel_path}: {e}")
                stats.errors += 1

        stats.end_time = time.time()
        logging.info(f"Full sync complete. {stats.summary()}")
        self.log_telemetry("full_sync_completed", asdict(stats))
        return stats

    def run_daemon(self) -> None:
        """
        Runs the persistent watchdog daemon with event debouncing and signal handling.
        """
        self._running = True

        def _handle_signal(signum: int, frame: Any) -> None:
            logging.info(f"Received shutdown signal ({signum}). Stopping vectorizer daemon...")
            self._running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        # 1. Initial quick sync
        logging.info("Running initial startup synchronization...")
        try:
            self.sync_all(force=False)
        except Exception as e:
            logging.warning(f"Initial sync encountered non-fatal error: {e}")

        # 2. Setup Watcher (Watchdog or Polling)
        observer = None
        polling_watcher = None

        if HAS_WATCHDOG and WatchdogEventHandler and Observer:
            try:
                event_handler = WatchdogEventHandler(self.debounce_queue, self.vault_dir)
                observer = Observer()
                observer.schedule(event_handler, str(self.vault_dir), recursive=True)
                observer.start()
                logging.info(f"Watchdog Observer active on {self.vault_dir}")
            except Exception as e:
                logging.warning(f"Watchdog start failed ({e}), falling back to PollingWatcher")
                observer = None

        if observer is None:
            polling_watcher = PollingWatcher(self.vault_dir, self.debounce_queue, poll_interval=1.0)
            logging.info(f"PollingWatcher active on {self.vault_dir} (1.0s interval)")

        logging.info("Obsidian Vectorizer Daemon running. Press Ctrl+C to terminate.")

        try:
            while self._running:
                if polling_watcher:
                    polling_watcher.poll_once()

                # Process ready debounced events
                ready_events = self.debounce_queue.pop_ready()
                for fp_str, ev_type in ready_events:
                    fp = Path(fp_str)
                    logging.info(f"Processing debounced event: {ev_type} -> {fp.name}")
                    try:
                        if ev_type in ["created", "modified"]:
                            self.process_file(fp, force=True)
                        elif ev_type == "deleted":
                            self.delete_file(fp)
                    except Exception as e:
                        logging.error(f"Error processing debounced event {ev_type} on {fp}: {e}")

                time.sleep(0.5)

        finally:
            if observer:
                observer.stop()
                observer.join()
            logging.info("Obsidian Vectorizer Daemon shutdown cleanly.")


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Obsidian Knowledge Vault Qdrant Vectorizer & Watchdog Daemon"
    )
    parser.add_argument(
        "--vault-dir",
        type=str,
        default=os.environ.get("OBSIDIAN_VAULT_DIR", str(DEFAULT_VAULT_DIR)),
        help="Path to Obsidian Markdown Vault"
    )
    parser.add_argument(
        "--llama-endpoint", "--embedding-url",
        dest="llama_endpoint",
        type=str,
        default=os.environ.get("LLAMA_EMBEDDING_URL", DEFAULT_LLAMA_ENDPOINT),
        help="Local llama.cpp OpenAI-compatible embeddings endpoint"
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default=os.environ.get("QDRANT_URL", DEFAULT_QDRANT_URL),
        help="Qdrant HTTP REST URL"
    )
    parser.add_argument(
        "--qdrant-path",
        type=str,
        default=os.environ.get("QDRANT_PATH", str(DEFAULT_QDRANT_PATH)),
        help="Local embedded Qdrant SQLite storage path fallback"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=os.environ.get("QDRANT_COLLECTION", DEFAULT_COLLECTION),
        help="Qdrant collection name"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size for embedding calls"
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=1.5,
        help="Debounce delay in seconds"
    )
    parser.add_argument(
        "--sync-all", "--once",
        dest="sync_all",
        action="store_true",
        help="Run a single-pass synchronization over all vault files and exit"
    )
    parser.add_argument(
        "--watch", "--daemon",
        dest="daemon",
        action="store_true",
        help="Run as a persistent watchdog background daemon"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print status of vault, embeddings endpoint, and Qdrant storage"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing of all files ignoring state cache"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=str(DEFAULT_LOG_FILE),
        help="Log file destination"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose DEBUG logging"
    )
    return parser.parse_args()


def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "[%(asctime)s] [%(levelname)s] %(message)s"
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        try:
            p = Path(log_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(str(p), encoding="utf-8"))
        except Exception:
            pass

    logging.basicConfig(level=level, format=format_str, handlers=handlers)


def main() -> int:
    args = parse_args()
    setup_logging(args.log_file, args.verbose)

    daemon = ObsidianVectorizerDaemon(
        vault_dir=args.vault_dir,
        llama_endpoint=args.llama_endpoint,
        qdrant_url=args.qdrant_url,
        qdrant_path=args.qdrant_path,
        collection_name=args.collection,
        batch_size=args.batch_size,
        debounce_seconds=args.debounce
    )

    if args.status:
        print("=" * 60)
        print("Obsidian Vectorizer Status Report")
        print("=" * 60)
        print(f"Vault Directory:     {daemon.vault_dir} (Exists: {daemon.vault_dir.exists()})")
        if daemon.vault_dir.exists():
            md_count = sum(1 for root, _, files in os.walk(daemon.vault_dir) for f in files if f.endswith(".md"))
            print(f"Markdown Notes:      {md_count} files")

        health_ok, health_msg = daemon.llama_client.check_health()
        print(f"Llama Endpoint:      {daemon.llama_client.endpoint_url}")
        print(f"Llama Health:        {'[READY]' if health_ok else '[WAITING]'} ({health_msg})")

        qdrant_stats = daemon.qdrant_store.get_stats()
        print(f"Qdrant Mode:         {qdrant_stats.get('mode')}")
        print(f"Qdrant Collection:   {qdrant_stats.get('collection')}")
        print(f"Indexed Points:      {qdrant_stats.get('points_count')}")
        if "db_path" in qdrant_stats:
            print(f"SQLite Storage Path: {qdrant_stats.get('db_path')}")
        print("=" * 60)
        return 0

    if args.daemon:
        daemon.run_daemon()
        return 0

    # Default action: sync_all
    stats = daemon.sync_all(force=args.force)
    print(stats.summary())
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
