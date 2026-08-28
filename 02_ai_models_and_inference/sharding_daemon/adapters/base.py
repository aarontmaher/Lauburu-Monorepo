#!/usr/bin/env python3
"""
02_ai_models_and_inference/sharding_daemon/adapters/base.py
===========================================================
Canonical Base Interfaces & Abstract Classes for Multi-Backend AI Sharding Adapters.
-----------------------------------------------------------------------------------
Defines standard tensor payloads, shard specifications, adapter status models,
and the abstract BackendAdapter contract required by Petals, llama.cpp, Exo,
and Accelerate execution engines.

Interface Contract:
- class BackendAdapter(ABC):
    - load_model_shard(model_name: str, layer_range: Tuple[int, int], device: str) -> bool
    - forward_tensor_step(hidden_states: Any, layer_idx: int) -> Any
    - forward_tensor_range(hidden_states: Any, start_layer: int, end_layer: int) -> Any
    - get_memory_usage_mb() -> float
    - is_healthy() -> bool
    - unload_model_shard() -> bool
    - get_status() -> AdapterStatus
    - get_backend_type() -> str
    - set_network_awareness(unal: Any) -> None
"""

from __future__ import annotations

import abc
import io
import time
import struct
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger("ShardingAdapters.Base")


class TensorDtype(str, Enum):
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8 = "int8"
    NF4 = "nf4"
    INT4 = "int4"


class CompressionMode(str, Enum):
    NONE = "NONE"
    FP16 = "FP16"
    INT8 = "INT8"
    NF4 = "NF4"


# Precomputed NF4 (NormalFloat4) 16-level quantization grid for Gaussian activations
NF4_QUANT_TABLE = np.array([
    -1.0, -0.6961928009986877, -0.5250730514526367, -0.39491748809814453,
    -0.28444138169288635, -0.18477343022823334, -0.09105003625154495, 0.0,
    0.07958029955625534, 0.16093020141124725, 0.24611230194568634, 0.33791524171829224,
    0.44070982933044434, 0.5626170039176941, 0.7229568362236023, 1.0
], dtype=np.float32)


@dataclass
class TensorPayload:
    """
    Standard serialized tensor representation across network hops and backend adapters.
    Supports genuine numpy/torch array storage, dynamic quantization, and zero-copy slicing.
    """
    data: np.ndarray
    shape: Tuple[int, ...] = field(default_factory=tuple)
    dtype: TensorDtype = TensorDtype.FLOAT32
    sequence_len: int = 1
    hidden_dim: int = 4096
    compression: CompressionMode = CompressionMode.NONE
    scale_factors: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.data, np.ndarray):
            self.data = np.asarray(self.data, dtype=np.float32)
        if not self.shape:
            self.shape = self.data.shape
        if len(self.shape) >= 2:
            self.sequence_len = self.shape[-2]
            self.hidden_dim = self.shape[-1]
        elif len(self.shape) == 1:
            self.sequence_len = 1
            self.hidden_dim = self.shape[0]

    @property
    def nbytes(self) -> int:
        base_bytes = self.data.nbytes
        if self.scale_factors is not None:
            base_bytes += self.scale_factors.nbytes
        return base_bytes

    def compress(self, target_mode: CompressionMode) -> TensorPayload:
        """
        Compresses tensor activations for low-bandwidth or high-latency network hops.
        Applies genuine numerical quantization (FP16, INT8 symmetric, or NF4 block-wise).
        """
        if target_mode == CompressionMode.NONE or self.compression == target_mode:
            return self

        float_data = self.data.astype(np.float32)

        if target_mode == CompressionMode.FP16:
            quant_data = float_data.astype(np.float16)
            return TensorPayload(
                data=quant_data,
                shape=self.shape,
                dtype=TensorDtype.FLOAT16,
                sequence_len=self.sequence_len,
                hidden_dim=self.hidden_dim,
                compression=CompressionMode.FP16,
                metadata={**self.metadata, "original_dtype": self.dtype.value}
            )

        elif target_mode == CompressionMode.INT8:
            # Symmetric INT8 quantization per token/row
            orig_shape = float_data.shape
            flat_2d = float_data.reshape(-1, orig_shape[-1])
            max_abs = np.max(np.abs(flat_2d), axis=-1, keepdims=True)
            scales = np.maximum(max_abs / 127.0, 1e-8).astype(np.float32)
            quant_2d = np.clip(np.round(flat_2d / scales), -128, 127).astype(np.int8)
            quant_data = quant_2d.reshape(orig_shape)
            return TensorPayload(
                data=quant_data,
                shape=self.shape,
                dtype=TensorDtype.INT8,
                sequence_len=self.sequence_len,
                hidden_dim=self.hidden_dim,
                compression=CompressionMode.INT8,
                scale_factors=scales,
                metadata={**self.metadata, "original_dtype": self.dtype.value}
            )

        elif target_mode == CompressionMode.NF4:
            # Block-wise NormalFloat4 Quantization (block size = 64)
            block_size = 64
            flat_1d = float_data.flatten()
            num_elements = flat_1d.size
            pad_len = (block_size - (num_elements % block_size)) % block_size
            if pad_len > 0:
                flat_1d = np.pad(flat_1d, (0, pad_len), mode="constant")

            blocks = flat_1d.reshape(-1, block_size)
            scales = np.maximum(np.max(np.abs(blocks), axis=1, keepdims=True), 1e-8).astype(np.float32)
            normalized_blocks = blocks / scales

            # Map to nearest NF4 index (0..15)
            # normalized_blocks: (num_blocks, 64, 1) - NF4_QUANT_TABLE: (16,)
            diffs = np.abs(normalized_blocks[:, :, np.newaxis] - NF4_QUANT_TABLE[np.newaxis, np.newaxis, :])
            indices = np.argmin(diffs, axis=-1).astype(np.uint8)  # values 0..15

            # Pack two 4-bit nibbles per byte
            even_nibbles = indices[:, 0::2]
            odd_nibbles = indices[:, 1::2]
            packed_bytes = (even_nibbles | (odd_nibbles << 4)).astype(np.uint8)

            return TensorPayload(
                data=packed_bytes,
                shape=self.shape,
                dtype=TensorDtype.NF4,
                sequence_len=self.sequence_len,
                hidden_dim=self.hidden_dim,
                compression=CompressionMode.NF4,
                scale_factors=scales,
                metadata={
                    **self.metadata,
                    "original_dtype": self.dtype.value,
                    "num_elements": num_elements,
                    "pad_len": pad_len,
                    "block_size": block_size
                }
            )

        return self

    def decompress(self) -> TensorPayload:
        """
        Decompresses quantized tensor back into full-precision float32 representation.
        """
        if self.compression == CompressionMode.NONE:
            return self

        if self.compression == CompressionMode.FP16:
            return TensorPayload(
                data=self.data.astype(np.float32),
                shape=self.shape,
                dtype=TensorDtype.FLOAT32,
                sequence_len=self.sequence_len,
                hidden_dim=self.hidden_dim,
                compression=CompressionMode.NONE,
                metadata=self.metadata
            )

        elif self.compression == CompressionMode.INT8:
            if self.scale_factors is None:
                return TensorPayload(
                    data=self.data.astype(np.float32),
                    shape=self.shape,
                    dtype=TensorDtype.FLOAT32,
                    sequence_len=self.sequence_len,
                    hidden_dim=self.hidden_dim,
                    compression=CompressionMode.NONE,
                    metadata=self.metadata
                )
            orig_shape = self.shape
            flat_2d = self.data.reshape(-1, orig_shape[-1]).astype(np.float32)
            recon_2d = flat_2d * self.scale_factors
            recon_data = recon_2d.reshape(orig_shape).astype(np.float32)
            return TensorPayload(
                data=recon_data,
                shape=self.shape,
                dtype=TensorDtype.FLOAT32,
                sequence_len=self.sequence_len,
                hidden_dim=self.hidden_dim,
                compression=CompressionMode.NONE,
                metadata=self.metadata
            )

        elif self.compression == CompressionMode.NF4:
            if self.scale_factors is None:
                return self
            num_elements = self.metadata.get("num_elements", self.data.size * 2)
            pad_len = self.metadata.get("pad_len", 0)
            block_size = self.metadata.get("block_size", 64)

            # Unpack nibbles
            packed = self.data
            even_nibbles = packed & 0x0F
            odd_nibbles = (packed >> 4) & 0x0F
            num_blocks = packed.shape[0]
            unpacked_indices = np.empty((num_blocks, block_size), dtype=np.int32)
            unpacked_indices[:, 0::2] = even_nibbles
            unpacked_indices[:, 1::2] = odd_nibbles

            # Map indices back to NF4 values
            dequant_blocks = NF4_QUANT_TABLE[unpacked_indices] * self.scale_factors
            flat_recon = dequant_blocks.flatten()
            if pad_len > 0:
                flat_recon = flat_recon[:num_elements]
            recon_data = flat_recon.reshape(self.shape).astype(np.float32)

            return TensorPayload(
                data=recon_data,
                shape=self.shape,
                dtype=TensorDtype.FLOAT32,
                sequence_len=self.sequence_len,
                hidden_dim=self.hidden_dim,
                compression=CompressionMode.NONE,
                metadata=self.metadata
            )

        return self

    def to_bytes(self) -> bytes:
        """Serializes TensorPayload into binary wire format for socket/RPC transit."""
        buf = io.BytesIO()
        shape_bytes = struct.pack(f"!I{len(self.shape)}I", len(self.shape), *self.shape)
        buf.write(shape_bytes)
        dtype_str = self.dtype.value.encode("utf-8")
        buf.write(struct.pack("!I", len(dtype_str)) + dtype_str)
        comp_str = self.compression.value.encode("utf-8")
        buf.write(struct.pack("!I", len(comp_str)) + comp_str)

        has_scales = 1 if self.scale_factors is not None else 0
        buf.write(struct.pack("!B", has_scales))
        if has_scales:
            scale_bytes = self.scale_factors.tobytes()
            buf.write(struct.pack(f"!II{len(self.scale_factors.shape)}I", len(scale_bytes), len(self.scale_factors.shape), *self.scale_factors.shape))
            buf.write(scale_bytes)

        raw_data = self.data.tobytes()
        buf.write(struct.pack("!I", len(raw_data)))
        buf.write(raw_data)
        return buf.getvalue()

    @classmethod
    def from_bytes(cls, b: bytes) -> TensorPayload:
        """Deserializes binary wire format into a TensorPayload."""
        buf = io.BytesIO(b)
        shape_len = struct.unpack("!I", buf.read(4))[0]
        shape = struct.unpack(f"!{shape_len}I", buf.read(4 * shape_len))

        dtype_len = struct.unpack("!I", buf.read(4))[0]
        dtype_str = buf.read(dtype_len).decode("utf-8")

        comp_len = struct.unpack("!I", buf.read(4))[0]
        comp_str = buf.read(comp_len).decode("utf-8")

        has_scales = struct.unpack("!B", buf.read(1))[0]
        scale_factors = None
        if has_scales == 1:
            scale_byte_len, scale_ndim = struct.unpack("!II", buf.read(8))
            scale_shape = struct.unpack(f"!{scale_ndim}I", buf.read(4 * scale_ndim))
            scale_raw = buf.read(scale_byte_len)
            scale_factors = np.frombuffer(scale_raw, dtype=np.float32).reshape(scale_shape)

        data_len = struct.unpack("!I", buf.read(4))[0]
        raw_data = buf.read(data_len)

        np_dtype = np.float32
        if dtype_str == "float16":
            np_dtype = np.float16
        elif dtype_str == "int8":
            np_dtype = np.int8
        elif dtype_str in ("nf4", "int4"):
            np_dtype = np.uint8

        data = np.frombuffer(raw_data, dtype=np_dtype)
        if comp_str != "NF4":
            data = data.reshape(shape)

        return cls(
            data=data,
            shape=shape,
            dtype=TensorDtype(dtype_str),
            compression=CompressionMode(comp_str),
            scale_factors=scale_factors
        )


@dataclass
class ShardSpec:
    """Specification of a model layer shard assigned to this node/adapter."""
    model_id: str
    start_layer: int
    end_layer: int
    total_layers: int
    device: str = "mps"
    dtype: str = "float32"
    memory_mb: float = 0.0
    quantization: str = "Q4_K_M"
    extra_params: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_layers(self) -> int:
        return max(0, self.end_layer - self.start_layer)


class AdapterStatus(BaseModel):
    """Real-time health, memory, and telemetry report from a backend adapter."""
    backend_type: str
    node_id: str
    is_loaded: bool = False
    model_id: str = ""
    start_layer: int = 0
    end_layer: int = 0
    total_layers: int = 0
    device: str = "cpu"
    allocated_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    memory_ceiling_mb: float = 0.0
    healthy: bool = True
    error_message: Optional[str] = None
    last_latency_ms: float = 0.0
    avg_step_latency_ms: float = 0.0
    total_forward_steps: int = 0
    tokens_processed: int = 0
    fallback_active: bool = False
    active_interconnect: str = "LOCAL"


class BackendAdapter(abc.ABC):
    """
    Abstract Base Class defining the unified interface contract for all
    Lauburu AI Sharding Daemon execution backends.
    """

    def __init__(self, node_id: str = "mac_host", config: Optional[Dict[str, Any]] = None):
        self.node_id = node_id
        self.config = config or {}
        self.current_shard: Optional[ShardSpec] = None
        self.is_loaded: bool = False
        self.network_awareness: Optional[Any] = None
        self.total_steps: int = 0
        self.total_tokens: int = 0
        self.step_latencies: List[float] = []
        self.peak_memory_mb: float = 0.0
        self.fallback_mode: bool = False
        self.last_error: Optional[str] = None
        logger.info(f"Initialized {self.get_backend_type()} adapter for node '{node_id}'")

    @abc.abstractmethod
    def get_backend_type(self) -> str:
        """Returns the unique backend identifier string (e.g. 'petals_dht', 'llamacpp_rpc')."""
        raise NotImplementedError

    @abc.abstractmethod
    def load_model_shard(self, model_name: str, layer_range: Tuple[int, int], device: str = "cpu", **kwargs) -> bool:
        """
        Loads the specified slice of model layers [start_layer, end_layer) into memory.
        Returns True on successful initialization and allocation.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def forward_tensor_step(self, hidden_states: Union[TensorPayload, np.ndarray, Any], layer_idx: int, **kwargs) -> TensorPayload:
        """
        Executes a forward pass step through a single transformer layer/block.
        Returns transformed TensorPayload activations.
        """
        raise NotImplementedError

    def forward_tensor_range(self, hidden_states: Union[TensorPayload, np.ndarray, Any], start_layer: int, end_layer: int, **kwargs) -> TensorPayload:
        """
        Executes a sequential forward pass through a range of contiguous layers [start_layer, end_layer).
        Default implementation iterates step-by-step with intermediate activation propagation.
        """
        curr = hidden_states if isinstance(hidden_states, TensorPayload) else TensorPayload(data=np.asarray(hidden_states))
        for l_idx in range(start_layer, end_layer):
            curr = self.forward_tensor_step(curr, l_idx, **kwargs)
        return curr

    @abc.abstractmethod
    def get_memory_usage_mb(self) -> float:
        """Returns current allocated memory footprint in Megabytes (MB)."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_healthy(self) -> bool:
        """Evaluates hardware availability, memory headroom, socket reachability, and thermal state."""
        raise NotImplementedError

    @abc.abstractmethod
    def unload_model_shard(self) -> bool:
        """Releases all allocated model weights, KV caches, and GPU buffers from memory."""
        raise NotImplementedError

    def set_network_awareness(self, unal: Any) -> None:
        """Hooks the Unified Network Awareness Layer for real-time link scoring and fallback steering."""
        self.network_awareness = unal
        logger.info(f"[{self.get_backend_type()}] Attached UNAL network awareness layer.")

    def get_status(self) -> AdapterStatus:
        """Generates comprehensive status snapshot for daemon telemetry and cluster monitoring."""
        avg_lat = float(np.mean(self.step_latencies[-50:])) if self.step_latencies else 0.0
        last_lat = self.step_latencies[-1] if self.step_latencies else 0.0
        curr_mem = self.get_memory_usage_mb()
        self.peak_memory_mb = max(self.peak_memory_mb, curr_mem)

        return AdapterStatus(
            backend_type=self.get_backend_type(),
            node_id=self.node_id,
            is_loaded=self.is_loaded,
            model_id=self.current_shard.model_id if self.current_shard else "",
            start_layer=self.current_shard.start_layer if self.current_shard else 0,
            end_layer=self.current_shard.end_layer if self.current_shard else 0,
            total_layers=self.current_shard.total_layers if self.current_shard else 0,
            device=self.current_shard.device if self.current_shard else "cpu",
            allocated_memory_mb=curr_mem,
            peak_memory_mb=self.peak_memory_mb,
            memory_ceiling_mb=self.config.get("memory_ceiling_mb", 16384.0),
            healthy=self.is_healthy(),
            error_message=self.last_error,
            last_latency_ms=last_lat,
            avg_step_latency_ms=avg_lat,
            total_forward_steps=self.total_steps,
            tokens_processed=self.total_tokens,
            fallback_active=self.fallback_mode,
            active_interconnect=self.config.get("primary_interconnect", "LOCAL")
        )

    def _record_step(self, latency_ms: float, tokens: int = 1):
        """Internal telemetry helper to record execution metrics."""
        self.total_steps += 1
        self.total_tokens += tokens
        self.step_latencies.append(latency_ms)
        if len(self.step_latencies) > 1000:
            self.step_latencies.pop(0)
