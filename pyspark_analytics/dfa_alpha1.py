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

    intervals = np.array(rr_intervals, dtype=float)
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


def compute_dfa_alpha1(rr_intervals: List[float]) -> float:
    """Wrapper function for DFA alpha1 calculation."""
    return calculate_dfa_alpha1_series(rr_intervals)


def aggregate_dfa_metrics(spark_session: Any, data: List[Dict[str, Any]]) -> Any:
    """
    Aggregates DFA-alpha1 metrics across user sessions using PySpark DataFrame operations.
    Data format: [{"user_id": str, "session_id": str, "rr_intervals": List[float]}, ...]
    """
    if not PYSPARK_AVAILABLE:
        raise RuntimeError("PySpark is required for aggregate_dfa_metrics but not installed.")

    schema = StructType([
        StructField("user_id", StringType(), False),
        StructField("session_id", StringType(), False),
        StructField("rr_intervals", F.ArrayType(DoubleType()), False)
    ])

    df = spark_session.createDataFrame(data, schema=schema)

    # Register UDF
    @F.udf(returnType=DoubleType())
    def dfa_udf(arr):
        if not arr:
            return 0.75
        return calculate_dfa_alpha1_series(arr)

    df_result = df.withColumn("dfa_alpha1", dfa_udf(F.col("rr_intervals")))
    df_summary = df_result.groupBy("user_id").agg(
        F.avg("dfa_alpha1").alias("avg_dfa_alpha1"),
        F.count("session_id").alias("session_count")
    )

    return df_summary
