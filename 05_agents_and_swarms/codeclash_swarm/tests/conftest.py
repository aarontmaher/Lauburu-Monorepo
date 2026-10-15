"""
PyTest Configuration & Fixtures for CodeClash Swarm & Sovereign Screen Lens E2E Suite.
Zero-mock compliance (Rule #0) and sub-3ms storage invariant verification (Rule 6.3).
"""
import os
import sys
import json
import sqlite3
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Generator, List

import pytest

# Ensure monorepo and codeclash_swarm directories are on sys.path
CODECLASH_ROOT = Path(__file__).resolve().parent.parent
MONOREPO_ROOT = Path(__file__).resolve().parents[3]

if str(CODECLASH_ROOT) not in sys.path:
    sys.path.insert(0, str(CODECLASH_ROOT))
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))

from models.schemas import (
    LanguageType,
    SymbolScope,
    SymbolRecord,
    CFGEdge,
    BasicBlock,
    CFGResult,
    ASTAnalysisReport,
    DecompilationResult,
    AdversarialTestResult,
)


# ============================================================================
# Screen Lens SQLite Schema Fixture
# ============================================================================

SCREEN_LENS_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    unix_ts_ms INTEGER NOT NULL,
    display_id INTEGER NOT NULL DEFAULT 0,
    screen_width INTEGER NOT NULL,
    screen_height INTEGER NOT NULL,
    active_app_name TEXT,
    active_bundle_id TEXT,
    active_window_title TEXT,
    active_pid INTEGER,
    raw_text_summary TEXT NOT NULL,
    ocr_confidence_avg REAL NOT NULL,
    ocr_mode TEXT NOT NULL,
    capture_duration_ms REAL NOT NULL,
    ocr_duration_ms REAL NOT NULL,
    change_hash TEXT
);

CREATE TABLE IF NOT EXISTS ocr_text_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id INTEGER NOT NULL,
    block_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    confidence REAL NOT NULL,
    bbox_x REAL NOT NULL,
    bbox_y REAL NOT NULL,
    bbox_w REAL NOT NULL,
    bbox_h REAL NOT NULL,
    pixel_x INTEGER NOT NULL,
    pixel_y INTEGER NOT NULL,
    pixel_w INTEGER NOT NULL,
    pixel_h INTEGER NOT NULL,
    FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(
    raw_text_summary,
    active_app_name,
    active_window_title,
    content='captures',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS captures_ai AFTER INSERT ON captures BEGIN
    INSERT INTO captures_fts(rowid, raw_text_summary, active_app_name, active_window_title)
    VALUES (new.id, new.raw_text_summary, new.active_app_name, new.active_window_title);
END;

CREATE TRIGGER IF NOT EXISTS captures_ad AFTER DELETE ON captures BEGIN
    INSERT INTO captures_fts(captures_fts, rowid, raw_text_summary, active_app_name, active_window_title)
    VALUES ('delete', old.id, old.raw_text_summary, old.active_app_name, old.active_window_title);
END;

CREATE INDEX IF NOT EXISTS idx_captures_unix_ts ON captures(unix_ts_ms);
CREATE INDEX IF NOT EXISTS idx_captures_app ON captures(active_app_name);
CREATE INDEX IF NOT EXISTS idx_ocr_blocks_capture_id ON ocr_text_blocks(capture_id);
"""


@pytest.fixture
def temp_sqlite_db() -> Generator[str, None, None]:
    """Provides a temporary SQLite database initialized with Screen Lens schema."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.executescript(SCREEN_LENS_SCHEMA_SQL)
    conn.commit()
    conn.close()

    yield db_path

    if os.path.exists(db_path):
        os.remove(db_path)
    wal_path = f"{db_path}-wal"
    shm_path = f"{db_path}-shm"
    if os.path.exists(wal_path):
        os.remove(wal_path)
    if os.path.exists(shm_path):
        os.remove(shm_path)


# ============================================================================
# Polyglot Source Code Fixtures
# ============================================================================

@pytest.fixture
def python_source_clean() -> str:
    return """def sliding_window_max(nums: list, k: int) -> list:
    '''Calculates the maximum in each sliding window of size k.'''
    if not nums or k <= 0:
        return []
    if k == 1:
        return list(nums)
    
    result = []
    from collections import deque
    dq = deque()
    
    for i, n in enumerate(nums):
        while dq and dq[0] < i - k + 1:
            dq.popleft()
        while dq and nums[dq[-1]] < n:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            result.append(nums[dq[0]])
            
    return result
"""


@pytest.fixture
def python_source_buggy() -> str:
    return """def sliding_window_max(nums: list, k: int) -> list:
    '''Corrupted implementation with off-by-one error injected.'''
    if not nums or k <= 0:
        return []
    result = []
    for i in range(len(nums) - k):  # Bug: misses last window (len - k + 1)
        window = nums[i:i + k]
        result.append(max(window))
    return result
"""


@pytest.fixture
def python_source_obfuscated() -> str:
    return """def _0x4a1b(_0x91ef, _0x12dc):
    if False:
        _0xdead = 9999 + 1
        return _0xdead
    _0x9900 = 10 + 20 * 2
    _0xres = []
    for _0xidx in range(len(_0x91ef)):
        if _0xidx % 2 == 0:
            _0xres.append(_0x91ef[_0xidx] + _0x12dc)
        else:
            _0xres.append(_0x91ef[_0xidx] * 2)
    return _0xres
"""


@pytest.fixture
def rust_mir_sample() -> str:
    return """
// MIR for `sliding_window_max`
fn sliding_window_max(_1: &[i32], _2: usize) -> Vec<i32> {
    debug nums => _1;
    debug k => _2;
    let mut _0: std::vec::Vec<i32>;
    let mut _3: bool;
    let mut _4: usize;

    bb0: {
        StorageLive(_3);
        _4 = Len((*_1));
        _3 = Eq(move _4, const 0_usize);
        switchInt(move _3) -> [0: bb2, otherwise: bb1];
    }

    bb1: {
        StorageDead(_3);
        _0 = Vec::<i32>::new() -> [return: bb4, unwind: bb5];
    }

    bb2: {
        StorageDead(_3);
        _0 = Vec::<i32>::with_capacity(const 10_usize) -> [return: bb3, unwind: bb5];
    }

    bb3: {
        return;
    }

    bb4: {
        return;
    }

    bb5 (cleanup): {
        resume;
    }
}
"""


@pytest.fixture
def go_source_sample() -> str:
    return """package main

import (
	"errors"
	"fmt"
)

type WindowProcessor struct {
	Capacity int
	Name     string
}

func (p *WindowProcessor) Process(nums []int, k int) ([]int, error) {
	if len(nums) == 0 || k <= 0 {
		return nil, errors.New("invalid arguments")
	}
	res := make([]int, 0, len(nums)-k+1)
	for i := 0; i <= len(nums)-k; i++ {
		maxVal := nums[i]
		for j := 1; j < k; j++ {
			if nums[i+j] > maxVal {
				maxVal = nums[i+j]
			}
		}
		res = append(res, maxVal)
	}
	return res, nil
}

func main() {
	proc := &WindowProcessor{Capacity: 100, Name: "MainProcessor"}
	out, err := proc.Process([]int{1, 3, -1, -3, 5, 3, 6, 7}, 3)
	if err == nil {
		fmt.Println(out)
	}
}
"""


@pytest.fixture
def typescript_source_sample() -> str:
    return """export interface WindowConfig {
    k: number;
    decayFactor: number;
    logEvents?: boolean;
}

export class SlidingWindowAnalyzer {
    private config: WindowConfig;

    constructor(config: WindowConfig) {
        this.config = config;
    }

    public async analyze(values: number[]): Promise<number[]> {
        if (!values || values.length === 0 || this.config.k <= 0) {
            return [];
        }
        const results: number[] = [];
        for (let i = 0; i <= values.length - this.config.k; i++) {
            let maxVal = values[i];
            for (let j = 1; j < this.config.k; j++) {
                if (values[i + j] > maxVal) {
                    maxVal = values[i + j];
                }
            }
            results.push(maxVal);
        }
        return results;
    }
}
"""


# ============================================================================
# LoRA Datasets & Obsidian Leaderboard Fixtures
# ============================================================================

@pytest.fixture
def temp_lora_dataset() -> Generator[str, None, None]:
    """Provides a temporary JSONL dataset path."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        file_path = f.name
    yield file_path
    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.fixture
def temp_obsidian_vault() -> Generator[Path, None, None]:
    """Provides a temporary Obsidian vault directory structure."""
    temp_dir = Path(tempfile.mkdtemp(prefix="obsidian_vault_test_"))
    analytics_dir = temp_dir / "04_ANALYTICS"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# ============================================================================
# Arena Duel Task Specs
# ============================================================================

@pytest.fixture
def algorithm_task_spec() -> Dict[str, Any]:
    return {
        "task_id": "swe_algo_001",
        "task_name": "Sliding Window Maximum Subarray",
        "language": "python",
        "base_code": """def sliding_window_max(nums: list, k: int) -> list:
    if not nums or k <= 0:
        return []
    if k == 1:
        return list(nums)
    res = []
    for i in range(len(nums) - k + 1):
        res.append(max(nums[i:i + k]))
    return res
""",
        "test_code": """import pytest

def test_sliding_window_basic():
    from candidate import sliding_window_max
    assert sliding_window_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]

def test_sliding_window_k1():
    from candidate import sliding_window_max
    assert sliding_window_max([4, -2], 1) == [4, -2]

def test_sliding_window_empty():
    from candidate import sliding_window_max
    assert sliding_window_max([], 3) == []

def test_sliding_window_all_negative():
    from candidate import sliding_window_max
    assert sliding_window_max([-7, -8, -7, 5, 7, 1, 6, 0], 4) == [5, 7, 7, 7, 7]
""",
        "difficulty": "medium",
        "timeout_seconds": 5.0,
    }


@pytest.fixture
def dsp_task_spec() -> Dict[str, Any]:
    return {
        "task_id": "swe_dsp_002",
        "task_name": "Pan-Tompkins QRS Peak Detection",
        "language": "python",
        "base_code": """def detect_qrs_peaks(signal: list, threshold: float = 0.5) -> list:
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1] and signal[i] >= threshold:
            peaks.append(i)
    return peaks
""",
        "test_code": """def test_peaks_basic():
    from candidate import detect_qrs_peaks
    sig = [0.1, 0.2, 0.9, 0.3, 0.1, 0.05, 0.85, 0.2]
    assert detect_qrs_peaks(sig, 0.5) == [2, 6]

def test_peaks_flat():
    from candidate import detect_qrs_peaks
    assert detect_qrs_peaks([0.1, 0.1, 0.1], 0.5) == []

def test_peaks_empty():
    from candidate import detect_qrs_peaks
    assert detect_qrs_peaks([], 0.5) == []
""",
        "difficulty": "hard",
        "timeout_seconds": 5.0,
    }


@pytest.fixture
def concurrency_task_spec() -> Dict[str, Any]:
    return {
        "task_id": "swe_conc_003",
        "task_name": "Thread-Safe Circular Ring Buffer",
        "language": "python",
        "base_code": """import threading

class CircularBuffer:
    def __init__(self, capacity: int):
        self.capacity = max(1, capacity)
        self.buffer = [None] * self.capacity
        self.head = 0
        self.tail = 0
        self.size = 0
        self.lock = threading.Lock()

    def push(self, item) -> bool:
        with self.lock:
            if self.size >= self.capacity:
                return False
            self.buffer[self.tail] = item
            self.tail = (self.tail + 1) % self.capacity
            self.size += 1
            return True

    def pop(self):
        with self.lock:
            if self.size == 0:
                return None
            item = self.buffer[self.head]
            self.buffer[self.head] = None
            self.head = (self.head + 1) % self.capacity
            self.size -= 1
            return item
""",
        "test_code": """def test_circular_buffer_fifo():
    from candidate import CircularBuffer
    cb = CircularBuffer(3)
    assert cb.push(10) is True
    assert cb.push(20) is True
    assert cb.push(30) is True
    assert cb.push(40) is False
    assert cb.pop() == 10
    assert cb.push(50) is True
    assert cb.pop() == 20
    assert cb.pop() == 30
    assert cb.pop() == 50
    assert cb.pop() is None
""",
        "difficulty": "medium",
        "timeout_seconds": 5.0,
    }
