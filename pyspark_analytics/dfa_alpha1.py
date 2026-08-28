"""
DFA-alpha1 (Detrended Fluctuation Analysis) time-series analytics using PySpark.
Used for HRV scaling exponent computation and time-series metrics aggregation.
"""

import math
from typing import List, Tuple, Dict, Any
import numpy as np

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import DoubleType, StructType, StructField, StringType
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False


def calculate_dfa_alpha1_series(rr_intervals: List[float], scale_min: int = 4, scale_max: int = 16) -> float:
    """
    Computes the DFA alpha-1 exponent for a given sequence of RR intervals (ms).
    Alpha1 range:
    - 0.75 - 1.0: Aerobic threshold / optimal recovery balance
    - > 1.0: Rest/recovery dominant
    - < 0.5: High fatigue / anaerobic stress
    """
    if not rr_intervals or len(rr_intervals) < scale_max * 2:
        return 0.75  # Default baseline if window too short

    try:
        clean_intervals = [float(x) for x in rr_intervals if x is not None and not math.isnan(x)]
        if len(clean_intervals) < scale_max * 2:
            return 0.75

        intervals = np.array(clean_intervals, dtype=float)
        mean_rr = np.mean(intervals)
        y = np.cumsum(intervals - mean_rr)

        scales = np.arange(scale_min, scale_max + 1)
        fluctuations = []

        for s in scales:
            num_segments = len(y) // s
            if num_segments == 0:
                continue

            rms_list = []
            for i in range(num_segments):
                segment = y[i * s : (i + 1) * s]
                x = np.arange(s)
                # Linear detrending
                poly = np.polyfit(x, segment, 1)
                trend = np.polyval(poly, x)
                rms = np.sqrt(np.mean((segment - trend) ** 2))
                rms_list.append(rms)

            if rms_list:
                fluctuations.append(np.mean(rms_list))
            else:
                fluctuations.append(1e-6)

        if len(fluctuations) < 2:
            return 0.75

        log_scales = np.log(scales[:len(fluctuations)])
        log_fluctuations = np.log(np.maximum(fluctuations, 1e-6))

        poly = np.polyfit(log_scales, log_fluctuations, 1)
        alpha1 = float(poly[0])
        return max(0.1, min(2.0, alpha1))
    except Exception:
        return 0.75


def compute_dfa_alpha1(rr_intervals: List[float], scale_min: int = 4, scale_max: int = 16) -> float:
    """Wrapper function for DFA alpha1 calculation."""
    return calculate_dfa_alpha1_series(rr_intervals, scale_min=scale_min, scale_max=scale_max)


def classify_dfa_alpha1_state(alpha1: float) -> str:
    """
    Classifies DFA alpha-1 exponent into physiological state categories.
    """
    if alpha1 >= 1.0:
        return "rest_recovery"
    elif alpha1 >= 0.75:
        return "aerobic_optimal"
    elif alpha1 >= 0.50:
        return "mild_fatigue"
    else:
        return "high_fatigue"


def compute_session_dfa_series(
    spark_session: Any,
    data: Any,
    scale_min: int = 4,
    scale_max: int = 16
) -> Any:
    """
    Computes per-session DFA-alpha1 metrics and state classification.
    `data` can be a list of dicts or a PySpark DataFrame.
    """
    if not PYSPARK_AVAILABLE:
        raise RuntimeError("PySpark is required for compute_session_dfa_series but not installed.")

    if isinstance(data, DataFrame):
        df = data
    else:
        schema = StructType([
            StructField("user_id", StringType(), False),
            StructField("session_id", StringType(), False),
            StructField("rr_intervals", F.ArrayType(DoubleType()), False)
        ])
        df = spark_session.createDataFrame(data, schema=schema)

    @F.udf(returnType=DoubleType())
    def dfa_udf(arr):
        if not arr:
            return 0.75
        return calculate_dfa_alpha1_series(arr, scale_min=scale_min, scale_max=scale_max)

    @F.udf(returnType=StringType())
    def state_udf(val):
        if val is None:
            return "aerobic_optimal"
        return classify_dfa_alpha1_state(float(val))

    df_result = df.withColumn("dfa_alpha1", dfa_udf(F.col("rr_intervals")))
    df_result = df_result.withColumn("dfa_state", state_udf(F.col("dfa_alpha1")))

    return df_result


def aggregate_dfa_metrics(
    spark_session: Any,
    data: Any,
    scale_min: int = 4,
    scale_max: int = 16
) -> Any:
    """
    Aggregates DFA-alpha1 metrics across user sessions using PySpark DataFrame operations.
    Supports input as a list of dicts or an existing PySpark DataFrame.
    Returns PySpark DataFrame with user-level DFA metrics summary.
    """
    df_sessions = compute_session_dfa_series(spark_session, data, scale_min=scale_min, scale_max=scale_max)

    df_summary = df_sessions.groupBy("user_id").agg(
        F.avg("dfa_alpha1").alias("avg_dfa_alpha1"),
        F.min("dfa_alpha1").alias("min_dfa_alpha1"),
        F.max("dfa_alpha1").alias("max_dfa_alpha1"),
        F.coalesce(F.stddev("dfa_alpha1"), F.lit(0.0)).alias("stddev_dfa_alpha1"),
        F.count("session_id").alias("session_count"),
        F.sum(F.when((F.col("dfa_alpha1") >= 0.75) & (F.col("dfa_alpha1") < 1.0), 1).otherwise(0)).alias("aerobic_optimal_count"),
        F.sum(F.when(F.col("dfa_alpha1") >= 1.0, 1).otherwise(0)).alias("recovery_dominant_count"),
        F.sum(F.when(F.col("dfa_alpha1") < 0.50, 1).otherwise(0)).alias("high_fatigue_count")
    )

    return df_summary
