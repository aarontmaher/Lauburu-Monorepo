"""
04_data_and_memory.pyspark_analytics package.
"""
from .pyspark_semantic_dedup import (
    PySparkSemanticDeduplicator,
    DedupReport,
    compute_shannon_entropy,
    compute_cosine_similarity,
    vectorize_text,
)

__all__ = [
    "PySparkSemanticDeduplicator",
    "DedupReport",
    "compute_shannon_entropy",
    "compute_cosine_similarity",
    "vectorize_text",
]
