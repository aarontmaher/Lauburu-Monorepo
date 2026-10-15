# -*- coding: utf-8 -*-
"""
Zero-Mock Helper Utilities for Sovereign Lens Bootstrapper E2E Test Suite.
Enforces Rule 0, Rule 1, Rule 3, and Rule 8 without simulated data.
"""

import os
import sys
import json
import math
import socket
import struct
import ctypes
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def get_project_root() -> Path:
    """Finds monorepo root by locating 00_core_infrastructure or .git."""
    curr = Path(__file__).resolve().parent
    for _ in range(6):
        if (curr / "00_core_infrastructure").exists() and (curr / "obsidian_vault").exists():
            return curr
        curr = curr.parent
    return Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")


PROJECT_ROOT = get_project_root()
SUITE_ROOT = PROJECT_ROOT / "tests" / "e2e" / "lens_bootstrapper"
BOOTSTRAPPER_DIR = PROJECT_ROOT / "00_core_infrastructure" / "lens_bootstrapper"


def send_socket_command(sock_path: str, command: str, timeout_sec: float = 2.0) -> Tuple[bool, str]:
    """
    Sends a line-delimited ASCII command to a Unix domain socket and reads response.
    Returns (success, response_string).
    """
    expanded_path = os.path.expanduser(sock_path)
    if not os.path.exists(expanded_path):
        return False, f"Socket file does not exist: {expanded_path}"

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout_sec)
    try:
        client.connect(expanded_path)
        if not command.endswith("\n"):
            command += "\n"
        client.sendall(command.encode("utf-8"))
        
        # Read response line
        response_bytes = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_bytes += chunk
            if b"\n" in response_bytes:
                break
        return True, response_bytes.decode("utf-8").strip()
    except Exception as e:
        return False, f"Socket error: {str(e)}"
    finally:
        client.close()


def query_darwin_mach_memory() -> Dict[str, int]:
    """
    Directly queries Darwin Mach kernel VM statistics via libc host_statistics64.
    Zero process forks, genuine Mach kernel syscall.
    """
    if sys.platform != "darwin":
        return {"error": "Not Darwin platform"}

    try:
        libc = ctypes.CDLL("/usr/lib/libc.dylib")
        page_size = ctypes.c_ulong(0)
        mach_host_self = libc.mach_host_self()
        libc.host_page_size(mach_host_self, ctypes.byref(page_size))
        ps = page_size.value if page_size.value > 0 else 16384

        class VmStatistics64(ctypes.Structure):
            _fields_ = [
                ("free_count", ctypes.c_uint32),
                ("active_count", ctypes.c_uint32),
                ("inactive_count", ctypes.c_uint32),
                ("wire_count", ctypes.c_uint32),
                ("zero_fill_count", ctypes.c_uint64),
                ("reactivations", ctypes.c_uint64),
                ("pageins", ctypes.c_uint64),
                ("pageouts", ctypes.c_uint64),
                ("faults", ctypes.c_uint64),
                ("cow_faults", ctypes.c_uint64),
                ("lookups", ctypes.c_uint64),
                ("hits", ctypes.c_uint64),
                ("purges", ctypes.c_uint64),
                ("purgeable_count", ctypes.c_uint32),
                ("speculative_count", ctypes.c_uint32),
                ("decompressions", ctypes.c_uint64),
                ("compressions", ctypes.c_uint64),
                ("swapins", ctypes.c_uint64),
                ("swapouts", ctypes.c_uint64),
                ("compressor_page_count", ctypes.c_uint32),
                ("throttled_count", ctypes.c_uint32),
                ("external_page_count", ctypes.c_uint32),
                ("internal_page_count", ctypes.c_uint32),
                ("total_uncompressed_pages_in_compressor", ctypes.c_uint64),
            ]

        vm_stat = VmStatistics64()
        count = ctypes.c_uint32(ctypes.sizeof(vm_stat) // 4)
        
        ret = libc.host_statistics64(
            mach_host_self,
            4,  # HOST_VM_INFO64
            ctypes.byref(vm_stat),
            ctypes.byref(count)
        )
        if ret == 0:
            free_bytes = (vm_stat.free_count + vm_stat.speculative_count) * ps
            avail_bytes = (vm_stat.free_count + vm_stat.speculative_count + vm_stat.inactive_count + vm_stat.purgeable_count) * ps
            wired_bytes = vm_stat.wire_count * ps
            comp_bytes = vm_stat.compressor_page_count * ps
            return {
                "page_size": ps,
                "free_bytes": free_bytes,
                "avail_bytes": avail_bytes,
                "wired_bytes": wired_bytes,
                "compressor_bytes": comp_bytes,
            }
    except Exception as e:
        return {"error": str(e)}

    return {"error": "Syscall failed"}


def compute_dense_ngram_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Deterministic 128-dimensional dense unit vector embedding via character/word n-gram hashing.
    Zero external libraries, 100% offline, zero prompt leakage (Rule 8).
    """
    if not text:
        return [0.0] * dim

    vec = [0.0] * dim
    clean_text = text.lower().strip()
    words = clean_text.split()
    
    # 1. Unigrams and bigrams
    for i, w in enumerate(words):
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * 1.5

        if i + 1 < len(words):
            bg = f"{w}_{words[i+1]}"
            h_bg = int(hashlib.md5(bg.encode("utf-8")).hexdigest(), 16)
            idx_bg = h_bg % dim
            sign_bg = 1.0 if ((h_bg >> 8) & 1) == 0 else -1.0
            vec[idx_bg] += sign_bg * 2.0

    # 2. Character trigrams
    for i in range(len(clean_text) - 2):
        tri = clean_text[i:i+3]
        h_tri = int(hashlib.sha256(tri.encode("utf-8")).hexdigest(), 16)
        idx_tri = h_tri % dim
        sign_tri = 1.0 if ((h_tri >> 4) & 1) == 0 else -1.0
        vec[idx_tri] += sign_tri * 0.5

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-12:
        return [0.0] * dim
    return [round(x / norm, 6) for x in vec]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two unit vectors."""
    if len(v1) != len(v2) or not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 < 1e-12 or norm2 < 1e-12:
        return 0.0
    return dot / (norm1 * norm2)
