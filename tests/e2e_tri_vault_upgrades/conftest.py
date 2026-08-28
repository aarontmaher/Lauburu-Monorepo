"""
Pytest fixtures and test harnesses for the Tri-Vault Storage Upgrades E2E Suite.
Provides temporary vaults, Delta Lake directories, embedded Qdrant stores,
module accessors, and local live HTTP embedding server fixtures.
"""
from __future__ import annotations

import os
import sys
import time
import json
import socket
import shutil
import tempfile
import threading
import hashlib
import importlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Generator, Dict, Any, List

import pytest

# Ensure monorepo root is on sys.path
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo").resolve()
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))

# Dynamically import numbered monorepo packages
delta_schema_mod = importlib.import_module("04_data_and_memory.delta_engine.schema")
delta_writer_mod = importlib.import_module("04_data_and_memory.delta_engine.writer")
delta_compactor_mod = importlib.import_module("04_data_and_memory.delta_engine.compactor")
delta_mmap_loader_mod = importlib.import_module("04_data_and_memory.delta_engine.mmap_loader")
obsidian_vectorizer_mod = importlib.import_module("04_data_and_memory.qdrant_sync.obsidian_vectorizer")


class LiveEmbeddingHTTPHandler(BaseHTTPRequestHandler):
    """
    Lightweight, authentic HTTP server implementing OpenAI / llama.cpp /v1/embeddings spec.
    Computes deterministic unit-normalized embeddings via SHA-256 seed for real HTTP socket tests.
    """

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logging during test execution
        pass

    def do_GET(self) -> None:
        if self.path in ("/health", "/v1/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "models": ["embedding-v1"]}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path.endswith("/v1/embeddings") or self.path.endswith("/embeddings"):
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                texts = data.get("input", [])
                if isinstance(texts, str):
                    texts = [texts]

                # Generate deterministic 128-dimensional embedding vectors
                results = []
                for idx, text in enumerate(texts):
                    # Deterministic pseudo-vector derived from sha256
                    h = hashlib.sha256(text.encode("utf-8")).digest()
                    # 128 floats between -1.0 and 1.0
                    raw_vec = []
                    for i in range(128):
                        byte_val = h[i % len(h)]
                        raw_vec.append(round((byte_val - 128) / 128.0, 6))

                    # Normalize vector
                    magnitude = sum(x * x for x in raw_vec) ** 0.5 or 1.0
                    normalized_vec = [round(x / magnitude, 6) for x in raw_vec]

                    results.append({
                        "object": "embedding",
                        "index": idx,
                        "embedding": normalized_vec
                    })

                resp_payload = {
                    "object": "list",
                    "data": results,
                    "model": data.get("model", "embedding"),
                    "usage": {"prompt_tokens": len(texts) * 10, "total_tokens": len(texts) * 10}
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="session")
def live_embedding_server() -> Generator[str, None, None]:
    """
    Spins up an authentic in-process HTTP embedding server on a dynamic open port.
    Returns the endpoint URL (e.g. http://127.0.0.1:PORT/v1/embeddings).
    """
    server = HTTPServer(("127.0.0.1", 0), LiveEmbeddingHTTPHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    endpoint = f"http://127.0.0.1:{port}/v1/embeddings"
    yield endpoint

    server.shutdown()
    server.server_close()


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Creates an isolated temporary directory for test artifacts."""
    temp_dir = Path(tempfile.mkdtemp(prefix="tri_vault_test_"))
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_vault_dir(temp_workspace: Path) -> Path:
    """Populates a realistic Obsidian Vault with diverse markdown documents."""
    vault = temp_workspace / "obsidian_vault"
    vault.mkdir(parents=True, exist_ok=True)

    # Note 1: 00_core_infrastructure.md (Canonical Module)
    note1 = vault / "00_core_infrastructure.md"
    note1.write_text(
        "---\n"
        "title: \"00 Core Infrastructure Specification\"\n"
        "tags: [seaweedfs, docker, tailscale, layer6]\n"
        "category: \"Infrastructure\"\n"
        "updated: \"2026-08-28T00:00:00Z\"\n"
        "---\n"
        "# 00 Core Infrastructure\n\n"
        "## SeaweedFS Distributed Storage\n"
        "The distributed cluster spans Layer 1 (Mac Mini M4 Pro) and Layer 6 (Pixel 10 Pro XL).\n"
        "Volume servers bind to 100.73.38.87 with 500GB local storage.\n\n"
        "## Cloud Tiering Policy\n"
        "Cloudflare R2 provides cold tiering with force_path_style S3 access.\n",
        encoding="utf-8"
    )

    # Note 2: 04_data_and_memory.md (Data & Memory)
    note2 = vault / "04_data_and_memory.md"
    note2.write_text(
        "---\n"
        "title: \"04 Data and Memory Pipeline\"\n"
        "tags: [delta_lake, parquet, mmap, pyspark, qdrant]\n"
        "category: \"Data & Memory\"\n"
        "---\n"
        "# 04 Data and Memory\n\n"
        "## Delta-rs Compaction\n"
        "PySpark crawlers write ACID Delta tables with automated bin-packing.\n\n"
        "## Zero-Copy Memory Mapping\n"
        "HuggingFace datasets leverage mmap over Thunderbolt 4 with zero RAM bloat (<50MB RSS).\n",
        encoding="utf-8"
    )

    # Note 3: Subdirectory note in 01_DEBATES/
    debates_dir = vault / "01_DEBATES"
    debates_dir.mkdir(parents=True, exist_ok=True)
    note3 = debates_dir / "DEBATE_2026_08_28_TRI_VAULT.md"
    note3.write_text(
        "# Tri-Vault Storage Consensus Debate\n\n"
        "## Debate Participants\n"
        "- Gemini 3.1 Pro High\n"
        "- Gemini 3.7 Flash High\n"
        "- Kimi Tandem\n\n"
        "## Consensus Verdict\n"
        "Unanimously ratified Delta Lake parquet compaction and 500GB Pixel 10 Pro volume allocation.\n"
        "#consensus #swarm #governance\n",
        encoding="utf-8"
    )

    return vault


@pytest.fixture
def canonical_paths() -> Dict[str, Path]:
    """Provides validated paths to monorepo directories and scripts."""
    return {
        "monorepo": MONOREPO_ROOT,
        "seaweedfs_dir": MONOREPO_ROOT / "00_core_infrastructure" / "seaweedfs",
        "pixel_script": MONOREPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "pixel_volume_daemon.sh",
        "r2_config": MONOREPO_ROOT / "00_core_infrastructure" / "seaweedfs" / "r2_tiering_config.json",
        "delta_engine_dir": MONOREPO_ROOT / "04_data_and_memory" / "delta_engine",
        "qdrant_sync_dir": MONOREPO_ROOT / "04_data_and_memory" / "qdrant_sync",
        "vectorizer_script": MONOREPO_ROOT / "04_data_and_memory" / "qdrant_sync" / "obsidian_vectorizer.py",
        "obsidian_vault": MONOREPO_ROOT / "obsidian_vault",
    }


# Export imported modules for test files
@pytest.fixture
def delta_engine():
    return {
        "schema": delta_schema_mod,
        "writer": delta_writer_mod,
        "compactor": delta_compactor_mod,
        "mmap_loader": delta_mmap_loader_mod,
    }


@pytest.fixture
def vectorizer_engine():
    return obsidian_vectorizer_mod
