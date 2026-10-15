"""
04_data_and_memory/tests/test_pyspark_semantic_dedup.py
Unit and integration tests for PySpark Semantic Deduplicator:
- Shannon Entropy filtering (H >= 3.20 bits/token).
- Qdrant Vector Clustering (Cosine Similarity >= 0.92).
- Embedded SQLite storage and JSONL streaming deduplication.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

DATA_MEM_DIR = Path(__file__).resolve().parents[1]
if str(DATA_MEM_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_MEM_DIR))

from pyspark_analytics.pyspark_semantic_dedup import (
    PySparkSemanticDeduplicator,
    QdrantVectorStore,
    DedupReport,
    compute_shannon_entropy,
    compute_cosine_similarity,
    vectorize_text,
)


def test_shannon_entropy_calculation():
    """Verifies Shannon entropy calculation across high and low entropy texts."""
    # High entropy text: diverse natural language sentence with varied vocabulary
    high_entropy_text = (
        "The distributed AI inference mesh orchestrates tensor sharding across heterogeneous "
        "hardware nodes including Apple Silicon Metal, Linux AMD Ryzen Ray clusters, and Edge TPUs."
    )
    h_high = compute_shannon_entropy(high_entropy_text, mode="token")
    assert h_high >= 3.20, f"Expected high entropy >= 3.20 bits/token, got {h_high}"

    # Low entropy text: degenerate repetition
    low_entropy_rep = "repeat repeat repeat repeat repeat repeat repeat repeat repeat repeat"
    h_low_rep = compute_shannon_entropy(low_entropy_rep, mode="token")
    assert h_low_rep < 3.20, f"Expected low entropy < 3.20 bits/token, got {h_low_rep}"
    assert h_low_rep == 0.0  # 1 unique token = 0 bits

    # Single character repetition
    h_char_rep = compute_shannon_entropy("aaaaaaaaaaaaaaaaaaaa", mode="token")
    assert h_char_rep < 3.20

    # Empty string
    assert compute_shannon_entropy("", mode="token") == 0.0
    assert compute_shannon_entropy("   ", mode="token") == 0.0


def test_cosine_similarity_calculation():
    """Verifies cosine similarity properties: identical = 1.0, orthogonal = 0.0."""
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert pytest.approx(compute_cosine_similarity(v1, v2), abs=1e-5) == 1.0
    assert pytest.approx(compute_cosine_similarity(v1, v3), abs=1e-5) == 0.0

    # Zero vector handling
    v_zero = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    assert compute_cosine_similarity(v1, v_zero) == 0.0


def test_vectorize_text_deterministic():
    """Verifies that vectorization produces unit-normalized deterministic vectors."""
    text1 = "Automated Tri-Vault storage self-healing and PySpark vector clustering."
    text2 = "Automated Tri-Vault storage self-healing and PySpark vector clustering."
    text3 = "Completely distinct topic about biometrics and ECG Pan-Tompkins detection."

    v1 = vectorize_text(text1, dim=256)
    v2 = vectorize_text(text2, dim=256)
    v3 = vectorize_text(text3, dim=256)

    assert v1.shape == (256,)
    assert pytest.approx(np.linalg.norm(v1), abs=1e-4) == 1.0
    assert np.allclose(v1, v2)

    sim_identical = compute_cosine_similarity(v1, v2)
    sim_different = compute_cosine_similarity(v1, v3)

    assert pytest.approx(sim_identical, abs=1e-4) == 1.0
    assert sim_different < 0.92


def test_deduplicate_dataset_removes_duplicates_and_low_entropy():
    """Verifies that deduplicator clusters cosine >= 0.92 and removes entropy < 3.20."""
    dedup = PySparkSemanticDeduplicator(
        cosine_threshold=0.92,
        min_shannon_entropy=3.20,
        vector_dim=256,
    )

    records = [
        # Item 1: High entropy unique instruction
        {
            "pair_id": "sample_001",
            "instruction": "Explain how to configure distributed tensor sharding using llama.cpp RPC over 10Gbps Thunderbolt bridge.",
            "solution": "Configure RPC server on port 8081 with Metal GPU acceleration and specify host parameters.",
            "truth_verified": False,
        },
        # Item 2: Duplicate of Item 1 (near-identical instruction with identical semantics)
        {
            "pair_id": "sample_001_dup",
            "instruction": "Explain how to configure distributed tensor sharding using llama.cpp RPC over 10Gbps Thunderbolt bridge.",
            "solution": "Configure RPC server on port 8081 with Metal GPU acceleration and specify host parameters with verification.",
            "truth_verified": True,  # Higher quality / verified
        },
        # Item 3: Distinct high-entropy instruction
        {
            "pair_id": "sample_002",
            "instruction": "Implement real-time Pan-Tompkins QRS algorithm for 512Hz Movesense ECG biometrics stream.",
            "solution": "Bandpass filter using 5-15Hz Butterworth, differentiate, square, and apply moving window integration.",
            "truth_verified": True,
        },
        # Item 4: Distinct high-entropy instruction
        {
            "pair_id": "sample_003",
            "instruction": "Detail the Bradley-Terry ELO tournament rating system for evaluating fine-tuned LoRA adapters.",
            "solution": "Conduct pairwise battles between candidate adapters and compute logistic win probabilities with 65% threshold.",
            "truth_verified": True,
        },
        # Item 5: Low-entropy degenerate sample (< 3.20 bits/token)
        {
            "pair_id": "sample_low_01",
            "instruction": "test test test test test test test test test test",
            "solution": "test test test test test test test test test test",
            "truth_verified": False,
        },
        # Item 6: Low-entropy repetitive sample
        {
            "pair_id": "sample_low_02",
            "instruction": "echo echo echo echo echo echo echo echo",
            "solution": "echo echo echo echo echo echo echo echo",
            "truth_verified": False,
        },
    ]

    dedup_records, report = dedup.cluster_and_deduplicate(records)

    assert report.total_samples == 6
    assert report.low_entropy_removed == 2
    assert report.duplicates_removed == 1
    assert report.retained_samples == 3
    assert len(dedup_records) == 3
    assert report.clusters_formed == 3
    assert report.retention_rate == 0.5  # 3/6

    # Verify that the verified duplicate was promoted as the cluster representative
    retained_ids = [r["pair_id"] for r in dedup_records]
    assert "sample_001_dup" in retained_ids
    assert "sample_002" in retained_ids
    assert "sample_003" in retained_ids
    assert "sample_low_01" not in retained_ids
    assert "sample_low_02" not in retained_ids


def test_qdrant_sqlite_vector_store(tmp_path: Path):
    """Verifies embedded Qdrant SQLite storage initialization, upsert, and point retrieval."""
    qdrant_dir = tmp_path / "qdrant_data"
    store = QdrantVectorStore(
        qdrant_path=qdrant_dir,
        collection_name="test_collection",
        vector_dim=128,
    )

    assert (qdrant_dir / "collection" / "test_collection" / "storage.sqlite").exists()
    assert store.count_points() == 0

    v1 = np.ones(128, dtype=np.float32) / np.sqrt(128)
    store.upsert_point(
        point_id="pt_001",
        vector=v1,
        payload={"task": "test_qdrant_vector", "score": 98.5},
        entropy=4.25,
        cluster_id=0,
    )

    assert store.count_points() == 1
    points = store.get_all_points()
    assert len(points) == 1
    assert points[0]["id"] == "pt_001"
    assert points[0]["payload"]["score"] == 98.5
    assert points[0]["entropy"] == 4.25
    assert points[0]["cluster_id"] == 0
    assert points[0]["vector"].shape == (128,)


def test_deduplicate_jsonl_file_e2e(tmp_path: Path):
    """Verifies end-to-end JSONL file ingestion, deduplication, and output generation."""
    input_file = tmp_path / "input_dataset.jsonl"
    output_file = tmp_path / "deduped_dataset.jsonl"
    qdrant_dir = tmp_path / "qdrant_data"

    topics = [
        ("Autonomous AI debate and consensus verification with full mathematical proofs.", "Execute Bradley-Terry tournament ranking on adapter weights."),
        ("Real-time 512Hz Movesense ECG Pan-Tompkins QRS detection and PTT blood pressure.", "Apply Butterworth bandpass filter and calculate moving window integration."),
        ("Dynamic RAM governor with Apple Silicon MPS cache eviction and Thunderbolt DMA offloading.", "Monitor host memory pressure and migrate tensor layers across 10Gbps bridge."),
    ]

    data = []
    for i in range(15):
        t_idx = i % 3
        instr, sol = topics[t_idx]
        data.append({
            "pair_id": f"rec_{i}",
            "instruction": f"{instr} (Sample variant {i // 3})",
            "solution": f"{sol} (Detailed resolution {i // 3})",
            "truth_verified": (i % 2 == 0),
        })

    with open(input_file, "w", encoding="utf-8") as f:
        for r in data:
            f.write(json.dumps(r) + "\n")

    dedup = PySparkSemanticDeduplicator(
        cosine_threshold=0.92,
        min_shannon_entropy=3.20,
        qdrant_path=qdrant_dir,
    )

    report = dedup.deduplicate_jsonl_file(input_file, output_file, sync_to_qdrant=True)

    assert report.total_samples == 15
    assert report.retained_samples == 3
    assert report.duplicates_removed == 12
    assert output_file.exists()

    # Read output file
    with open(output_file, "r", encoding="utf-8") as f:
        out_lines = [json.loads(l) for l in f if l.strip()]

    assert len(out_lines) == 3
    assert dedup.qdrant_store.count_points() == 3


def test_scale_1000_samples_performance():
    """Verifies high throughput on 1,000 samples (< 2 seconds execution time)."""
    dedup = PySparkSemanticDeduplicator(
        cosine_threshold=0.92,
        min_shannon_entropy=3.20,
        vector_dim=128,
    )

    # 10 distinct topics replicated 100 times each = 1,000 records
    topics = [
        "Distributed memory governor throttling and MPS cache eviction on Apple Silicon M4.",
        "Pulse Transit Time continuous non-invasive blood pressure inversion model calibration.",
        "Qwen AgentWorld 35B terminal tool call simulation and trajectory error prediction.",
        "Shopify Storefront GraphQL membership authentication and recurring billing gateway.",
        "SeaweedFS distributed file system replication and master topology health monitoring.",
        "Detrended Fluctuation Analysis DFA alpha 1 aerobic threshold boundary detection.",
        "Multi-stream JSONL harvesting pipeline with atomic file append and SHA256 hashing.",
        "Textual Rich TUI reactive telemetry dashboard 60 FPS terminal render loop.",
        "Rust Ratatui zero allocation immediate mode interface and crossterm event multiplexer.",
        "SWE-bench autonomous benchmark harness execution and automated patch validation.",
    ]

    records = []
    for i in range(1000):
        t_idx = i % 10
        records.append({
            "pair_id": f"perf_{i:04d}",
            "instruction": f"Task {topics[t_idx]} Variation {i // 10}",
            "solution": f"Detailed resolution for {topics[t_idx]} with comprehensive execution steps.",
            "truth_verified": (i % 2 == 0),
        })

    start = time.time()
    dedup_records, report = dedup.cluster_and_deduplicate(records)
    elapsed = time.time() - start

    assert report.total_samples == 1000
    assert report.retained_samples == 10
    assert report.duplicates_removed == 990
    assert len(dedup_records) == 10
    assert elapsed < 5.0, f"1000 samples took {elapsed:.2f}s, expected < 5.0s"


def test_boundary_corner_cases():
    """Verifies behavior on boundary inputs (empty lists, extreme strings)."""
    dedup = PySparkSemanticDeduplicator()

    # Empty list
    recs, rep = dedup.cluster_and_deduplicate([])
    assert recs == []
    assert rep.total_samples == 0
    assert rep.retained_samples == 0

    # Unicode & Special Characters
    unicode_records = [
        {
            "pair_id": "u_01",
            "instruction": "日本語のテキストと数学記号 ∫_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2} AI 訓練データ",
            "solution": "量子力学とニューラルネットワークの数学的証明と分散学習アーキテクチャ",
        },
        {
            "pair_id": "u_02",
            "instruction": "日本語のテキストと数学記号 ∫_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2} AI 訓練データ",
            "solution": "量子力学とニューラルネットワークの数学的証明と分散学習アーキテクチャ",
        },
    ]
    u_recs, u_rep = dedup.cluster_and_deduplicate(unicode_records)
    assert u_rep.total_samples == 2
    assert u_rep.duplicates_removed == 1
    assert len(u_recs) == 1
