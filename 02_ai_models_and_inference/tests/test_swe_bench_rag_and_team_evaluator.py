#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for SWE-bench Full Dataset, RAG Strategies & Team Models
"""

import os
import sys
import json
import pytest
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[1] / "benchmarks"
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))

from swe_bench_rag_and_team_evaluator import (
    SweBenchRAGRetriever,
    TeamModelEvaluator,
    run_full_swe_bench_evaluation,
    REPORT_FILE
)


def test_oracle_retrieval():
    task = {
        "instance_id": "django__django-11099",
        "patch": "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n+++ b/django/contrib/auth/validators.py\n"
    }
    res = SweBenchRAGRetriever.retrieve_oracle(task)
    assert res["retrieval_strategy"] == "Oracle Retrieval"
    assert "django/contrib/auth/validators.py" in res["files_retrieved"]
    assert res["precision"] == 1.0


def test_bm25_retrieval_token_limits():
    task = {"problem_statement": "Unicode username validator newline bug", "repo": "django/django"}
    res13 = SweBenchRAGRetriever.retrieve_bm25(task, token_limit=13000)
    assert res13["context_tokens_est"] <= 13000
    
    res50 = SweBenchRAGRetriever.retrieve_bm25(task, token_limit=50000)
    assert res50["context_tokens_est"] <= 50000
    assert len(res50["files_retrieved"]) >= len(res13["files_retrieved"])


def test_ast_slicing_token_reduction():
    task = {
        "patch": "+++ b/django/contrib/auth/validators.py\n+++ b/django/contrib/auth/models.py\n"
    }
    res = SweBenchRAGRetriever.retrieve_ast_slicing(task)
    assert res["token_reduction_ratio"] >= 0.80
    assert res["context_tokens_est"] < 1500


def test_swe_llama_peft_adapters_downloaded():
    dir_7b = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/swe_llama_7b_peft")
    dir_13b = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/swe_llama_13b_peft")
    
    assert (dir_7b / "adapter_model.bin").exists()
    assert (dir_7b / "adapter_config.json").exists()
    assert (dir_13b / "adapter_model.bin").exists()
    assert (dir_13b / "adapter_config.json").exists()


def test_swe_bench_full_dataset_ingested():
    full_dataset = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/swe_bench_datasets/swe-bench_full.jsonl")
    assert full_dataset.exists()
    assert full_dataset.stat().st_size > 1024 * 1024  # > 1MB
    
    with open(full_dataset, "r", encoding="utf-8") as f:
        first_line = json.loads(f.readline())
    assert "instance_id" in first_line
    assert "repo" in first_line


def test_full_evaluation_pipeline_and_obsidian_sync():
    res = run_full_swe_bench_evaluation()
    assert res["status"] == "SUCCESS"
    assert res["evaluations_count"] >= 35
    assert REPORT_FILE.exists()
    assert REPORT_FILE.stat().st_size > 500


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
