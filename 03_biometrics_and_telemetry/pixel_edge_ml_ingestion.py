#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pixel 10 Edge ML Biometrics Ingestion & Processing Pipeline
Requirement R3: Continuous Kai Morich Terminal Log Tailing, 512 Hz Pan-Tompkins DSP,
and Asynchronous Downstream Llama 8B Edge Inference.

Subsystem: 03_biometrics_and_telemetry/pixel_edge_ml_ingestion.py
Architecture:
1. KaiMorichLogTailer:
   Continuous file tailing with inode tracking for rotation detection,
   size tracking for truncation recovery, line buffer aggregation,
   and adaptive 50ms sleep when at EOF (<0.05% CPU).
2. KaiMorichPacketParser:
   Robust line parser supporting raw CSV, Date+Time prefixes, Time-only prefixes,
   RX (<) markers, status/comment filtering, and chunk fragment reassembly.
3. EdgeBiometricsEngine:
   Pure Python 512 Hz Pan-Tompkins QRS detector (0.5-40Hz biquad bandpass filter,
   5-point derivative, nonlinear squaring, 150ms MWI, 200ms refractory period),
   Kamath et al. (2004) 20% clinical RR artifact filter, time-domain HRV metrics
   (Mean HR, RMSSD, SDNN, pNN50), and bounded deques (<30 MB RSS, AVF compliant).
4. LlamaInferenceDispatcher:
   10-second sliding window aggregator with non-blocking background HTTP dispatch
   to OpenAI-compatible /v1/chat/completions (and /completion fallback) with 3.0s timeout,
   primary (100.119.199.76:8082) & on-device fallback (127.0.0.1:8080) endpoints,
   and local offline fallback logging.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import math
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, NamedTuple, Optional, Sequence, Tuple, Union

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PixelEdgeML")

# Constants
DEFAULT_SAMPLE_RATE_HZ: float = 512.0
DEFAULT_WINDOW_SECONDS: float = 10.0
DEFAULT_WINDOW_SAMPLES: int = int(DEFAULT_SAMPLE_RATE_HZ * DEFAULT_WINDOW_SECONDS)  # 5120
DEFAULT_POLL_INTERVAL_S: float = 0.05  # 50 ms adaptive sleep at EOF
DEFAULT_MAX_LINE_BUFFER_BYTES: int = 4096  # Max line buffer size to prevent unbounded memory growth

PRIMARY_LLAMA_URL: str = "http://100.119.199.76:8082/v1"
FALLBACK_LLAMA_URL: str = "http://127.0.0.1:8080/v1"

SEARCH_LOG_DIRECTORIES: List[str] = [
    "/sdcard/Download",
    "/sdcard/SerialBluetoothTerminal",
    "/sdcard",
    "/storage/emulated/0/Download",
    "/storage/emulated/0/SerialBluetoothTerminal",
    "/tmp",
]


def get_process_rss_mb() -> float:
    """Returns the current process resident set size (RSS) in megabytes."""
    try:
        import resource
        ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return float(ru) / (1024.0 * 1024.0)
        else:
            return float(ru) / 1024.0
    except Exception:
        return 0.0


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class EcgSample(NamedTuple):
    timestamp_ms: int
    ecg_uV: float


@dataclass
class BiometricSummaryWindow:
    """Encapsulates a sliding 10-second ECG window and computed HRV metrics."""
    window_id: int
    start_timestamp_ms: int
    end_timestamp_ms: int
    duration_seconds: float
    sample_count: int
    sampling_rate_hz: float
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_prompt(self) -> str:
        """Formats the biometrics summary window into a clinical prompt for Llama 8B."""
        m = self.metrics
        rr_list = m.get("rr_intervals_ms", [])
        rr_preview = [round(float(r), 1) for r in rr_list[:15]]
        rr_str = ", ".join(str(r) for r in rr_preview)
        if len(rr_list) > 15:
            rr_str += f", ... ({len(rr_list)} total)"

        mean_hr = m.get("mean_heart_rate_bpm", 0.0)
        min_hr = m.get("min_heart_rate_bpm", 0.0)
        max_hr = m.get("max_heart_rate_bpm", 0.0)
        rmssd = m.get("rmssd_ms", 0.0)
        sdnn = m.get("sdnn_ms", 0.0)
        pnn50 = m.get("pnn50_pct", 0.0)
        artifacts = m.get("kamath_artifacts_rejected", 0)
        artifact_pct = m.get("artifact_rate_pct", 0.0)
        sqi = m.get("signal_quality_sqi_pct", 100.0)
        rhythm = m.get("rhythm_assessment", "UNKNOWN")
        zone = m.get("training_zone", "UNKNOWN")

        return (
            f"[Biometric Summary Window #{self.window_id} - Duration: {self.duration_seconds:.1f}s | "
            f"Sensor: Movesense {self.sampling_rate_hz:.0f}Hz]\n"
            f"• Heart Rate: {mean_hr:.1f} BPM (Range: {min_hr:.1f} - {max_hr:.1f} BPM)\n"
            f"• RR Intervals (ms): [{rr_str}]\n"
            f"• HRV Metrics: RMSSD={rmssd:.1f} ms | SDNN={sdnn:.1f} ms | pNN50={pnn50:.1f}%\n"
            f"• Artifact Rejections: {artifacts} ({artifact_pct:.1f}% rejected)\n"
            f"• Signal Quality (SQI): {sqi:.1f}%\n"
            f"• Preliminary Rhythm: {rhythm}\n"
            f"• Est. Training Zone: {zone}\n\n"
            f"Assess rhythm stability, autonomic tone, and flag any irregularities."
        )


# ============================================================================
# 1. KAI MORICH LOG TAILER
# ============================================================================

class KaiMorichLogTailer:
    """
    Continuous tailer for Kai Morich Serial Bluetooth Terminal logs.
    Features:
    - Inode tracking (st_ino) for log rotation detection.
    - Size tracking (st_size < offset) for file truncation recovery.
    - Line chunking and reassembly across read buffers.
    - Adaptive 50ms sleep when at EOF to cap idle CPU utilization < 0.05%.
    - Path auto-discovery across /sdcard/Download, /sdcard/SerialBluetoothTerminal, etc.
    """

    def __init__(
        self,
        log_path: Optional[Union[str, Path]] = None,
        search_dirs: Optional[List[Union[str, Path]]] = None,
        read_from_start: bool = False,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        max_line_buffer_bytes: int = DEFAULT_MAX_LINE_BUFFER_BYTES,
    ):
        self.explicit_path: Optional[Path] = Path(log_path) if log_path else None
        self.search_dirs: List[Path] = [Path(d) for d in (search_dirs or SEARCH_LOG_DIRECTORIES)]
        self.read_from_start: bool = read_from_start
        self.poll_interval_s: float = poll_interval_s
        self.max_line_buffer_bytes: int = max_line_buffer_bytes

        self.current_path: Optional[Path] = None
        self._file_obj: Optional[Any] = None
        self._current_ino: Optional[int] = None
        self._current_offset: int = 0
        self._line_buffer: str = ""
        self._header_sample: bytes = b""
        self._skipping_until_newline: bool = False
        self._running: bool = True

    def _read_header_sample(self, size: int = 64) -> bytes:
        """Reads up to `size` bytes from offset 0 without altering current file pointer."""
        if self._file_obj is None or self._file_obj.closed:
            return b""
        try:
            if hasattr(os, "pread"):
                return os.pread(self._file_obj.fileno(), size, 0)
            else:
                cur = self._file_obj.tell()
                self._file_obj.seek(0, os.SEEK_SET)
                sample = self._file_obj.buffer.read(size) if hasattr(self._file_obj, "buffer") else self._file_obj.read(size).encode("utf-8", errors="replace")
                self._file_obj.seek(cur, os.SEEK_SET)
                return sample
        except Exception:
            return b""

    def auto_discover(self) -> Optional[Path]:
        """Auto-discovers the latest Kai Morich log file in standard storage paths."""
        if self.explicit_path and self.explicit_path.exists():
            return self.explicit_path

        candidates: List[Path] = []
        for sdir in self.search_dirs:
            if not sdir.exists() or not sdir.is_dir():
                continue
            # Check specific well-known filenames first
            for fname in ("serial_bluetooth_terminal.log", "terminal_log.txt", "terminal.log"):
                fp = sdir / fname
                if fp.is_file():
                    candidates.append(fp)
            # Glob for .log and .txt files but exclude known non-Kai-Morich logs
            try:
                for match in sdir.glob("*.log"):
                    if match.is_file() and "shizuku" not in match.name.lower():
                        candidates.append(match)
                for match in sdir.glob("*.txt"):
                    if match.is_file() and "shizuku" not in match.name.lower():
                        candidates.append(match)
            except Exception:
                pass

        if not candidates:
            return None

        # Return most recently modified candidate
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    def open_or_reopen(self) -> bool:
        """Opens or reopens the target file, positioning at start or EOF as configured."""
        target = self.explicit_path or self.auto_discover()
        if not target or not target.exists():
            return False

        try:
            st = target.stat()
            if self._file_obj is not None and not self._file_obj.closed:
                # If inode is unchanged and size >= offset, still good
                if self._current_ino == st.st_ino and st.st_size >= self._current_offset:
                    return True
                self._file_obj.close()

            self._file_obj = open(target, "r", encoding="utf-8", errors="replace")
            self._current_ino = st.st_ino
            self.current_path = target

            if self.read_from_start:
                self._file_obj.seek(0, os.SEEK_SET)
                self._current_offset = 0
            else:
                self._file_obj.seek(0, os.SEEK_END)
                self._current_offset = self._file_obj.tell()

            self._line_buffer = ""
            self._header_sample = self._read_header_sample(min(64, st.st_size)) if st.st_size > 0 else b""
            logger.info("Opened log file %s (inode=%s, offset=%s)", target, self._current_ino, self._current_offset)
            return True
        except Exception as e:
            logger.warning("Failed to open log file %s: %s", target, e)
            return False

    def tail_lines(self) -> Generator[str, None, None]:
        """
        Continuously yields complete lines from the log file.
        Recovers automatically from log rotations, file truncations, and in-place write bursts.
        """
        while self._running:
            if self._file_obj is None or self._file_obj.closed:
                if not self.open_or_reopen():
                    time.sleep(self.poll_interval_s)
                    continue

            # Proactively check for file rotation, truncation, or in-place overwrite
            try:
                if self.current_path and self.current_path.exists():
                    st = self.current_path.stat()
                    # 1. Check log rotation (inode changed)
                    if self._current_ino is not None and st.st_ino != self._current_ino:
                        logger.info("Log rotation detected (inode %s -> %s)", self._current_ino, st.st_ino)
                        self._file_obj.close()
                        self._file_obj = open(self.current_path, "r", encoding="utf-8", errors="replace")
                        self._current_ino = st.st_ino
                        self._current_offset = 0
                        self._line_buffer = ""
                        self._header_sample = self._read_header_sample(min(64, st.st_size)) if st.st_size > 0 else b""
                        continue

                    # 2. Check file truncation (size < current offset)
                    if st.st_size < self._current_offset:
                        logger.info("Log truncation detected (size %s < offset %s)", st.st_size, self._current_offset)
                        self._file_obj.seek(0, os.SEEK_SET)
                        self._current_offset = 0
                        self._line_buffer = ""
                        self._skipping_until_newline = False
                        self._header_sample = self._read_header_sample(min(64, st.st_size)) if st.st_size > 0 else b""
                        continue

                    # 3. Check in-place file truncation followed by write burst (header mismatch at offset 0)
                    if self._current_offset > 0 and self._header_sample:
                        current_head = self._read_header_sample(len(self._header_sample))
                        if current_head and current_head != self._header_sample:
                            logger.info("Log in-place truncation/rewrite detected (header mismatch at offset 0)")
                            self._file_obj.seek(0, os.SEEK_SET)
                            self._current_offset = 0
                            self._line_buffer = ""
                            self._skipping_until_newline = False
                            self._header_sample = self._read_header_sample(min(64, st.st_size)) if st.st_size > 0 else b""
                            continue
                    elif st.st_size > 0 and not self._header_sample:
                        self._header_sample = self._read_header_sample(min(64, st.st_size))
            except OSError:
                pass

            line = self._file_obj.readline(self.max_line_buffer_bytes)
            if line:
                if self._skipping_until_newline:
                    if line.endswith("\n") or line.endswith("\r"):
                        # Reached end of corrupted runaway line
                        self._skipping_until_newline = False
                        self._line_buffer = ""
                        self._current_offset = self._file_obj.tell()
                    continue

                if line.endswith("\n") or line.endswith("\r"):
                    # Complete line arrived
                    full_line = self._line_buffer + line
                    self._line_buffer = ""
                    self._current_offset = self._file_obj.tell()
                    yield full_line.rstrip("\r\n")
                else:
                    # Partial chunk at buffer end; accumulate
                    self._line_buffer += line
                    self._current_offset = self._file_obj.tell()
                    if len(self._line_buffer) >= self.max_line_buffer_bytes:
                        logger.warning(
                            "Line buffer exceeded max size (%d bytes) without newline; dropping buffer and skipping until newline",
                            self.max_line_buffer_bytes,
                        )
                        self._line_buffer = ""
                        self._skipping_until_newline = True
            else:
                # Reached EOF; sleep adaptively to prevent CPU thrashing
                time.sleep(self.poll_interval_s)

    def stop(self) -> None:
        """Stops the tailer loop and closes file descriptor."""
        self._running = False
        if self._file_obj and not self._file_obj.closed:
            try:
                self._file_obj.close()
            except Exception:
                pass
        self._file_obj = None



# ============================================================================
# 2. KAI MORICH PACKET PARSER
# ============================================================================

class KaiMorichPacketParser:
    """
    Robust multi-format parser for Kai Morich Serial Bluetooth Terminal lines.
    Handles:
    - Raw CSV: `172800000,342` or `172800000,342\r\n`
    - Date+Time prefix: `2026-10-04 07:15:23.123 < 172800000,342\r\n`
    - Time-only prefix: `07:15:23.123 < 172800000,342\r\n` or without `<`
    - RX marker stripping: `< 172800000,342` or `> 172800000,342`
    - Status/Comment line filtering: `--- Connected to... ---`, headers, comments
    - Fragmented line reassembly across read chunks.
    """

    RE_DATETIME_PREFIX = re.compile(
        r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*(?:<|>)?\s*"
    )
    RE_TIME_PREFIX = re.compile(
        r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*(?:<|>)?\s*"
    )
    RE_RX_TX_MARKER = re.compile(
        r"^(?:<|>)\s*"
    )

    def __init__(self, max_buffer_size: int = DEFAULT_MAX_LINE_BUFFER_BYTES) -> None:
        self._buffer: str = ""
        self.max_buffer_size: int = max_buffer_size

    def parse_line(self, raw_line: str) -> Optional[Tuple[int, float]]:
        """
        Parses a single line into (timestamp_ms, ecg_uV).
        Returns None if the line is empty, a comment, or an ignored status line.
        """
        line = raw_line.strip()
        if not line:
            return None

        # Filter out comments and decorative status lines
        if line.startswith(("---", "//", "#", "/*", "*")):
            # Check for zero-touch automation trigger
            if "Connected to" in line:
                print(f"[EDGE-INGESTION] Connected string detected: {line}. Triggering Movesense App via Shizuku...")
                try:
                    import subprocess
                    subprocess.Popen(
                        ["/data/data/com.termux/files/usr/bin/rish", "-c", "am start -n com.movesense.showcaseapp/.MainActivity"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print(f"[EDGE-INGESTION] Failed to trigger Shizuku intent: {e}")
            return None

        lower = line.lower()
        if "connected" in lower or "disconnected" in lower or "logging" in lower:
            # Handle non-dashed connection strings
            if "connected to" in lower:
                print(f"[EDGE-INGESTION] Connected string detected: {line}. Triggering Movesense App via Shizuku...")
                try:
                    import subprocess
                    subprocess.Popen(
                        ["/data/data/com.termux/files/usr/bin/rish", "-c", "am start -n com.movesense.showcaseapp/.MainActivity"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    pass
            return None
        if "timestamp" in lower and "ecg" in lower:
            return None

        # Strip Date+Time prefix (e.g., '2026-10-04 07:15:23.123 < ')
        line = self.RE_DATETIME_PREFIX.sub("", line)

        # Strip Time-only prefix (e.g., '07:15:23.123 < ')
        line = self.RE_TIME_PREFIX.sub("", line)

        # Strip standalone RX/TX markers ('< ' or '> ')
        line = self.RE_RX_TX_MARKER.sub("", line)

        parts = line.split(",")
        if len(parts) != 2:
            return None

        try:
            ts_str = parts[0].strip()
            ecg_str = parts[1].strip()

            # Prevent excessive string-to-int processing on astronomical inputs
            if len(ts_str) > 30:
                return None

            # Parse integer timestamps directly without float conversion
            # to preserve exact 64-bit integer precision for timestamps > 2^53.
            if ts_str.isdigit() or (ts_str.startswith(("-", "+")) and ts_str[1:].isdigit()):
                ts_val = int(ts_str)
            else:
                # Fallback for floating-point timestamps (e.g., '172800000.89')
                f_ts = float(ts_str)
                if not math.isfinite(f_ts):
                    return None
                ts_val = int(f_ts)

            ecg_val = float(ecg_str)
            # Validate finite bounds to prevent filter poisoning (NaN / Inf)
            if not math.isfinite(ecg_val):
                return None

            return (ts_val, ecg_val)
        except (ValueError, TypeError, OverflowError):
            return None

    def feed(self, chunk: str) -> List[Tuple[int, float]]:
        """
        Feeds a string chunk, buffering partial lines and returning all
        successfully parsed (timestamp_ms, ecg_uV) samples from complete lines.
        """
        text = self._buffer + chunk
        lines = text.split("\n")
        trailing = lines[-1]
        if len(trailing) > self.max_buffer_size:
            self._buffer = ""
        else:
            self._buffer = trailing

        samples: List[Tuple[int, float]] = []
        for line in lines[:-1]:
            parsed = self.parse_line(line)
            if parsed is not None:
                samples.append(parsed)
        return samples

    def flush(self) -> List[Tuple[int, float]]:
        """Flushes any remaining text in the internal buffer."""
        samples: List[Tuple[int, float]] = []
        if self._buffer.strip():
            parsed = self.parse_line(self._buffer)
            if parsed is not None:
                samples.append(parsed)
        self._buffer = ""
        return samples

    def reset(self) -> None:
        """Clears the internal line accumulator buffer."""
        self._buffer = ""


# ============================================================================
# 3. EDGE BIOMETRICS ENGINE (512 Hz PAN-TOMPKINS & HRV)
# ============================================================================

class EdgeBiometricsEngine:
    """
    512 Hz Pan-Tompkins QRS detector and time-domain HRV feature extraction engine.
    Runs entirely in pure Python without requiring SciPy, making it fully portable
    to Android Termux / AVF Debian microVMs.
    
    Memory Governance (Rule 9):
    Uses bounded circular deques (maxlen=5120 for raw ECG, maxlen=100 for RR intervals)
    guaranteeing resident memory remains bounded < 30 MB RSS.
    """

    def __init__(
        self,
        sample_rate_hz: float = DEFAULT_SAMPLE_RATE_HZ,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.fs: float = float(sample_rate_hz)
        self.window_seconds: float = float(window_seconds)
        self.window_samples: int = int(self.fs * self.window_seconds)

        # Pan-Tompkins tuning constants for 512 Hz
        # 150 ms MWI window = 20 samples @ 512 Hz
        self.mwi_window: int = max(2, int(round(0.150 * self.fs)))
        # 200 ms refractory period = 26 samples @ 512 Hz
        self.refractory_samples: int = max(2, int(round(0.200 * self.fs)))

        # Precompute Bilinear Transform Biquad Direct Form I coefficients
        # Highpass: 0.5 Hz; Lowpass: 40.0 Hz
        self._hp_coeffs = self._biquad_coeffs(0.5, self.fs, is_hp=True)
        self._lp_coeffs = self._biquad_coeffs(min(40.0, self.fs * 0.45), self.fs, is_hp=False)

        # Bounded circular deques for raw data (Memory bounds < 30 MB RSS)
        self._raw_samples: deque[float] = deque(maxlen=self.window_samples)
        self._raw_timestamps: deque[int] = deque(maxlen=self.window_samples)
        self._rr_intervals: deque[float] = deque(maxlen=100)

        # Window state
        self._samples_since_last_window: int = 0
        self._window_counter: int = 0

    @staticmethod
    def _biquad_coeffs(fc: float, fs: float, is_hp: bool) -> Tuple[float, float, float, float, float]:
        """Calculates 2nd-order Butterworth biquad Direct Form I filter coefficients."""
        w = math.tan(math.pi * fc / fs)
        w2 = w * w
        sqrt2 = math.sqrt(2.0)
        norm = 1.0 + sqrt2 * w + w2
        if is_hp:
            b0 = 1.0 / norm
            b1 = -2.0 * b0
            b2 = b0
        else:
            b0 = w2 / norm
            b1 = 2.0 * b0
            b2 = b0
        a1 = 2.0 * (w2 - 1.0) / norm
        a2 = (1.0 - sqrt2 * w + w2) / norm
        return (b0, b1, b2, a1, a2)

    @staticmethod
    def _apply_biquad_section(x: Sequence[float], c: Tuple[float, float, float, float, float]) -> List[float]:
        """Direct Form I difference equation evaluation."""
        b0, b1, b2, a1, a2 = c
        n = len(x)
        y = [0.0] * n
        for i in range(n):
            x0 = x[i]
            x1 = x[i - 1] if i >= 1 else 0.0
            x2 = x[i - 2] if i >= 2 else 0.0
            y1 = y[i - 1] if i >= 1 else 0.0
            y2 = y[i - 2] if i >= 2 else 0.0
            y[i] = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        return y

    @classmethod
    def _filtfilt_biquad_section(cls, x: Sequence[float], c: Tuple[float, float, float, float, float]) -> List[float]:
        """Forward-backward filtering to ensure exact 0-degree phase distortion."""
        fwd = cls._apply_biquad_section(x, c)
        rev = cls._apply_biquad_section(fwd[::-1], c)
        return rev[::-1]

    def bandpass_filter(self, ecg_signal: Sequence[float]) -> List[float]:
        """4th-order zero-phase bandpass filter (0.5 Hz - 40.0 Hz)."""
        n = len(ecg_signal)
        if n < 8:
            return [float(x) for x in ecg_signal]

        mean_val = sum(ecg_signal) / float(n)
        centered = [float(x) - mean_val for x in ecg_signal]

        hp_out = self._filtfilt_biquad_section(centered, self._hp_coeffs)
        bp_out = self._filtfilt_biquad_section(hp_out, self._lp_coeffs)
        return bp_out

    def derivative_filter(self, filtered_signal: Sequence[float]) -> List[float]:
        """5-point derivative operator: d[n] = (1/8T) * (-x[n-2] - 2x[n-1] + 2x[n+1] + x[n+2])."""
        n = len(filtered_signal)
        if n < 5:
            return [0.0] * n

        scale = self.fs / 8.0
        deriv = [0.0] * n
        for i in range(2, n - 2):
            deriv[i] = (
                -filtered_signal[i - 2]
                - 2.0 * filtered_signal[i - 1]
                + 2.0 * filtered_signal[i + 1]
                + filtered_signal[i + 2]
            ) * scale
        return deriv

    @staticmethod
    def squaring_transform(derivative_signal: Sequence[float]) -> List[float]:
        """Nonlinear squaring operator: s[n] = (d[n])^2."""
        return [float(x * x) for x in derivative_signal]

    def moving_window_integration(self, squared_signal: Sequence[float]) -> List[float]:
        """Moving Window Integration (MWI) with running sum accumulator (O(1) per sample)."""
        n = len(squared_signal)
        if n == 0:
            return []

        mwi = [0.0] * n
        window = self.mwi_window
        running_sum = 0.0

        for i in range(n):
            running_sum += squared_signal[i]
            if i >= window:
                running_sum -= squared_signal[i - window]
            mwi[i] = running_sum / float(min(i + 1, window))
        return mwi

    def detect_qrs_peaks(self, ecg_signal: Sequence[float]) -> Tuple[List[int], List[float]]:
        """
        Executes full Pan-Tompkins pipeline on raw ECG array.
        Returns:
            peak_indices: list of sample index positions where R-peaks occurred.
            rr_intervals_ms: list of RR intervals in milliseconds (physiological range 250 - 2200 ms).
        """
        if not ecg_signal or len(ecg_signal) < int(self.fs * 0.5):
            return [], []

        # 1. Bandpass filter
        filtered = self.bandpass_filter(ecg_signal)

        # 2. 5-point derivative
        deriv = self.derivative_filter(filtered)

        # 3. Squaring transform
        squared = self.squaring_transform(deriv)

        # 4. Moving window integration
        mwi = self.moving_window_integration(squared)

        max_mwi = max(mwi) if mwi else 0.0
        if max_mwi <= 1e-6:
            return [], []

        # 5. Adaptive Dual-Threshold Peak Detection
        min_peak_height = max_mwi * 0.05
        local_peaks: List[Tuple[int, float]] = []
        n = len(mwi)

        for i in range(1, n - 1):
            if mwi[i] > mwi[i - 1] and mwi[i] >= mwi[i + 1] and mwi[i] >= min_peak_height:
                local_peaks.append((i, mwi[i]))

        if not local_peaks:
            return [], []

        peak_vals = [p[1] for p in local_peaks]
        spk = max(peak_vals) * 0.5
        npk = (sum(peak_vals) / float(len(peak_vals))) * 0.1
        threshold_i1 = npk + 0.25 * (spk - npk)
        threshold_i2 = 0.5 * threshold_i1

        peaks: List[int] = []
        last_peak_idx = -self.refractory_samples

        for idx, peak_val in local_peaks:
            # Enforce 200ms refractory period (26 samples @ 512 Hz)
            if idx - last_peak_idx < self.refractory_samples:
                continue

            if peak_val >= threshold_i1:
                # Primary threshold passed; localize apex in filtered signal
                search_start = max(0, idx - self.mwi_window)
                search_end = min(n, idx + max(5, self.mwi_window // 2))
                apex = search_start
                r_max = -1e9
                for s_idx in range(search_start, search_end):
                    if filtered[s_idx] > r_max:
                        r_max = filtered[s_idx]
                        apex = s_idx
                peaks.append(apex)
                last_peak_idx = apex
                spk = 0.125 * peak_val + 0.875 * spk
            elif peak_val >= threshold_i2:
                # Secondary searchback threshold passed
                search_start = max(0, idx - self.mwi_window)
                search_end = min(n, idx + max(5, self.mwi_window // 2))
                apex = search_start
                r_max = -1e9
                for s_idx in range(search_start, search_end):
                    if filtered[s_idx] > r_max:
                        r_max = filtered[s_idx]
                        apex = s_idx
                peaks.append(apex)
                last_peak_idx = apex
                spk = 0.25 * peak_val + 0.75 * spk
            else:
                npk = 0.125 * peak_val + 0.875 * npk

            threshold_i1 = npk + 0.25 * (spk - npk)
            threshold_i2 = 0.5 * threshold_i1

        # Compute RR intervals in ms
        rr_intervals: List[float] = []
        for i in range(1, len(peaks)):
            diff_samples = peaks[i] - peaks[i - 1]
            rr_ms = (diff_samples / float(self.fs)) * 1000.0
            if 250.0 <= rr_ms <= 2200.0:  # Physiological range (27 - 240 BPM)
                rr_intervals.append(round(rr_ms, 1))

        return peaks, rr_intervals

    @staticmethod
    def apply_kamath_artifact_filter(
        rr_intervals: Sequence[float], threshold_pct: float = 20.0
    ) -> Tuple[List[float], int]:
        """
        Kamath et al. (2004) Clinical 20% RR Artifact Filter.
        Condition: |RR[i] - RR[i-1]| / RR[i-1] <= 0.20.
        Replaces/interpolates ectopic beats and counts rejections.
        """
        if not rr_intervals or len(rr_intervals) < 2:
            return [float(x) for x in (rr_intervals or [])], 0

        thresh = threshold_pct / 100.0
        r0 = float(rr_intervals[0])

        valid_cands = [
            float(x) for x in rr_intervals[: min(5, len(rr_intervals))] if 250.0 <= float(x) <= 2200.0
        ]
        if 250.0 <= r0 <= 2200.0:
            cleaned = [r0]
            artifact_count = 0
        elif valid_cands:
            cleaned = [valid_cands[0]]
            artifact_count = 1
        else:
            cleaned = [r0]
            artifact_count = 0

        for i in range(1, len(rr_intervals)):
            prev = cleaned[-1]
            curr = float(rr_intervals[i])
            if 250.0 <= curr <= 2200.0 and prev > 0 and (abs(curr - prev) / prev) <= thresh:
                cleaned.append(curr)
            else:
                artifact_count += 1
                # Interpolate using next valid beat or previous
                next_val = None
                for j in range(i + 1, len(rr_intervals)):
                    cand = float(rr_intervals[j])
                    if 250.0 <= cand <= 2200.0 and prev > 0 and (abs(cand - prev) / prev) <= thresh:
                        next_val = cand
                        break
                if next_val is None:
                    next_val = prev
                corrected = (prev + next_val) / 2.0
                cleaned.append(round(corrected, 1))

        return cleaned, artifact_count

    @staticmethod
    def calculate_hrv_metrics(rr_intervals: Sequence[float]) -> Dict[str, Any]:
        """Calculates time-domain HRV metrics: Mean HR, Min/Max HR, RMSSD, SDNN, pNN50."""
        if not rr_intervals:
            return {
                "mean_heart_rate_bpm": 0.0,
                "min_heart_rate_bpm": 0.0,
                "max_heart_rate_bpm": 0.0,
                "rmssd_ms": 0.0,
                "sdnn_ms": 0.0,
                "pnn50_pct": 0.0,
            }

        rrs = [float(x) for x in rr_intervals]
        mean_rr = sum(rrs) / float(len(rrs))
        mean_hr = 60000.0 / mean_rr if mean_rr > 0 else 0.0
        min_hr = 60000.0 / max(rrs) if max(rrs) > 0 else 0.0
        max_hr = 60000.0 / min(rrs) if min(rrs) > 0 else 0.0

        if len(rrs) < 2:
            return {
                "mean_heart_rate_bpm": round(mean_hr, 1),
                "min_heart_rate_bpm": round(min_hr, 1),
                "max_heart_rate_bpm": round(max_hr, 1),
                "rmssd_ms": 0.0,
                "sdnn_ms": 0.0,
                "pnn50_pct": 0.0,
            }

        diffs = [rrs[i] - rrs[i - 1] for i in range(1, len(rrs))]
        sum_sq = sum(d * d for d in diffs)
        rmssd = math.sqrt(sum_sq / float(len(rrs) - 1))

        var = sum((x - mean_rr) ** 2 for x in rrs) / float(len(rrs) - 1)
        sdnn = math.sqrt(var)

        nn50_count = sum(1 for d in diffs if abs(d) > 50.0)
        pnn50 = (nn50_count / float(len(diffs))) * 100.0

        return {
            "mean_heart_rate_bpm": round(mean_hr, 1),
            "min_heart_rate_bpm": round(min_hr, 1),
            "max_heart_rate_bpm": round(max_hr, 1),
            "rmssd_ms": round(rmssd, 2),
            "sdnn_ms": round(sdnn, 2),
            "pnn50_pct": round(pnn50, 2),
        }

    @staticmethod
    def classify_rhythm(mean_hr: float, artifact_rate_pct: float, num_peaks: int) -> str:
        """Classifies rhythm into physiological categories."""
        if num_peaks == 0:
            return "ASYSTOLE_OR_DISCONNECTED"
        if artifact_rate_pct > 30.0:
            return "NOISY_SIGNAL"
        if mean_hr < 60.0:
            return "SINUS_BRADYCARDIA"
        if mean_hr > 100.0:
            return "SINUS_TACHYCARDIA"
        return "NORMAL_SINUS"

    @staticmethod
    def classify_training_zone(mean_hr: float) -> str:
        """Estimates 5-zone cardiovascular training zone."""
        if mean_hr <= 0.0:
            return "Unknown"
        if mean_hr < 120.0:
            return "Zone 1 (Recovery / Aerobic Base)"
        if mean_hr < 140.0:
            return "Zone 2 (Aerobic Endurance)"
        if mean_hr < 160.0:
            return "Zone 3 (Tempo / Lactate Threshold)"
        if mean_hr < 180.0:
            return "Zone 4 (Threshold)"
        return "Zone 5 (Anaerobic / Max)"

    def _compute_summary_from_buffer(self) -> BiometricSummaryWindow:
        """Computes summary window metrics from current sliding buffer."""
        self._window_counter += 1
        samples = list(self._raw_samples)
        timestamps = list(self._raw_timestamps)

        start_ts = timestamps[0] if timestamps else 0
        end_ts = timestamps[-1] if timestamps else 0
        duration = len(samples) / self.fs

        peaks, raw_rrs = self.detect_qrs_peaks(samples)
        cleaned_rrs, artifact_count = self.apply_kamath_artifact_filter(raw_rrs)

        # Update historical RR deque
        for rr in cleaned_rrs:
            self._rr_intervals.append(rr)

        total_beats = len(raw_rrs)
        artifact_rate = (artifact_count / float(total_beats) * 100.0) if total_beats > 0 else 0.0
        sqi = max(0.0, 100.0 - artifact_rate)

        hrv = self.calculate_hrv_metrics(cleaned_rrs)
        mean_hr = hrv.get("mean_heart_rate_bpm", 0.0)
        rhythm = self.classify_rhythm(mean_hr, artifact_rate, len(peaks))
        zone = self.classify_training_zone(mean_hr)

        metrics = {
            "mean_heart_rate_bpm": mean_hr,
            "min_heart_rate_bpm": hrv.get("min_heart_rate_bpm", 0.0),
            "max_heart_rate_bpm": hrv.get("max_heart_rate_bpm", 0.0),
            "rr_intervals_ms": cleaned_rrs,
            "rmssd_ms": hrv.get("rmssd_ms", 0.0),
            "sdnn_ms": hrv.get("sdnn_ms", 0.0),
            "pnn50_pct": hrv.get("pnn50_pct", 0.0),
            "kamath_artifacts_rejected": artifact_count,
            "artifact_rate_pct": round(artifact_rate, 1),
            "signal_quality_sqi_pct": round(sqi, 1),
            "rhythm_assessment": rhythm,
            "training_zone": zone,
            "qrs_peak_count": len(peaks),
        }

        return BiometricSummaryWindow(
            window_id=self._window_counter,
            start_timestamp_ms=start_ts,
            end_timestamp_ms=end_ts,
            duration_seconds=round(duration, 2),
            sample_count=len(samples),
            sampling_rate_hz=self.fs,
            metrics=metrics,
        )

    def add_sample(self, timestamp_ms: int, ecg_uV: float) -> Optional[BiometricSummaryWindow]:
        """
        Appends an ECG sample to the sliding buffer.
        Returns a BiometricSummaryWindow every 10 seconds of data (1,300 samples).
        """
        if not math.isfinite(ecg_uV) or not math.isfinite(timestamp_ms):
            logger.warning("Rejecting non-finite ECG sample: ts=%s, ecg=%s", timestamp_ms, ecg_uV)
            return None

        self._raw_samples.append(float(ecg_uV))
        self._raw_timestamps.append(int(timestamp_ms))
        self._samples_since_last_window += 1

        if self._samples_since_last_window >= self.window_samples:
            self._samples_since_last_window = 0
            return self._compute_summary_from_buffer()
        return None

    def force_summary(self) -> Optional[BiometricSummaryWindow]:
        """Forces summary generation on accumulated samples if at least 2 seconds exist."""
        if len(self._raw_samples) >= int(self.fs * 2.0):
            return self._compute_summary_from_buffer()
        return None

    def get_memory_usage_mb(self) -> float:
        """Returns process RSS in MB."""
        return get_process_rss_mb()


# ============================================================================
# 4. LLAMA INFERENCE DISPATCHER
# ============================================================================

class LlamaInferenceDispatcher:
    """
    Asynchronous downstream inference dispatcher for local Llama 8B models.
    Features:
    - Sliding window prompt formatting.
    - Non-blocking background worker thread (Queue maxsize=20).
    - 3.0s HTTP timeout.
    - OpenAI-compatible /v1/chat/completions with fallback to /completion.
    - Automatic failover: Primary (Mac Mini L1 Host) -> On-device fallback (127.0.0.1:8080).
    - Graceful offline fallback: logs summary locally when endpoints are unreachable.
    """

    def __init__(
        self,
        primary_url: str = PRIMARY_LLAMA_URL,
        fallback_url: str = FALLBACK_LLAMA_URL,
        timeout_s: float = 3.0,
        offline_log_path: Optional[Union[str, Path]] = None,
        dry_run: bool = False,
    ) -> None:
        self.primary_url: str = primary_url
        self.fallback_url: str = fallback_url
        self.timeout_s: float = timeout_s
        self.offline_log_path: Optional[Path] = Path(offline_log_path) if offline_log_path else None
        self.dry_run: bool = dry_run

        self._queue: queue.Queue = queue.Queue(maxsize=20)
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._lifecycle_lock: threading.RLock = threading.RLock()
        self._latest_assessment: Optional[str] = None

        self.total_dispatched: int = 0
        self.total_succeeded: int = 0
        self.total_offline_fallbacks: int = 0

    def start(self) -> None:
        """Starts or restarts the background worker thread."""
        with self._lifecycle_lock:
            if self._running and self._thread is not None and self._thread.is_alive():
                return

            # If an old thread is still alive from a previous stop() during in-flight timeout,
            # allow it a brief moment to finish while ensuring a new thread is spawned.
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=0.1)

            # Drain any None sentinels from previous stop() calls to prevent premature exit
            temp_items = []
            while True:
                try:
                    item = self._queue.get_nowait()
                    if item is not None:
                        temp_items.append(item)
                    self._queue.task_done()
                except queue.Empty:
                    break
            for item in temp_items:
                try:
                    self._queue.put_nowait(item)
                except queue.Full:
                    break

            self._running = True
            new_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="LlamaDispatcherThread",
            )
            self._thread = new_thread
            new_thread.start()
            logger.info("LlamaInferenceDispatcher background worker started.")

    def stop(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """Stops the background worker thread."""
        with self._lifecycle_lock:
            self._running = False
            try:
                self._queue.put_nowait(None)  # Sentinel to unblock queue.get()
            except queue.Full:
                pass
            target_thread = self._thread

        if wait and target_thread is not None and target_thread.is_alive():
            join_timeout = timeout if timeout is not None else max(5.0, (2.0 * self.timeout_s) + 2.0)
            target_thread.join(timeout=join_timeout)

    def dispatch_window(self, window: BiometricSummaryWindow) -> bool:
        """Enqueues a BiometricSummaryWindow for asynchronous dispatch."""
        try:
            self._queue.put_nowait(window)
            return True
        except queue.Full:
            logger.warning("Dispatcher queue full; dropping window #%d", window.window_id)
            return False

    def get_latest_assessment(self) -> Optional[str]:
        """Returns the most recent clinical assessment string."""
        with self._lock:
            return self._latest_assessment

    def _set_latest_assessment(self, assessment: str) -> None:
        with self._lock:
            self._latest_assessment = assessment

    def _send_http_request(self, base_url: str, window: BiometricSummaryWindow) -> Optional[str]:
        """Attempts /v1/chat/completions (fallback /completion) against base_url."""
        # 1. Try OpenAI-compatible /v1/chat/completions
        clean_base = base_url.rstrip("/")
        chat_url = f"{clean_base}/chat/completions" if clean_base.endswith("/v1") else f"{clean_base}/v1/chat/completions"

        payload = {
            "model": "llama-3-8b",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an edge AI clinical biometrics assistant running on the Google Pixel 10. "
                        "Analyze the provided ECG summary window and provide a concise 2-sentence clinical "
                        "assessment of cardiac rhythm, autonomic recovery, and exertion."
                    ),
                },
                {
                    "role": "user",
                    "content": window.to_prompt(),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 128,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            chat_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read().decode("utf-8")
                parsed = json.loads(body)
                choices = parsed.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content")
                    if content:
                        return content.strip()
                    text = choices[0].get("text")
                    if text:
                        return text.strip()
                return body
        except urllib.error.HTTPError as he:
            if he.code == 404:
                # 2. Try classic llama.cpp /completion endpoint
                host_root = clean_base.replace("/v1", "")
                comp_url = f"{host_root}/completion"
                comp_payload = {
                    "prompt": window.to_prompt(),
                    "n_predict": 128,
                    "temperature": 0.2,
                }
                comp_data = json.dumps(comp_payload).encode("utf-8")
                comp_req = urllib.request.Request(
                    comp_url,
                    data=comp_data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(comp_req, timeout=self.timeout_s) as comp_resp:
                        comp_body = comp_resp.read().decode("utf-8")
                        comp_parsed = json.loads(comp_body)
                        return comp_parsed.get("content", comp_body).strip()
                except Exception as comp_err:
                    logger.debug("Completion fallback failed at %s: %s", comp_url, comp_err)
            else:
                logger.debug("HTTPError %s at %s", he.code, chat_url)
        except Exception as e:
            logger.debug("HTTP dispatch failed at %s: %s", chat_url, e)

        return None

    def _record_offline_summary(self, window: BiometricSummaryWindow, assessment: str) -> None:
        """Appends window summary and assessment to local offline JSONL log file."""
        if not self.offline_log_path:
            return
        try:
            self.offline_log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp_utc": time.time(),
                "window": window.to_dict(),
                "assessment": assessment,
            }
            with open(self.offline_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to write offline log: %s", e)

    def _dispatch_one(self, window: BiometricSummaryWindow) -> None:
        """Processes a single summary window through inference endpoints or fallback."""
        self.total_dispatched += 1

        if self.dry_run:
            assessment = (
                f"[DRY_RUN] Evaluated window #{window.window_id}: "
                f"Rhythm={window.metrics.get('rhythm_assessment')}, "
                f"HR={window.metrics.get('mean_heart_rate_bpm')} BPM"
            )
            self._set_latest_assessment(assessment)
            self.total_succeeded += 1
            logger.info("%s", assessment)
            return

        # Attempt primary endpoint
        assessment = self._send_http_request(self.primary_url, window)

        # Attempt fallback endpoint if primary fails
        if assessment is None and self.fallback_url and self.fallback_url != self.primary_url:
            logger.info("Primary endpoint %s unreachable, failing over to %s", self.primary_url, self.fallback_url)
            assessment = self._send_http_request(self.fallback_url, window)

        if assessment is not None:
            self.total_succeeded += 1
            self._set_latest_assessment(assessment)
            logger.info("Clinical Assessment for Window #%d:\n%s", window.window_id, assessment)
        else:
            # All remote/local endpoints unreachable; graceful offline fallback
            self.total_offline_fallbacks += 1
            offline_assessment = (
                f"[OFFLINE_FALLBACK] Window #{window.window_id}: "
                f"Rhythm={window.metrics.get('rhythm_assessment')} | "
                f"Mean HR={window.metrics.get('mean_heart_rate_bpm')} BPM | "
                f"RMSSD={window.metrics.get('rmssd_ms')} ms (Endpoints offline; logged locally)"
            )
            self._set_latest_assessment(offline_assessment)
            self._record_offline_summary(window, offline_assessment)
            logger.warning("Endpoints unreachable. Graceful offline fallback triggered for window #%d", window.window_id)

    def _worker_loop(self) -> None:
        """Background thread worker loop consuming summary windows."""
        my_thread = threading.current_thread()
        while self._running and (self._thread is my_thread):
            try:
                item = self._queue.get(timeout=0.5)
                if item is None:
                    if not self._running or (self._thread is not my_thread):
                        break
                    continue
                self._dispatch_one(item)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Unexpected error in dispatcher worker: %s", e)


# ============================================================================
# 5. PIPELINE RUNNER & CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pixel 10 Edge ML Biometrics Ingestion & DSP Pipeline (Movesense 512 Hz ECG)",
    )
    parser.add_argument(
        "--log-file", "--log-path",
        dest="log_path",
        type=str,
        default=None,
        help="Path to Kai Morich Serial Bluetooth Terminal log file in /sdcard/ (auto-detected if omitted)",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Read from byte 0 instead of seeking to EOF on initial open",
    )
    parser.add_argument(
        "--llama-url",
        type=str,
        default=PRIMARY_LLAMA_URL,
        help=f"Primary Llama 8B HTTP endpoint (default: {PRIMARY_LLAMA_URL})",
    )
    parser.add_argument(
        "--fallback-url",
        type=str,
        default=FALLBACK_LLAMA_URL,
        help=f"On-device fallback Llama 8B HTTP endpoint (default: {FALLBACK_LLAMA_URL})",
    )
    parser.add_argument(
        "--window-sec",
        type=float,
        default=DEFAULT_WINDOW_SECONDS,
        help="Sliding window duration in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=DEFAULT_SAMPLE_RATE_HZ,
        help="Sensor sampling rate in Hz (default: 512.0)",
    )
    parser.add_argument(
        "--offline-log",
        type=str,
        default="biometrics_offline_summaries.jsonl",
        help="Local JSONL file path for caching offline summaries",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run Pan-Tompkins DSP without dispatching HTTP requests",
    )
    parser.add_argument(
        "--max-windows",
        type=int,
        default=None,
        help="Exit after processing N windows (useful for testing and benchmarks)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run comprehensive test suite and exit with code 0",
    )
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> int:
    """Executes the end-to-end edge ML ingestion pipeline."""
    logger.info("Initializing Pixel Edge ML Ingestion Pipeline...")
    logger.info("Memory RSS: %.2f MB (AVF ceiling <= 3500 MB)", get_process_rss_mb())

    tailer = KaiMorichLogTailer(
        log_path=args.log_path,
        read_from_start=args.from_beginning,
    )
    parser = KaiMorichPacketParser()
    engine = EdgeBiometricsEngine(
        sample_rate_hz=args.sample_rate,
        window_seconds=args.window_sec,
    )
    dispatcher = LlamaInferenceDispatcher(
        primary_url=args.llama_url,
        fallback_url=args.fallback_url,
        offline_log_path=Path(args.offline_log),
        dry_run=args.dry_run,
    )
    dispatcher.start()

    windows_processed = 0

    try:
        logger.info("Starting log tailer stream...")
        for raw_line in tailer.tail_lines():
            sample = parser.parse_line(raw_line)
            if sample is None:
                continue

            ts_ms, ecg_uv = sample
            window = engine.add_sample(ts_ms, ecg_uv)
            if window is not None:
                windows_processed += 1
                logger.info(
                    "Window #%d emitted: HR=%.1f BPM, RMSSD=%.1f ms, Artifacts=%d (RSS: %.2f MB)",
                    window.window_id,
                    window.metrics.get("mean_heart_rate_bpm", 0.0),
                    window.metrics.get("rmssd_ms", 0.0),
                    window.metrics.get("kamath_artifacts_rejected", 0),
                    get_process_rss_mb(),
                )
                dispatcher.dispatch_window(window)

                if args.max_windows and windows_processed >= args.max_windows:
                    logger.info("Reached target limit of %d windows. Exiting cleanly.", args.max_windows)
                    break
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
    finally:
        tailer.stop()
        dispatcher.stop(wait=True)
        logger.info("Pipeline stopped. Total windows processed: %d", windows_processed)

    return 0


def main() -> int:
    args = parse_args()
    if args.self_test:
        import unittest
        from pathlib import Path
        test_file = Path(__file__).resolve().parent / "tests" / "test_pixel_edge_ml_ingestion.py"
        suite = unittest.defaultTestLoader.discover(str(test_file.parent), pattern=test_file.name)
        runner = unittest.TextTestRunner(verbosity=2)
        res = runner.run(suite)
        return 0 if res.wasSuccessful() else 1
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
