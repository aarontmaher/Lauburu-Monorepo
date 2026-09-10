---
title: "Movesense 24/7 Continuous Biometrics Data Lake Vault"
tags: [movesense, biometrics, 247, tri_vault, ecg, hrv, dsp, zero_mock]
updated_utc: "2026-09-10 03:11:28 UTC"
---

# 💓 Movesense 24/7 Continuous Biometrics Data Lake Vault

> **Rule #0 Enforced:** 100% authentic sensor telemetry from physical Movesense HR+ (261030002013). Zero mocked metrics.  
> **Rule #2 Tri-Vault Storage:** Synchronized between SQLite WAL (`movesense_247.db`), PySpark JSONL Data Lake (`04_data_and_memory/biometrics_lake/`), and Obsidian Knowledge Core.  
> **Rule #3 Host Sanctuary:** Lightweight background daemon preserving $\ge 9.6\text{ GB}$ host RAM buffer.  
> **Master Wikilinks:** [[Index]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]]

---

## 📊 1. 24/7 Storage Lake Overview

| Metric | Measured Value | Storage Tier & Engine |
| :--- | :--- | :--- |
| **Total Recorded Samples** | `4,622` frames | SQLite WAL (`movesense_247.db`) |
| **Valid Biometric Samples** | `4,622` frames | PySpark Daily JSONL Lake |
| **Total Recorded Workouts** | `46` sessions | Relational Table `workout_sessions` |
| **Local Database Size** | `1592.0 KB` | `04_data_and_memory/biometrics_lake/` |
| **PySpark Lake Partition** | `jsonl/2026-09-10.jsonl` | Append-only partitioned stream |
| **LoRA Distillation Mirror** | `lora_datasets/biometrics/` | Continuous learning instruction feed |

---

## 🗓️ 2. Today's Physiological Profile (2026-09-10)

| Physiological Parameter | Value | Interpretation |
| :--- | :--- | :--- |
| **Total Wear Time Today** | **`77.0 min`** | Sensor contact & streaming duration |
| **Resting Heart Rate (Min)** | **`72.0 BPM`** | Nocturnal / Parasympathetic baseline |
| **Mean Active Heart Rate** | **`104.0 BPM`** | Daily metabolic cardiovascular demand |
| **Peak Heart Rate (Max)** | **`104.0 BPM`** | Maximum cardiovascular excursion |
| **Mean HRV (RMSSD)** | **`16.5 ms`** | Autonomic nervous system recovery tone |
| **Mean Readiness Score** | **`76.0 / 100`** | Systemic readiness & recovery status |

---

## 🏋️ 3. Recent Recorded Workout Sessions

| Session ID | Start Time | Duration | Avg HR | Max HR | Avg RMSSD | Zone 2 Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `workout_1789009535` | `2026-09-10T03:05` | `0.5 min` | `104.0 bpm` | `104.0 bpm` | `16.5 ms` | `0.0 min` |
| `workout_1789009301` | `2026-09-10T03:01` | `1.8 min` | `104.0 bpm` | `104.0 bpm` | `16.5 ms` | `0.0 min` |
| `workout_1789009162` | `2026-09-10T02:59` | `1.2 min` | `104.0 bpm` | `104.0 bpm` | `16.5 ms` | `0.0 min` |
| `workout_1789008828` | `2026-09-10T02:53` | `2.7 min` | `104.0 bpm` | `104.0 bpm` | `16.5 ms` | `0.0 min` |
| `workout_1789008570` | `2026-09-10T02:49` | `2.4 min` | `104.0 bpm` | `104.0 bpm` | `16.5 ms` | `0.0 min` |

---

## 📡 4. Latest Telemetry Samples (Rule #0 Verified)

| Timestamp (UTC) | HR | Clean RR | RMSSD | DFA-α1 | Zone | Ingestion Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `03:11:28` | `104.0 bpm` | `582.7 ms` | `16.52 ms` | `0.67` | `ZONE 3/4` | `pixel_10_pro_xl_ble` |
| `03:11:26` | `104.0 bpm` | `582.7 ms` | `16.52 ms` | `0.67` | `ZONE 3/4` | `pixel_10_pro_xl_ble` |
| `03:11:23` | `104.0 bpm` | `582.7 ms` | `16.52 ms` | `0.67` | `ZONE 3/4` | `pixel_10_pro_xl_ble` |
| `03:11:21` | `104.0 bpm` | `582.7 ms` | `16.52 ms` | `0.67` | `ZONE 3/4` | `pixel_10_pro_xl_ble` |
| `03:11:20` | `104.0 bpm` | `582.7 ms` | `16.52 ms` | `0.67` | `ZONE 3/4` | `pixel_10_pro_xl_ble` |
