"""
Unit and boundary tests for Pixel Local Persistence Engine and Port 4000 Forwarding Client.
"""

import json
import sqlite3
import tempfile
import time
from pathlib import Path
import pytest

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPUTE_HUB_SERVICES = REPO_ROOT / "01_apps" / "lauburu_compute_hub" / "services"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(COMPUTE_HUB_SERVICES) not in sys.path:
    sys.path.insert(0, str(COMPUTE_HUB_SERVICES))

from pixel_persistence_engine import PixelPersistenceEngine
from port4000_forwarder import Port4000Forwarder
from movesense_ingestion import (
    MovesenseStreamSimulator,
    MovesenseBinaryDecoder,
    PolarHrsDecoder,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    calculate_hemodynamics_bp
)


@pytest.fixture
def pixel_storage(tmp_path):
    return PixelPersistenceEngine(base_dir=tmp_path)


def test_pixel_storage_initialization(pixel_storage, tmp_path):
    assert pixel_storage.jsonl_path.parent.exists()
    assert pixel_storage.db_path.parent.exists()
    assert pixel_storage.db_path.exists()

    with pixel_storage._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        assert cur.fetchone()[0].upper() == "WAL"


def test_append_single_sample(pixel_storage):
    ts = int(time.time() * 1000)
    frame = {
        "timestamp_epoch_ms": ts,
        "sensor_type": "movesense",
        "sample_rate_hz": 128,
        "heart_rate": 142.5,
        "rr_intervals_ms": [820.0, 815.0],
        "rmssd": 35.2,
        "dfa_alpha1": 0.760,
        "ecg_mv": [0.1, 0.9, -0.2],
        "acc_g": {"x": 0.02, "y": 0.98, "z": 0.15}
    }
    frame_id = pixel_storage.append_frame(frame)
    assert frame_id > 0

    jsonl_recs = pixel_storage.read_jsonl_records()
    assert len(jsonl_recs) == 1
    assert jsonl_recs[0]["timestamp_epoch_ms"] == ts
    assert jsonl_recs[0]["heart_rate"] == 142.5

    sqlite_recs = pixel_storage.read_sqlite_records()
    assert len(sqlite_recs) == 1
    assert sqlite_recs[0]["timestamp_epoch_ms"] == ts
    assert sqlite_recs[0]["heart_rate"] == 142.5
    assert sqlite_recs[0]["synced_to_port4000"] == 0


def test_monotonic_timestamp_enforcement(pixel_storage):
    base_ts = int(time.time() * 1000)
    pixel_storage.append_frame({
        "timestamp_epoch_ms": base_ts,
        "sensor_type": "movesense",
        "sample_rate_hz": 128,
        "heart_rate": 140.0
    })

    # Equal timestamp should fail
    with pytest.raises(ValueError, match="Monotonic timestamp violation"):
        pixel_storage.append_frame({
            "timestamp_epoch_ms": base_ts,
            "sensor_type": "movesense",
            "sample_rate_hz": 128,
            "heart_rate": 141.0
        })

    # Decreasing timestamp should fail
    with pytest.raises(ValueError, match="Monotonic timestamp violation"):
        pixel_storage.append_frame({
            "timestamp_epoch_ms": base_ts - 100,
            "sensor_type": "movesense",
            "sample_rate_hz": 128,
            "heart_rate": 141.0
        })

    # Increasing timestamp should succeed
    new_id = pixel_storage.append_frame({
        "timestamp_epoch_ms": base_ts + 100,
        "sensor_type": "movesense",
        "sample_rate_hz": 128,
        "heart_rate": 142.0
    })
    assert new_id > 0


def test_15_second_continuous_stream_parity(pixel_storage):
    sim = MovesenseStreamSimulator(base_heart_rate=135.0)
    frames = sim.generate_15s_stream()
    assert len(frames) == 15

    for f in frames:
        pixel_storage.append_frame(f)

    integrity = pixel_storage.verify_integrity()
    assert integrity["valid"] is True
    assert integrity["counts_match"] is True
    assert integrity["jsonl_record_count"] == 15
    assert integrity["sqlite_record_count"] == 15
    assert integrity["jsonl_monotonic"] is True
    assert integrity["sqlite_monotonic"] is True
    assert integrity["field_parity"] is True


def test_sync_state_and_forwarder(pixel_storage):
    forwarder = Port4000Forwarder(
        host="127.0.0.1",
        port=4000,
        session_token="test_token_abc",
        persistence_engine=pixel_storage
    )

    base_ts = int(time.time() * 1000)
    for i in range(5):
        pixel_storage.append_frame({
            "timestamp_epoch_ms": base_ts + (i * 1000),
            "sensor_type": "movesense",
            "sample_rate_hz": 128,
            "heart_rate": 130.0 + i
        })

    unsynced = pixel_storage.get_unsynced_frames()
    assert len(unsynced) == 5

    marked = pixel_storage.mark_frames_synced([unsynced[0]["id"], unsynced[1]["id"]])
    assert marked == 2

    remaining = pixel_storage.get_unsynced_frames()
    assert len(remaining) == 3


def test_kamath_filter_and_rmssd():
    rr = [800.0, 810.0, 1200.0, 805.0]  # 1200 is an artifact (+48%)
    cleaned, count = apply_kamath_artifact_filter(rr)
    assert count == 1
    assert len(cleaned) == 4
    assert cleaned[2] < 1000.0  # Corrected

    rmssd = calculate_rmssd([800.0, 810.0, 805.0, 815.0])
    assert rmssd is not None
    assert rmssd > 0


def test_dfa_alpha1_and_bp():
    rr_steady = [800.0 + (i % 3) * 5.0 for i in range(30)]
    dfa = calculate_dfa_alpha1(rr_steady)
    assert dfa is not None
    assert 0.40 <= dfa <= 1.40

    sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=195.0, hr_bpm=140.0)
    assert sbp is not None and 100.0 <= sbp <= 160.0
    assert dbp is not None and 60.0 <= dbp <= 100.0
    assert map_val is not None
