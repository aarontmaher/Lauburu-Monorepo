#!/usr/bin/env python3
"""
Movesense Showcase & Grappling Data Ingestion Pipeline
Converts physical sensor CSV recordings and SQLite databases into canonical Parquet datasets
for kinematic analysis, cardiovascular modeling, and local AI training.
Follows Rule 1: Zero-Mock Empirical Truth.
"""

import os
import io
import glob
import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timezone

DATA_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/movesense_showcase_sessions"
DB_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/grappling_history.db"
PARQUET_OUT_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/movesense_parquet"

os.makedirs(PARQUET_OUT_DIR, exist_ok=True)

def parse_clean_csv(file_path: str) -> pd.DataFrame:
    """Reads CSV while stripping trailing commas/spaces from every line."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        clean_lines = [line.strip().rstrip(",") for line in f if line.strip()]
    if not clean_lines:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO("\n".join(clean_lines)))

def ingest_showcase_csvs():
    """Parses all Movesense Showcase CSV files."""
    print(">>> [1/4] Ingesting Movesense Showcase CSVs...")
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    lin_acc_frames = []
    ang_vel_frames = []
    mag_field_frames = []
    hr_frames = []
    temp_frames = []
    
    for f in sorted(csv_files):
        if os.path.getsize(f) == 0:
            continue
        fname = os.path.basename(f)
        try:
            df = parse_clean_csv(f)
            if df.empty:
                continue
            df["source_file"] = fname
            df.columns = [c.strip() for c in df.columns]
            
            if "LinearAcceleration" in fname:
                df = df.rename(columns={
                    "Timestamp (ms)": "timestamp_ms",
                    "X: (m/s^2)": "acc_x",
                    "Y: (m/s^2)": "acc_y",
                    "Z: (m/s^2)": "acc_z"
                })
                # Ensure float
                for col in ["acc_x", "acc_y", "acc_z"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["acc_mag"] = np.sqrt(df["acc_x"]**2 + df["acc_y"]**2 + df["acc_z"]**2)
                lin_acc_frames.append(df)
            elif "AngularVelocity" in fname:
                df = df.rename(columns={
                    "Timestamp (ms)": "timestamp_ms",
                    "X: (degree per second)": "gyro_x",
                    "Y: (degree per second)": "gyro_y",
                    "Z: (degree per second)": "gyro_z"
                })
                for col in ["gyro_x", "gyro_y", "gyro_z"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["gyro_mag"] = np.sqrt(df["gyro_x"]**2 + df["gyro_y"]**2 + df["gyro_z"]**2)
                ang_vel_frames.append(df)
            elif "MagneticField" in fname:
                df = df.rename(columns={
                    "Timestamp (ms)": "timestamp_ms",
                    "X: (microtesla)": "mag_x",
                    "Y: (microtesla)": "mag_y",
                    "Z: (microtesla)": "mag_z"
                })
                for col in ["mag_x", "mag_y", "mag_z"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["mag_total"] = np.sqrt(df["mag_x"]**2 + df["mag_y"]**2 + df["mag_z"]**2)
                mag_field_frames.append(df)
            elif "HeartRate" in fname:
                df = df.rename(columns={
                    "Timestamp": "timestamp_ms",
                    "HR: (Beats per minute)": "heart_rate_bpm",
                    "RR: (ms)": "rr_interval_ms"
                })
                hr_frames.append(df)
            elif "Temperature" in fname:
                df = df.rename(columns={
                    "Timestamp (ms)": "timestamp_ms",
                    "Temp (Kelvin)": "temp_kelvin"
                })
                df["temp_celsius"] = df["temp_kelvin"] - 273.15
                temp_frames.append(df)
        except Exception as e:
            print(f"  Error reading {fname}: {e}")
            
    results = {}
    if lin_acc_frames:
        lin_acc_df = pd.concat(lin_acc_frames, ignore_index=True)
        path = os.path.join(PARQUET_OUT_DIR, "showcase_linear_acceleration.parquet")
        lin_acc_df.to_parquet(path, index=False)
        results["linear_acceleration"] = {"rows": len(lin_acc_df), "file": path}
        print(f"  ✓ Saved {len(lin_acc_df):,} linear acceleration samples to {path}")
        
    if ang_vel_frames:
        ang_vel_df = pd.concat(ang_vel_frames, ignore_index=True)
        path = os.path.join(PARQUET_OUT_DIR, "showcase_angular_velocity.parquet")
        ang_vel_df.to_parquet(path, index=False)
        results["angular_velocity"] = {"rows": len(ang_vel_df), "file": path}
        print(f"  ✓ Saved {len(ang_vel_df):,} angular velocity samples to {path}")

    if mag_field_frames:
        mag_field_df = pd.concat(mag_field_frames, ignore_index=True)
        path = os.path.join(PARQUET_OUT_DIR, "showcase_magnetic_field.parquet")
        mag_field_df.to_parquet(path, index=False)
        results["magnetic_field"] = {"rows": len(mag_field_df), "file": path}
        print(f"  ✓ Saved {len(mag_field_df):,} magnetic field samples to {path}")

    if hr_frames:
        hr_df = pd.concat(hr_frames, ignore_index=True)
        path = os.path.join(PARQUET_OUT_DIR, "showcase_heart_rate.parquet")
        hr_df.to_parquet(path, index=False)
        results["heart_rate"] = {"rows": len(hr_df), "file": path}
        print(f"  ✓ Saved {len(hr_df):,} heart rate samples to {path}")

    if temp_frames:
        temp_df = pd.concat(temp_frames, ignore_index=True)
        path = os.path.join(PARQUET_OUT_DIR, "showcase_temperature.parquet")
        temp_df.to_parquet(path, index=False)
        results["temperature"] = {"rows": len(temp_df), "file": path}
        print(f"  ✓ Saved {len(temp_df):,} temperature samples to {path}")

    return results

def ingest_grappling_db():
    """Ingests SQLite grappling_history.db tables into Parquet."""
    print(">>> [2/4] Ingesting SQLite grappling_history.db...")
    if not os.path.exists(DB_PATH):
        print(f"  ! DB {DB_PATH} not found.")
        return {}
        
    conn = sqlite3.connect(DB_PATH)
    results = {}
    
    # 1. IMU Motion Telemetry
    print("  Reading imu_motion_telemetry...")
    imu_df = pd.read_sql_query("SELECT * FROM imu_motion_telemetry", conn)
    if not imu_df.empty:
        imu_df["acc_mag"] = np.sqrt(imu_df["acc_x"]**2 + imu_df["acc_y"]**2 + imu_df["acc_z"]**2)
        imu_df["gyro_mag"] = np.sqrt(imu_df["gyro_x"]**2 + imu_df["gyro_y"]**2 + imu_df["gyro_z"]**2)
        path = os.path.join(PARQUET_OUT_DIR, "grappling_imu_telemetry.parquet")
        imu_df.to_parquet(path, index=False)
        results["grappling_imu"] = {"rows": len(imu_df), "file": path}
        print(f"  ✓ Saved {len(imu_df):,} IMU records to {path}")

    # 2. RR Interval History
    print("  Reading rr_interval_history...")
    rr_df = pd.read_sql_query("SELECT * FROM rr_interval_history", conn)
    if not rr_df.empty:
        # Apply Kamath (2004) 20% clinical RR artifact filter
        rr_vals = rr_df["rr_ms"].values
        valid_mask = [True]
        for i in range(1, len(rr_vals)):
            prev = rr_vals[i-1]
            curr = rr_vals[i]
            if prev > 0 and abs(curr - prev) / prev <= 0.20:
                valid_mask.append(True)
            else:
                valid_mask.append(False)
        rr_df["kamath_valid"] = valid_mask
        path = os.path.join(PARQUET_OUT_DIR, "grappling_rr_intervals.parquet")
        rr_df.to_parquet(path, index=False)
        results["grappling_rr"] = {"rows": len(rr_df), "valid_kamath": int(sum(valid_mask)), "file": path}
        print(f"  ✓ Saved {len(rr_df):,} RR intervals ({sum(valid_mask):,} Kamath valid) to {path}")

    # 3. Bicep ECG Calibration
    print("  Reading bicep_ecg_calibration...")
    ecg_cal_df = pd.read_sql_query("SELECT * FROM bicep_ecg_calibration", conn)
    if not ecg_cal_df.empty:
        path = os.path.join(PARQUET_OUT_DIR, "grappling_ecg_calibration.parquet")
        ecg_cal_df.to_parquet(path, index=False)
        results["ecg_calibration"] = {"rows": len(ecg_cal_df), "file": path}
        print(f"  ✓ Saved {len(ecg_cal_df):,} ECG calibration records to {path}")

    conn.close()
    return results

def create_unified_training_dataset():
    """Builds a synchronized kinematic & cardiac training feature matrix."""
    print(">>> [3/4] Synthesizing unified training feature matrix...")
    imu_path = os.path.join(PARQUET_OUT_DIR, "grappling_imu_telemetry.parquet")
    rr_path = os.path.join(PARQUET_OUT_DIR, "grappling_rr_intervals.parquet")
    
    if not os.path.exists(imu_path):
        print("  ! Missing IMU parquet file.")
        return None, 0
        
    imu_df = pd.read_parquet(imu_path)
    
    # Feature engineering for kinematic intensity & physical work:
    imu_df["jerk"] = imu_df["acc_mag"].diff().fillna(0.0).abs()
    imu_df["mechanical_work_proxy"] = imu_df["acc_mag"] * imu_df["gyro_mag"]
    imu_df["is_high_intensity"] = ((imu_df["acc_mag"] > 15.0) | (imu_df["gyro_mag"] > 100.0)).astype(int)
    
    # Bucket into 1-second epochs (robust conversion avoiding Pandas 2.0 microsecond divisor collapse)
    imu_df["epoch_sec"] = pd.to_datetime(imu_df["timestamp"]).values.astype("datetime64[s]").astype("int64")
    
    features = imu_df.groupby("epoch_sec").agg({
        "acc_mag": ["mean", "max", "std"],
        "gyro_mag": ["mean", "max", "std"],
        "jerk": ["mean", "max"],
        "mechanical_work_proxy": ["mean", "sum"],
        "is_high_intensity": ["mean"]
    })
    features.columns = ["_".join(c).strip() for c in features.columns.values]
    features = features.reset_index()
    
    # If RR intervals exist, correlate HR with physical intensity
    if os.path.exists(rr_path):
        rr_df = pd.read_parquet(rr_path)
        rr_df["epoch_sec"] = pd.to_datetime(rr_df["timestamp"]).values.astype("datetime64[s]").astype("int64")
        cardiac_agg = rr_df.groupby("epoch_sec").agg({
            "bpm": ["mean", "max", "min"],
            "rr_ms": ["mean", "std"]
        })
        cardiac_agg.columns = ["cardiac_" + "_".join(c).strip() for c in cardiac_agg.columns.values]
        cardiac_agg = cardiac_agg.reset_index()
        
        dataset = pd.merge(features, cardiac_agg, on="epoch_sec", how="left")
    else:
        dataset = features

    out_path = os.path.join(PARQUET_OUT_DIR, "movesense_training_dataset.parquet")
    dataset.to_parquet(out_path, index=False)
    print(f"  ✓ Unified training dataset created with {len(dataset):,} epoch records at {out_path}")
    return out_path, len(dataset)

def main():
    print("=================================================================")
    print("Movesense Pipeline: Zero-Mock Physical Data Ingestion to Parquet")
    print("=================================================================")
    showcase_results = ingest_showcase_csvs()
    db_results = ingest_grappling_db()
    out_path, n_epochs = create_unified_training_dataset()
    
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "showcase_csv_records": showcase_results,
        "grappling_db_records": db_results,
        "unified_dataset": {
            "path": out_path,
            "epoch_records": n_epochs
        }
    }
    summary_path = os.path.join(PARQUET_OUT_DIR, "ingestion_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n>>> [4/4] Ingestion complete. Summary written to {summary_path}")

if __name__ == "__main__":
    main()
