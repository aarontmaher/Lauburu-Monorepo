#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
E2E Storage & ELO Verification Helpers (Zero-Mock Invariant Support)
================================================================================
Subsystem: tests/e2e_storage_elo/e2e_storage_elo_helpers.py
Authoritative Reference: PROJECT.md & ORIGINAL_REQUEST.md (§R1, §R2, §R3)
"""

import os
import sys
import ctypes
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DYLIB_PATH = REPO_ROOT / "01_apps/screen_lens/c_core/liblauburu_storage.dylib"
BENCH_BIN_PATH = REPO_ROOT / "01_apps/screen_lens/c_core/lauburu_storage_bench"

PRIMARY_CONTEXT_MAP = REPO_ROOT / "07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md"
MIRROR_CONTEXT_MAP = REPO_ROOT / "obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md"
CANONICAL_CONTEXT_MAP_SHA256 = "80e96726403861ba55f8d9029442fb44e581bfb2da345adc0a27fce024ef0b02"
CANONICAL_CONTEXT_MAP_SIZE = 5548

ROUTER_DAEMON_SRC = REPO_ROOT / "00_core_infrastructure/router_ai_daemon/src"
if str(ROUTER_DAEMON_SRC) not in sys.path:
    sys.path.insert(0, str(ROUTER_DAEMON_SRC))

# Import ELO engine components
try:
    from elo.elo_engine import (
        EloEngine,
        MIN_ELO_RATING,
        MAX_ELO_RATING,
        calculate_wilson_confidence_interval,
        CategoryScorecard,
        ProjectEloScorecard,
        evaluate_project_scorecard,
        WilsonConfidenceInterval,
        CodeOffMatch,
        ResourceUsage,
    )
except ImportError:
    from router_ai_daemon.src.elo.elo_engine import (  # type: ignore
        EloEngine,
        MIN_ELO_RATING,
        MAX_ELO_RATING,
        calculate_wilson_confidence_interval,
        CategoryScorecard,
        ProjectEloScorecard,
        evaluate_project_scorecard,
        WilsonConfidenceInterval,
        CodeOffMatch,
        ResourceUsage,
    )


# --- CTYPES C11 STRUCTURES & BINDINGS ---

class CStorageNode(ctypes.Structure):
    _fields_ = [
        ("node_id", ctypes.c_char * 32),
        ("network_role", ctypes.c_char * 64),
        ("available_capacity_bytes", ctypes.c_uint64),
        ("is_active", ctypes.c_bool),
    ]


class CStorageChunkMeta(ctypes.Structure):
    _fields_ = [
        ("chunk_index", ctypes.c_uint32),
        ("hash_token", ctypes.c_uint32),
        ("assigned_node_id", ctypes.c_char * 32),
        ("data_length", ctypes.c_uint32),
        ("fletcher32_checksum", ctypes.c_uint32),
    ]


class CStoragePoolReport(ctypes.Structure):
    _fields_ = [
        ("total_payload_bytes", ctypes.c_size_t),
        ("chunk_count", ctypes.c_size_t),
        ("active_nodes_count", ctypes.c_size_t),
        ("slice_and_disperse_latency_us", ctypes.c_double),
        ("reassemble_latency_us", ctypes.c_double),
        ("bitrot_free", ctypes.c_bool),
        ("e2e_sha256_match", ctypes.c_bool),
    ]


class C11StorageEngine:
    """Zero-mock interface directly binding to compiled native liblauburu_storage.dylib."""

    CANONICAL_7_LAYERS = [
        ("L1_Mac_Node", "Primary Host M4 Pro", 24 * 1024 * 1024 * 1024),
        ("L2_MacBook_Pro", "40Gbps TB4 DMA Model Vault", 285 * 1024 * 1024 * 1024),
        ("L3_Linux_Head_Node", "Gateway Ingress & Compute Hub", 400 * 1024 * 1024 * 1024),
        ("L4_Linux_Tablet", "Mobile Linux Compute & Touch DSP", 100 * 1024 * 1024 * 1024),
        ("L5_MacBook_Air", "Secondary High-Speed Metal Worker", 100 * 1024 * 1024 * 1024),
        ("L6_Pixel_10_Pro_XL", "8K Vision Stream & Edge TPU", 64 * 1024 * 1024 * 1024),
        ("L7_Samsung_S20", "Dedicated Automated UI Tester", 64 * 1024 * 1024 * 1024),
    ]

    def __init__(self, dylib_path: Optional[Path] = None):
        target_path = dylib_path or DYLIB_PATH
        if not target_path.exists():
            raise FileNotFoundError(f"Native shared library not found: {target_path}")

        self.lib = ctypes.CDLL(str(target_path))

        # Setup function signatures
        self.lib.storage_pool_init_ring.argtypes = []
        self.lib.storage_pool_init_ring.restype = None

        self.lib.storage_pool_add_node.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint64
        ]
        self.lib.storage_pool_add_node.restype = ctypes.c_bool

        self.lib.storage_pool_sort_ring.argtypes = []
        self.lib.storage_pool_sort_ring.restype = None

        self.lib.storage_pool_find_node.argtypes = [ctypes.c_uint32]
        self.lib.storage_pool_find_node.restype = ctypes.c_int

        self.lib.compute_fletcher32.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t
        ]
        self.lib.compute_fletcher32.restype = ctypes.c_uint32

        self.lib.storage_pool_get_node.argtypes = [ctypes.c_size_t]
        self.lib.storage_pool_get_node.restype = ctypes.POINTER(CStorageNode)

        self.lib.storage_pool_get_node_count.argtypes = []
        self.lib.storage_pool_get_node_count.restype = ctypes.c_size_t

        self.lib.storage_pool_get_ring_size.argtypes = []
        self.lib.storage_pool_get_ring_size.restype = ctypes.c_size_t

        self.lib.storage_pool_disperse_payload.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
            ctypes.POINTER(CStorageChunkMeta),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)),
        ]
        self.lib.storage_pool_disperse_payload.restype = CStoragePoolReport

        self.lib.storage_pool_reassemble_payload.argtypes = [
            ctypes.POINTER(CStorageChunkMeta),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
        ]
        self.lib.storage_pool_reassemble_payload.restype = ctypes.c_bool

    def init_and_register_canonical_mesh(self) -> None:
        """Initialize consistent hash ring and register all 7 canonical mesh layers."""
        self.lib.storage_pool_init_ring()
        for node_id, role, cap in self.CANONICAL_7_LAYERS:
            res = self.lib.storage_pool_add_node(node_id.encode("utf-8"), role.encode("utf-8"), cap)
            if not res:
                raise RuntimeError(f"Failed to add node {node_id}")
        self.lib.storage_pool_sort_ring()

    def get_node_count(self) -> int:
        return int(self.lib.storage_pool_get_node_count())

    def get_ring_size(self) -> int:
        return int(self.lib.storage_pool_get_ring_size())

    def get_node_info(self, idx: int) -> Dict[str, Any]:
        node_ptr = self.lib.storage_pool_get_node(idx)
        if not node_ptr:
            raise IndexError(f"Invalid node index {idx}")
        n = node_ptr.contents
        return {
            "node_id": n.node_id.decode("utf-8"),
            "role": n.network_role.decode("utf-8"),
            "capacity_bytes": n.available_capacity_bytes,
            "is_active": n.is_active,
        }

    def compute_fletcher32(self, data: bytes) -> int:
        buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        return int(self.lib.compute_fletcher32(buf, len(data)))

    def find_node(self, token: int) -> int:
        return int(self.lib.storage_pool_find_node(ctypes.c_uint32(token)))

    def disperse_and_reassemble(
        self,
        payload: bytes,
        max_chunks: int = 64,
        corrupt_chunk_idx: Optional[int] = None,
        corrupt_byte_offset: int = 0,
        corrupt_xor_mask: int = 0x01,
    ) -> Tuple[CStoragePoolReport, List[Dict[str, Any]], bool, bytes]:
        """Disperses payload into chunks and optionally corrupts a block before reassembly."""
        payload_len = len(payload)
        payload_buf = (ctypes.c_uint8 * payload_len).from_buffer_copy(payload)

        metas = (CStorageChunkMeta * max_chunks)()
        chunk_ptrs = (ctypes.POINTER(ctypes.c_uint8) * max_chunks)()

        rep = self.lib.storage_pool_disperse_payload(
            payload_buf, payload_len, metas, max_chunks, chunk_ptrs
        )

        chunk_count = rep.chunk_count
        chunk_info = []
        for i in range(chunk_count):
            m = metas[i]
            chunk_info.append({
                "chunk_index": m.chunk_index,
                "token": m.hash_token,
                "node": m.assigned_node_id.decode("utf-8"),
                "length": m.data_length,
                "fletcher32": m.fletcher32_checksum,
            })

        # Inject corruption if requested
        if corrupt_chunk_idx is not None and 0 <= corrupt_chunk_idx < chunk_count:
            ptr = chunk_ptrs[corrupt_chunk_idx]
            original_val = ptr[corrupt_byte_offset]
            ptr[corrupt_byte_offset] = original_val ^ corrupt_xor_mask

        # Reassemble
        out_buf = (ctypes.c_uint8 * payload_len)()
        ok = self.lib.storage_pool_reassemble_payload(
            metas, chunk_ptrs, chunk_count, out_buf, payload_len
        )

        reassembled_bytes = bytes(out_buf)

        # Free allocated chunk buffers
        libc = ctypes.CDLL(None)
        for i in range(chunk_count):
            if chunk_ptrs[i]:
                libc.free(chunk_ptrs[i])

        return rep, chunk_info, ok, reassembled_bytes

