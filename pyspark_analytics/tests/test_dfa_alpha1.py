"""
Tests for DFA-alpha1 computation and PySpark aggregation.
"""

import pytest
import numpy as np
from pyspark_analytics.dfa_alpha1 import compute_dfa_alpha1, aggregate_dfa_metrics

try:
    from pyspark.sql import SparkSession
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False


@pytest.fixture(scope="module")
def spark_session():
    if not PYSPARK_AVAILABLE:
        pytest.skip("PySpark is not available in this environment")
    spark = SparkSession.builder \
        .appName("DFAAlpha1Test") \
        .master("local[1]") \
        .config("spark.ui.enabled", "false") \
        .getOrCreate()
    yield spark
    spark.stop()


def test_compute_dfa_alpha1_baseline():
    # White noise or regular series
    rr_intervals = [800.0 + 10.0 * np.sin(i / 5.0) for i in range(100)]
    alpha1 = compute_dfa_alpha1(rr_intervals)
    assert 0.1 <= alpha1 <= 2.0
    assert isinstance(alpha1, float)


def test_compute_dfa_alpha1_short_series():
    # Short series fallback
    rr_intervals = [800.0, 810.0, 790.0]
    alpha1 = compute_dfa_alpha1(rr_intervals)
    assert alpha1 == 0.75


def test_aggregate_dfa_metrics_pyspark(spark_session):
    data = [
        {
            "user_id": "user_1",
            "session_id": "sess_101",
            "rr_intervals": [800.0 + float(i % 10) for i in range(50)],
        },
        {
            "user_id": "user_1",
            "session_id": "sess_102",
            "rr_intervals": [750.0 + float(i % 5) for i in range(50)],
        },
        {
            "user_id": "user_2",
            "session_id": "sess_201",
            "rr_intervals": [820.0 + float(i % 8) for i in range(50)],
        },
    ]

    summary_df = aggregate_dfa_metrics(spark_session, data)
    rows = summary_df.collect()

    assert len(rows) == 2
    users = {r["user_id"]: r for r in rows}
    assert "user_1" in users
    assert users["user_1"]["session_count"] == 2
    assert 0.1 <= users["user_1"]["avg_dfa_alpha1"] <= 2.0
