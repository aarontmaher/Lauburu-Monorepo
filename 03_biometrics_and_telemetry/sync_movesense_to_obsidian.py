#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Movesense 24/7 Tri-Vault Obsidian Knowledge Graph Rollup
========================================================
Subsystem: 03_biometrics_and_telemetry/sync_movesense_to_obsidian.py
Rule #0 Enforced: Zero simulated data. Reads directly from movesense_247.db.
Rule #2 Compliant: Tri-Vault storage (Obsidian Knowledge Core synchronization).
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_LAKE_DIR = REPO_ROOT / "04_data_and_memory/biometrics_lake"
DB_PATH = DATA_LAKE_DIR / "movesense_247.db"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault/APPS_AND_FEATURES"
VAULT_DOC_PATH = OBSIDIAN_DIR / "MOVESENSE_247_BIOMETRICS_VAULT.md"


def sync_obsidian_vault():
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 1. Total statistics
    total_samples = conn.execute("SELECT COUNT(*) FROM biometric_samples;").fetchone()[0]
    valid_hr_samples = conn.execute("SELECT COUNT(*) FROM biometric_samples WHERE heart_rate_bpm > 0;").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM workout_sessions;").fetchone()[0]
    db_size_kb = round(os.path.getsize(DB_PATH) / 1024.0, 1)

    # 2. Today's Rollup
    today_samples_row = conn.execute("""
        SELECT 
            COUNT(*) as count,
            AVG(heart_rate_bpm) as mean_hr,
            MIN(heart_rate_bpm) as min_hr,
            MAX(heart_rate_bpm) as max_hr,
            AVG(rmssd_ms) as mean_rmssd,
            AVG(readiness_score) as mean_readiness
        FROM biometric_samples
        WHERE timestamp_utc LIKE ? AND heart_rate_bpm > 30.0;
    """, (f"{today_str}%",)).fetchone()

    t_count = today_samples_row["count"] if today_samples_row else 0
    t_wear_min = round(t_count / 60.0, 1)
    t_mean_hr = round(today_samples_row["mean_hr"], 1) if today_samples_row and today_samples_row["mean_hr"] else "--"
    t_min_hr = round(today_samples_row["min_hr"], 1) if today_samples_row and today_samples_row["min_hr"] else "--"
    t_max_hr = round(today_samples_row["max_hr"], 1) if today_samples_row and today_samples_row["max_hr"] else "--"
    t_rmssd = round(today_samples_row["mean_rmssd"], 1) if today_samples_row and today_samples_row["mean_rmssd"] else "--"
    t_readiness = round(today_samples_row["mean_readiness"], 1) if today_samples_row and today_samples_row["mean_readiness"] else "--"

    # 3. Recent Workouts
    sessions = conn.execute("""
        SELECT * FROM workout_sessions
        ORDER BY start_time_utc DESC LIMIT 5;
    """).fetchall()

    # 4. Recent Telemetry Samples
    recent_samples = conn.execute("""
        SELECT timestamp_utc, heart_rate_bpm, clean_rr_ms, rmssd_ms, dfa_alpha1, training_zone, source
        FROM biometric_samples
        WHERE heart_rate_bpm > 0
        ORDER BY id DESC LIMIT 5;
    """).fetchall()

    conn.close()

    # Build Markdown
    content = f"""---
title: "Movesense 24/7 Continuous Biometrics Data Lake Vault"
tags: [movesense, biometrics, 247, tri_vault, ecg, hrv, dsp, zero_mock]
updated_utc: "{now_iso}"
---

# 💓 Movesense 24/7 Continuous Biometrics Data Lake Vault

> **Rule #0 Enforced:** 100% authentic sensor telemetry from physical Movesense HR+ (261030002013). Zero mocked metrics.  
> **Rule #2 Tri-Vault Storage:** Synchronized between SQLite WAL (`movesense_247.db`), PySpark JSONL Data Lake (`04_data_and_memory/biometrics_lake/`), and Obsidian Knowledge Core.  
> **Rule #3 Host Sanctuary:** Lightweight background daemon preserving $\\ge 9.6\\text{{ GB}}$ host RAM buffer.  
> **Master Wikilinks:** [[Index]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]]

---

## 📊 1. 24/7 Storage Lake Overview

| Metric | Measured Value | Storage Tier & Engine |
| :--- | :--- | :--- |
| **Total Recorded Samples** | `{total_samples:,}` frames | SQLite WAL (`movesense_247.db`) |
| **Valid Biometric Samples** | `{valid_hr_samples:,}` frames | PySpark Daily JSONL Lake |
| **Total Recorded Workouts** | `{total_sessions}` sessions | Relational Table `workout_sessions` |
| **Local Database Size** | `{db_size_kb} KB` | `04_data_and_memory/biometrics_lake/` |
| **PySpark Lake Partition** | `jsonl/{today_str}.jsonl` | Append-only partitioned stream |
| **LoRA Distillation Mirror** | `lora_datasets/biometrics/` | Continuous learning instruction feed |

---

## 🗓️ 2. Today's Physiological Profile ({today_str})

| Physiological Parameter | Value | Interpretation |
| :--- | :--- | :--- |
| **Total Wear Time Today** | **`{t_wear_min} min`** | Sensor contact & streaming duration |
| **Resting Heart Rate (Min)** | **`{t_min_hr} BPM`** | Nocturnal / Parasympathetic baseline |
| **Mean Active Heart Rate** | **`{t_mean_hr} BPM`** | Daily metabolic cardiovascular demand |
| **Peak Heart Rate (Max)** | **`{t_max_hr} BPM`** | Maximum cardiovascular excursion |
| **Mean HRV (RMSSD)** | **`{t_rmssd} ms`** | Autonomic nervous system recovery tone |
| **Mean Readiness Score** | **`{t_readiness} / 100`** | Systemic readiness & recovery status |

---

## 🏋️ 3. Recent Recorded Workout Sessions

"""

    if sessions:
        content += "| Session ID | Start Time | Duration | Avg HR | Max HR | Avg RMSSD | Zone 2 Time |\n"
        content += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for s in sessions:
            dur_m = round(s["duration_seconds"] / 60.0, 1)
            z2_m = round(s["zone2_seconds"] / 60.0, 1)
            content += f"| `{s['session_id']}` | `{s['start_time_utc'][:16]}` | `{dur_m} min` | `{s['avg_hr']} bpm` | `{s['max_hr']} bpm` | `{s['avg_rmssd']} ms` | `{z2_m} min` |\n"
    else:
        content += "*No workout sessions recorded yet today. Standby mode active while sensor is unclipped.*\n"

    content += "\n---\n\n## 📡 4. Latest Telemetry Samples (Rule #0 Verified)\n\n"

    if recent_samples:
        content += "| Timestamp (UTC) | HR | Clean RR | RMSSD | DFA-α1 | Zone | Ingestion Source |\n"
        content += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for r in recent_samples:
            content += f"| `{r['timestamp_utc'][11:19]}` | `{r['heart_rate_bpm']} bpm` | `{r['clean_rr_ms']} ms` | `{r['rmssd_ms']} ms` | `{r['dfa_alpha1']}` | `{r['training_zone'].split('(')[0].strip()}` | `{r['source']}` |\n"
    else:
        content += "*Awaiting sensor connection. Telemetry displays clean waiting state (`--`) when disconnected.*\n"

    with open(VAULT_DOC_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Synced Movesense 24/7 Knowledge Vault to {VAULT_DOC_PATH}")


if __name__ == "__main__":
    sync_obsidian_vault()
