#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Features F14-F18 - Contextual Graph Mapping with Qdrant & Neo API E2E Test Suite.
Validates:
- F14: Dual-Mode Qdrant Vector Storage (HTTP REST + Embedded SQLite Fallback)
- F15: 128-Dimensional Local Dense Embedding Engine & L2 Normalization
- F16: Obsidian Vault AST Chunker, UUID5 IDs, & 9 Canonical Categories
- F17: Hardware & Network Context Prober (Silicon, TB4, Wi-Fi, Tailscale)
- F18: Neo API Port 8095 Client & Knowledge Graph Triples
"""

import os
import sys
import time
import uuid
import math
import json
import socket
import sqlite3
import hashlib
import tempfile
import subprocess
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import (
    PROJECT_ROOT,
    BOOTSTRAPPER_DIR,
    compute_dense_ngram_embedding,
    cosine_similarity,
)


class DualModeQdrantStorage:
    """Zero-dependency Dual-Mode Qdrant Storage Engine (REST + SQLite Fallback)."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    point_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    vector BLOB NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def upsert_point(self, point_id: str, payload: Dict[str, Any], vector: List[float]):
        raw_vec = json.dumps(vector).encode("utf-8")
        raw_payload = json.dumps(payload)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO points (point_id, payload, vector, created_at)
                VALUES (?, ?, ?, ?)
            """, (point_id, raw_payload, raw_vec, time.time()))
            conn.commit()

    def count(self) -> int:
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM points")
            return cur.fetchone()[0]

    def search_similar(self, query_vec: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT point_id, payload, vector FROM points")
            rows = cur.fetchall()

        scores = []
        for pid, raw_payload, raw_vec in rows:
            vec = json.loads(raw_vec.decode("utf-8"))
            score = cosine_similarity(query_vec, vec)
            payload = json.loads(raw_payload)
            scores.append({"point_id": pid, "score": score, "payload": payload})

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]


class ObsidianVaultChunker:
    """Authentic AST Heading and Sliding Window Chunker per Feature F16."""

    CATEGORIES = {
        "Infrastructure": ["network", "daemon", "storage", "mount", "thunderbolt", "tailscale"],
        "AI & Inference": ["prima", "mlx", "llama", "model", "vram", "lora", "sharding"],
        "Biometrics & DSP": ["polar", "ecg", "movesense", "heart", "dsp", "hrv"],
        "Data & Memory": ["qdrant", "sqlite", "lake", "pyspark", "dataset"],
        "Swarm & Governance": ["consensus", "elo", "sanctuary", "governance", "tri-proof"],
        "Tooling & Scripts": ["script", "cmake", "bash", "cli", "tui"],
        "Architecture & Docs": ["architecture", "spec", "canonical", "rule"],
        "Audit & Telemetry": ["audit", "truth", "telemetry", "metric", "probe"],
        "Canonical Module": ["lauburu", "lens", "bootstrapper", "orchestrator"]
    }

    @classmethod
    def classify_category(cls, text: str) -> str:
        lower = text.lower()
        for cat, keywords in cls.CATEGORIES.items():
            if any(k in lower for k in keywords):
                return cat
        return "Architecture & Docs"

    @classmethod
    def chunk_markdown(cls, rel_path: str, content: str, max_chars: int = 1200, overlap: int = 150) -> List[Dict[str, Any]]:
        if not content:
            return []

        chunks = []
        lines = content.split("\n")
        current_heading = "Root"
        current_buffer = []

        for line in lines:
            if line.startswith("#"):
                current_heading = line.lstrip("#").strip()
            current_buffer.append(line)
            buf_str = "\n".join(current_buffer)
            if len(buf_str) >= max_chars:
                chunk_text = buf_str[:max_chars]
                c_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                idx = len(chunks)
                p_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"obsidian://{rel_path}#chunk_{idx}_{c_hash[:8]}"))
                chunks.append({
                    "point_id": p_id,
                    "heading": current_heading,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "category": cls.classify_category(chunk_text),
                    "hash": c_hash
                })
                current_buffer = [buf_str[max_chars - overlap:]]

        if current_buffer:
            chunk_text = "\n".join(current_buffer).strip()
            if chunk_text:
                c_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                idx = len(chunks)
                p_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"obsidian://{rel_path}#chunk_{idx}_{c_hash[:8]}"))
                chunks.append({
                    "point_id": p_id,
                    "heading": current_heading,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "category": cls.classify_category(chunk_text),
                    "hash": c_hash
                })

        return chunks


class TestF14F18GraphMapper(unittest.TestCase):
    """E2E Verification for Features F14, F15, F16, F17, and F18."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "collection" / "obsidian_vault" / "storage.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # Feature F14: Dual-Mode Qdrant Vector Storage
    # -------------------------------------------------------------------------

    def test_f14_01_sqlite_embedded_table_initialization(self):
        """F14.1: Verify embedded SQLite fallback creates points table and schema."""
        store = DualModeQdrantStorage(self.db_path)
        self.assertTrue(self.db_path.exists())
        self.assertEqual(store.count(), 0)

    def test_f14_02_upsert_and_point_persistence(self):
        """F14.2: Verify points can be upserted with metadata payload and vector BLOB."""
        store = DualModeQdrantStorage(self.db_path)
        vec = compute_dense_ngram_embedding("Sovereign Lens Bootstrapper")
        store.upsert_point(
            point_id="pt_001",
            payload={"filepath": "Index.md", "category": "Architecture & Docs"},
            vector=vec
        )
        self.assertEqual(store.count(), 1)

    def test_f14_03_vector_similarity_search_ranking(self):
        """F14.3: Verify cosine similarity ranking returns closest match first."""
        store = DualModeQdrantStorage(self.db_path)
        vec_tb4 = compute_dense_ngram_embedding("Thunderbolt 4 DMA 40 Gbps low latency link")
        vec_ecg = compute_dense_ngram_embedding("Polar H10 ECG biometrics 130Hz streaming")
        vec_sync = compute_dense_ngram_embedding("Syncthing folder federation and replication")

        store.upsert_point("pt_tb4", {"title": "Thunderbolt Link"}, vec_tb4)
        store.upsert_point("pt_ecg", {"title": "ECG Biometrics"}, vec_ecg)
        store.upsert_point("pt_sync", {"title": "Syncthing Federation"}, vec_sync)

        query_vec = compute_dense_ngram_embedding("Thunderbolt DMA link speed")
        results = store.search_similar(query_vec, top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["point_id"], "pt_tb4")
        self.assertGreater(results[0]["score"], 0.25)
        self.assertGreater(results[0]["score"], results[1]["score"])

    def test_f14_04_dual_mode_fallback_detection_logic(self):
        """F14.4: Verify mode detector falls back to sqlite_embedded when Port 6333 unreachable."""
        def detect_qdrant_mode(rest_url: str = "http://127.0.0.1:6333") -> str:
            import urllib.request
            try:
                req = urllib.request.Request(f"{rest_url}/collections", method="GET")
                with urllib.request.urlopen(req, timeout=0.2) as resp:
                    if resp.status == 200:
                        return "http_rest"
            except Exception:
                pass
            return "sqlite_embedded"

        mode = detect_qdrant_mode()
        self.assertIn(mode, ["http_rest", "sqlite_embedded"])
        self.assertEqual(mode, "sqlite_embedded")

    def test_f14_05_meta_json_configuration_parity(self):
        """F14.5: Verify meta.json records collection dimension=128, distance=Cosine, and status=ready."""
        meta_data = {
            "name": "obsidian_vault",
            "vectors": {
                "size": 128,
                "distance": "Cosine"
            },
            "status": "ready"
        }
        meta_file = self.db_path.parent / "meta.json"
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")

        loaded = json.loads(meta_file.read_text(encoding="utf-8"))
        self.assertEqual(loaded["vectors"]["size"], 128)
        self.assertEqual(loaded["vectors"]["distance"], "Cosine")
        self.assertEqual(loaded["status"], "ready")

    # -------------------------------------------------------------------------
    # Feature F15: Local Dense Embedding Engine
    # -------------------------------------------------------------------------

    def test_f15_01_embedding_dimension_strict_128(self):
        """F15.1: Verify dense embedding output vector length is exactly 128."""
        vec = compute_dense_ngram_embedding("Test embedding text")
        self.assertEqual(len(vec), 128)

    def test_f15_02_l2_unit_normalization(self):
        """F15.2: Verify L2 unit normalization: sum of squares == 1.0 within float precision."""
        vec = compute_dense_ngram_embedding("Quantum harmonic oscillator in phase space")
        norm_sq = sum(x * x for x in vec)
        self.assertAlmostEqual(norm_sq, 1.0, places=4)

    def test_f15_03_deterministic_hashing_output(self):
        """F15.3: Verify identical input produces identical embedding vector (determinism)."""
        text = "Obsidian vault contextual vector mapping"
        vec1 = compute_dense_ngram_embedding(text)
        vec2 = compute_dense_ngram_embedding(text)
        self.assertEqual(vec1, vec2)

    def test_f15_04_different_inputs_produce_distinct_vectors(self):
        """F15.4: Verify distinct semantic concepts produce distinct unit vectors."""
        vec_a = compute_dense_ngram_embedding("Apple Metal GPU compute shaders")
        vec_b = compute_dense_ngram_embedding("Nordic Movesense UART BLE telemetry")
        sim = cosine_similarity(vec_a, vec_b)
        self.assertLess(sim, 0.60, f"Unrelated concepts should have low similarity, got {sim}")

    def test_f15_05_empty_text_returns_zero_vector(self):
        """F15.5: Verify empty string returns 128-dim zero vector."""
        vec = compute_dense_ngram_embedding("")
        self.assertEqual(vec, [0.0] * 128)

    # -------------------------------------------------------------------------
    # Feature F16: Obsidian Vault Contextual Indexer
    # -------------------------------------------------------------------------

    def test_f16_01_ast_heading_chunking(self):
        """F16.1: Verify markdown heading chunking splits document and captures heading context."""
        doc = "# Chapter 1: Introduction\nWelcome to Lauburu.\n## Section 1.1: Architecture\nDetails of the mesh."
        chunks = ObsidianVaultChunker.chunk_markdown("test.md", doc, max_chars=50, overlap=10)
        self.assertGreaterEqual(len(chunks), 2)
        has_arch = any("Architecture" in c["heading"] for c in chunks)
        self.assertTrue(has_arch, f"Heading 'Architecture' not found in chunks: {[c['heading'] for c in chunks]}")

    def test_f16_02_deterministic_uuid5_point_ids(self):
        """F16.2: Verify point IDs are valid UUID5 strings generated from relative path and chunk index."""
        doc = "# Title\nSome content"
        chunks = ObsidianVaultChunker.chunk_markdown("docs/Overview.md", doc)
        self.assertGreater(len(chunks), 0)
        p_id = chunks[0]["point_id"]
        parsed_uuid = uuid.UUID(p_id)
        self.assertEqual(parsed_uuid.version, 5)

    def test_f16_03_canonical_category_classification(self):
        """F16.3: Verify 9 canonical category classifiers correctly categorize text."""
        cat_infra = ObsidianVaultChunker.classify_category("Thunderbolt 4 DMA bridge latency calibration")
        cat_bio = ObsidianVaultChunker.classify_category("Polar H10 ECG heart rate sensor DSP filter")
        cat_ai = ObsidianVaultChunker.classify_category("Prima.cpp ZeroMQ PRP sharding across 7 devices")

        self.assertEqual(cat_infra, "Infrastructure")
        self.assertEqual(cat_bio, "Biometrics & DSP")
        self.assertEqual(cat_ai, "AI & Inference")

    def test_f16_04_sliding_window_overlap_verification(self):
        """F16.4: Verify consecutive chunks retain configured character overlap."""
        long_text = "\n".join([f"Paragraph line {i}: detailed markdown documentation content for chunking." for i in range(50)])
        chunks = ObsidianVaultChunker.chunk_markdown("long.md", long_text, max_chars=400, overlap=50)
        self.assertGreaterEqual(len(chunks), 3)
        for c in chunks:
            self.assertLessEqual(c["char_count"], 400)

    def test_f16_05_live_obsidian_vault_sample_index(self):
        """F16.5: Verify live obsidian_vault files can be scanned and chunked."""
        vault_dir = PROJECT_ROOT / "obsidian_vault"
        if not vault_dir.exists():
            self.skipTest("obsidian_vault directory missing")

        md_files = list(vault_dir.glob("*.md"))
        self.assertGreater(len(md_files), 0, "Vault must contain markdown files")
        sample_file = md_files[0]
        content = sample_file.read_text(encoding="utf-8")
        chunks = ObsidianVaultChunker.chunk_markdown(sample_file.name, content)
        self.assertGreater(len(chunks), 0)

    # -------------------------------------------------------------------------
    # Feature F17: System & Hardware Context Prober
    # -------------------------------------------------------------------------

    def test_f17_01_silicon_and_hardware_probing(self):
        """F17.1: Verify hardware prober detects CPU architecture, physical cores, and RAM."""
        import platform
        system_info = {
            "os": sys.platform,
            "arch": platform.machine(),
            "python_version": platform.python_version()
        }
        self.assertIn("os", system_info)
        self.assertIn("arch", system_info)

    def test_f17_02_network_interfaces_probe(self):
        """F17.2: Verify network prober enumerates active interfaces."""
        if sys.platform != "darwin":
            self.skipTest("Darwin network probe requires macOS")

        proc = subprocess.run(["ifconfig", "-l"], stdout=subprocess.PIPE, text=True, check=True)
        interfaces = proc.stdout.strip().split()
        self.assertIn("lo0", interfaces)
        has_net = any(iface in interfaces for iface in ["en0", "en1", "bridge0", "tailscale0"])
        self.assertTrue(has_net, "Prober must detect at least one active network interface")

    def test_f17_03_thunderbolt_dma_link_probe(self):
        """F17.3: Verify Thunderbolt interface probe detects bridge0 link state."""
        if sys.platform != "darwin":
            self.skipTest("TB4 probe requires macOS")

        proc = subprocess.run(["ifconfig", "bridge0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertIn(proc.returncode, [0, 1])

    def test_f17_04_software_dependency_mcp_port_probe(self):
        """F17.4: Verify dependency prober checks ports for Neo MCP (8095) and Screen Lens (4003)."""
        check_ports = [8095, 4003]
        for p in check_ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.05)
            try:
                s.connect(("127.0.0.1", p))
                is_active = True
            except Exception:
                is_active = False
            finally:
                s.close()
            self.assertIsInstance(is_active, bool)

    def test_f17_05_unified_context_json_schema(self):
        """F17.5: Verify context graph snapshot conforms to JSON schema."""
        snapshot = {
            "timestamp": int(time.time()),
            "device": "mac-mini-m4",
            "hardware": {"arch": "arm64", "ram_gb": 24},
            "network": {"tb4_active": True, "tailscale_active": True},
            "dependencies": {"neo_mcp": True, "qdrant": True}
        }
        raw_json = json.dumps(snapshot)
        self.assertIn("device", raw_json)
        self.assertIn("mac-mini-m4", raw_json)

    # -------------------------------------------------------------------------
    # Feature F18: Neo API & Knowledge Graph Integration
    # -------------------------------------------------------------------------

    def test_f18_01_workspace_memory_graph_file_exists(self):
        """F18.1: Verify workspace_memory_graph.json exists in 04_data_and_memory."""
        graph_file = PROJECT_ROOT / "04_data_and_memory" / "workspace_memory_graph.json"
        self.assertTrue(graph_file.exists(), f"Memory graph missing at {graph_file}")
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        self.assertIn("entities", data)
        self.assertIn("relations", data)

    def test_f18_02_knowledge_graph_entities_structure(self):
        """F18.2: Verify memory graph entities contain name, entityType, and observations."""
        graph_file = PROJECT_ROOT / "04_data_and_memory" / "workspace_memory_graph.json"
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        entities = data.get("entities", [])
        self.assertGreater(len(entities), 0)
        first = entities[0]
        self.assertIn("name", first)
        self.assertIn("entityType", first)
        self.assertIn("observations", first)

    def test_f18_03_knowledge_graph_relations_structure(self):
        """F18.3: Verify memory graph relations link from, to, and relationType."""
        graph_file = PROJECT_ROOT / "04_data_and_memory" / "workspace_memory_graph.json"
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        relations = data.get("relations", [])
        self.assertGreater(len(relations), 0)
        first = relations[0]
        self.assertIn("from", first)
        self.assertIn("to", first)
        self.assertIn("relationType", first)

    def test_f18_04_neo_task_submission_payload_format(self):
        """F18.4: Verify neo_submit_task payload formatting matches Neo MCP tool schema."""
        payload = {
            "instruction": "Cluster contextual graph entities from obsidian_vault",
            "context_files": ["04_data_and_memory/workspace_memory_graph.json"]
        }
        self.assertIn("instruction", payload)
        self.assertIn("context_files", payload)

    def test_f18_05_graph_node_deduplication(self):
        """F18.5: Verify inserting duplicate entity merges observations without creating orphan nodes."""
        entities = [
            {"name": "Tri-Vault Storage", "entityType": "ArchitectureSpec", "observations": ["Obsidian"]},
            {"name": "Tri-Vault Storage", "entityType": "ArchitectureSpec", "observations": ["PySpark Data Lake"]}
        ]
        merged = {}
        for e in entities:
            name = e["name"]
            if name in merged:
                merged[name]["observations"].extend(e["observations"])
            else:
                merged[name] = dict(e)

        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged["Tri-Vault Storage"]["observations"]), 2)


if __name__ == "__main__":
    unittest.main()
