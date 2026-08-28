"""
Tests for DFA-alpha1 computation and PySpark aggregation.
"""

import pytest
import numpy as np
from pyspark_analytics.dfa_alpha1 import (
    compute_dfa_alpha1,
    calculate_dfa_alpha1_series,
    classify_dfa_alpha1_state,
    compute_session_dfa_series,
    aggregate_dfa_metrics,
)

try:
    from pyspark.sql import SparkSession
    from pyspark.sql.types import DoubleType, StructType, StructField, StringType
    from pyspark.sql import functions as F
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
    # Regular signal series
    rr_intervals = [800.0 + 10.0 * np.sin(i / 5.0) for i in range(100)]
    alpha1 = compute_dfa_alpha1(rr_intervals)
    assert 0.1 <= alpha1 <= 2.0
    assert isinstance(alpha1, float)


def test_compute_dfa_alpha1_short_series():
    # Short series fallback
    rr_intervals = [800.0, 810.0, 790.0]
    alpha1 = compute_dfa_alpha1(rr_intervals)
    assert alpha1 == 0.75


def test_classify_dfa_alpha1_state():
    assert classify_dfa_alpha1_state(1.1) == "rest_recovery"
    assert classify_dfa_alpha1_state(0.85) == "aerobic_optimal"
    assert classify_dfa_alpha1_state(0.60) == "mild_fatigue"
    assert classify_dfa_alpha1_state(0.40) == "high_fatigue"


def test_calculate_dfa_alpha1_series_edge_cases():
    assert calculate_dfa_alpha1_series([]) == 0.75
    assert calculate_dfa_alpha1_series([None, 800.0, float('nan')]) == 0.75
    # Custom scales
    rr_intervals = [800.0 + float(i % 5) for i in range(60)]
    alpha1_custom = calculate_dfa_alpha1_series(rr_intervals, scale_min=4, scale_max=10)
    assert 0.1 <= alpha1_custom <= 2.0


def test_compute_session_dfa_series_pyspark(spark_session):
    data = [
        {
            "user_id": "user_1",
            "session_id": "sess_101",
            "rr_intervals": [800.0 + float(i % 10) for i in range(50)],
        },
    ]
    df_result = compute_session_dfa_series(spark_session, data)
    rows = df_result.collect()
    assert len(rows) == 1
    assert "dfa_alpha1" in rows[0]
    assert "dfa_state" in rows[0]
    assert 0.1 <= rows[0]["dfa_alpha1"] <= 2.0
    assert rows[0]["dfa_state"] in ["rest_recovery", "aerobic_optimal", "mild_fatigue", "high_fatigue"]


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
    assert 0.1 <= users["user_1"]["min_dfa_alpha1"] <= 2.0
    assert 0.1 <= users["user_1"]["max_dfa_alpha1"] <= 2.0
    assert users["user_1"]["stddev_dfa_alpha1"] >= 0.0
    assert "aerobic_optimal_count" in users["user_1"]
    assert "recovery_dominant_count" in users["user_1"]
    assert "high_fatigue_count" in users["user_1"]


def test_aggregate_dfa_metrics_pyspark_dataframe_input(spark_session):
    schema = StructType([
        StructField("user_id", StringType(), False),
        StructField("session_id", StringType(), False),
        StructField("rr_intervals", F.ArrayType(DoubleType()), False)
    ])
    data = [
        ("user_df", "sess_01", [800.0 + float(i) for i in range(40)]),
        ("user_df", "sess_02", [780.0 + float(i) for i in range(40)]),
    ]
    df_in = spark_session.createDataFrame(data, schema=schema)
    summary_df = aggregate_dfa_metrics(spark_session, df_in)
    rows = summary_df.collect()

    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == "user_df"
    assert row["session_count"] == 2
    assert 0.1 <= row["avg_dfa_alpha1"] <= 2.0
