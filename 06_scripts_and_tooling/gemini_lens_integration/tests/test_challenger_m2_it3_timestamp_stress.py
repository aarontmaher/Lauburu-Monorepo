"""Milestone 2 Iteration 3 Adversarial Timestamp Stress Test Suite.

Authored by challenger_m2_it3_1.
Empirically stress-tests and audits the timestamp normalization remediation in lens_client.py:
1. Microseconds and nanoseconds timestamp normalization (int, float, str, scientific notation).
2. Milliseconds and seconds normalization (int, float, str).
3. Preservation of historical integrity (valid timestamps must NEVER default to datetime.now()).
4. Extreme integer values (10^25, 10^50, 10^100, 10^400).
5. Negative timestamps (valid pre-1970 seconds, extreme negative values).
6. Non-finite floating point numbers (inf, -inf, nan) and string equivalents ("inf", "+inf", "-inf", "nan").
7. Malformed, empty, and non-primitive inputs (None, whitespace, dict, list, bytes).
8. End-to-end integration with ScreenLensClient harvesting SQLite tables with microsecond and nanosecond timestamps.
"""

from __future__ import annotations

import datetime
import math
import sqlite3
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lens_client import ScreenLensClient, normalize_iso_timestamp


class TestNanosecondAndMicrosecondNormalization:
    """Rigorous verification of sub-millisecond epoch timestamps."""

    # Reference point: 2026-10-11T11:14:20.484000Z
    REF_SEC = 1791717260
    REF_MS = 1791717260484
    REF_US = 1791717260484000
    REF_NS = 1791717260484000000
    EXPECTED_PREFIX = "2026-10-11T11:14:20"

    def test_nanoseconds_all_types(self):
        """Nanoseconds as int, float, str, and scientific notation."""
        for val in [
            self.REF_NS,
            float(self.REF_NS),
            str(self.REF_NS),
            f" {self.REF_NS} ",
            "1.791717260484e18",
            1.791717260484e18,
        ]:
            result = normalize_iso_timestamp(val)
            assert result.startswith(self.EXPECTED_PREFIX), (
                f"Failed for nanosecond input {val!r}: got {result}"
            )
            # Ensure it is a valid ISO string
            dt = datetime.datetime.fromisoformat(result)
            assert dt.year == 2026
            assert dt.month == 10
            assert dt.day == 11

    def test_microseconds_all_types(self):
        """Microseconds as int, float, str, and scientific notation."""
        for val in [
            self.REF_US,
            float(self.REF_US),
            str(self.REF_US),
            f"\t{self.REF_US}\n",
            "1.791717260484e15",
            1.791717260484e15,
        ]:
            result = normalize_iso_timestamp(val)
            assert result.startswith(self.EXPECTED_PREFIX), (
                f"Failed for microsecond input {val!r}: got {result}"
            )
            dt = datetime.datetime.fromisoformat(result)
            assert dt.year == 2026
            assert dt.month == 10
            assert dt.day == 11

    def test_milliseconds_all_types(self):
        """Milliseconds as int, float, str, and scientific notation."""
        for val in [
            self.REF_MS,
            float(self.REF_MS),
            str(self.REF_MS),
            f"{self.REF_MS}.0",
            "1.791717260484e12",
            1.791717260484e12,
        ]:
            result = normalize_iso_timestamp(val)
            assert result.startswith(self.EXPECTED_PREFIX), (
                f"Failed for millisecond input {val!r}: got {result}"
            )
            dt = datetime.datetime.fromisoformat(result)
            assert dt.year == 2026

    def test_seconds_all_types(self):
        """Seconds as int, float, and str."""
        for val in [
            self.REF_SEC,
            float(self.REF_SEC),
            str(self.REF_SEC),
            f"{self.REF_SEC}.484",
        ]:
            result = normalize_iso_timestamp(val)
            assert result.startswith(self.EXPECTED_PREFIX), (
                f"Failed for second input {val!r}: got {result}"
            )
            dt = datetime.datetime.fromisoformat(result)
            assert dt.year == 2026


class TestAdversarialExtremeNumericInputs:
    """Stress tests on extreme integers, floats, negative values, and infinities."""

    def test_extreme_large_integers(self):
        """Extreme large numbers must not enter infinite loops or crash."""
        extreme_values = [
            10**18,   # ~quintillion (attoseconds)
            10**21,   # zeptoseconds
            10**24,   # yoctoseconds
            10**30,   # astronomical scale
            10**100,  # googol
            10**400,  # overflows Python float conversion (OverflowError)
        ]
        for val in extreme_values:
            result = normalize_iso_timestamp(val)
            assert isinstance(result, str)
            assert len(result) > 0
            # Must not crash and must produce an ISO-like or datetime string
            assert "T" in result or "-" in result

    def test_extreme_large_strings(self):
        """Extreme numeric strings must not crash."""
        large_strings = [
            "1" + "0" * 25,
            "1" + "0" * 100,
            "9" * 400,  # string that overflows float()
        ]
        for val in large_strings:
            result = normalize_iso_timestamp(val)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_negative_timestamps(self):
        """Negative timestamps (pre-1970) must either be parsed or gracefully fall back."""
        # -86400 is 1969-12-31T00:00:00+00:00
        res = normalize_iso_timestamp(-86400)
        assert res.startswith("1969-12-31")

        res_str = normalize_iso_timestamp("-86400")
        assert res_str.startswith("1969-12-31")

        # Zero epoch
        res_zero = normalize_iso_timestamp(0)
        assert res_zero.startswith("1970-01-01")

        # Massive negative values (out of range for platform datetime)
        extreme_negatives = [-1e18, -1e30, -10**100, -10**400]
        for neg in extreme_negatives:
            res_neg = normalize_iso_timestamp(neg)
            assert isinstance(res_neg, str)
            assert len(res_neg) > 0

    def test_float_infinities_and_nan(self):
        """Float inf, -inf, and nan must never hang or raise unhandled exceptions."""
        non_finites = [
            float("inf"),
            float("-inf"),
            float("nan"),
        ]
        for val in non_finites:
            res = normalize_iso_timestamp(val)
            assert isinstance(res, str)
            # Must return a valid current datetime ISO string
            dt = datetime.datetime.fromisoformat(res)
            now = datetime.datetime.now(datetime.timezone.utc)
            assert abs((dt - now).total_seconds()) < 5

    def test_string_infinities_and_nan(self):
        """String representations of inf, +inf, -inf, and nan must not crash."""
        str_non_finites = ["inf", "+inf", "-inf", "nan", "NaN", "Infinity", "-Infinity"]
        for val in str_non_finites:
            res = normalize_iso_timestamp(val)
            assert isinstance(res, str)
            assert len(res) > 0

    def test_malformed_and_non_primitive_types(self):
        """Various non-timestamp types and garbage strings must fallback gracefully."""
        bad_inputs = [
            None,
            "",
            "   ",
            "\n\t\r",
            [],
            [1, 2, 3],
            {},
            {"timestamp": 123},
            (1,),
            object(),
            b"2026-10-11",
        ]
        for item in bad_inputs:
            res = normalize_iso_timestamp(item)
            assert isinstance(res, str)
            assert len(res) > 0
            # Must return current datetime ISO string
            dt = datetime.datetime.fromisoformat(res)
            now = datetime.datetime.now(datetime.timezone.utc)
            assert abs((dt - now).total_seconds()) < 5


class TestSQLiteHarvestWithSubmillisecondTimestamps:
    """Verifies that ScreenLensClient correctly ingests microsecond and nanosecond timestamps from SQLite."""

    def test_sqlite_harvest_microsecond_timestamp(self, tmp_path: Path):
        """Harvesting from SQLite with a microsecond epoch preserves historical timestamp."""
        db_path = tmp_path / "micro_test.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE frames (id INTEGER PRIMARY KEY, timestamp INTEGER, app_name TEXT, window_title TEXT, ocr_text TEXT);"
        )
        # Microsecond timestamp for 2026-10-11T11:14:20.484000
        conn.execute(
            "INSERT INTO frames VALUES (1, 1791717260484000, 'CodeEditor', 'test.py', 'code content');"
        )
        conn.commit()
        conn.close()

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58991",
                    "ocr_stream_url": "http://127.0.0.1:58992",
                    "hud_mjpeg_url": "http://127.0.0.1:58993",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])
        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "CodeEditor"
        assert harvest["timestamp"].startswith("2026-10-11T11:14:20.484")

    def test_sqlite_harvest_nanosecond_timestamp(self, tmp_path: Path):
        """Harvesting from SQLite with a nanosecond epoch preserves historical timestamp."""
        db_path = tmp_path / "nano_test.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE frames (id INTEGER PRIMARY KEY, timestamp INTEGER, app_name TEXT, window_title TEXT, ocr_text TEXT);"
        )
        # Nanosecond timestamp for 2026-10-11T11:14:20.484000
        conn.execute(
            "INSERT INTO frames VALUES (1, 1791717260484000000, 'BrowserApp', 'docs', 'doc content');"
        )
        conn.commit()
        conn.close()

        offline_cfg = {
            "endpoints": {
                "screen_lens": {
                    "orchestrator_url": "http://127.0.0.1:58991",
                    "ocr_stream_url": "http://127.0.0.1:58992",
                    "hud_mjpeg_url": "http://127.0.0.1:58993",
                }
            }
        }
        client = ScreenLensClient(config_dict=offline_cfg, sqlite_db_paths=[db_path])
        harvest = client.harvest_perception(timeout_s=0.5)

        assert harvest["source"] == "sqlite"
        assert harvest["active_app"] == "BrowserApp"
        assert harvest["timestamp"].startswith("2026-10-11T11:14:20.484")
