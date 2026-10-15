"""
Mesh Healer Subsystem Package
Part of Canonical Mesh Fallback Terminal (bluetooth_terminal_ide).
"""

from .healer_engine import HealerState, MeshHealer
from .nus_transport import NusTransport
from .outage_detector import MeshOutageDetector
from .protocol import (
    NUS_RX_UUID,
    NUS_SERVICE_UUID,
    NUS_TX_UUID,
    NusStreamDeframer,
    OOBMessage,
    assert_not_tunneling,
    calculate_chunk_size,
    chunk_payload,
    is_tunneling_payload,
    validate_oob_command,
)
from .session_spawner import SessionSpawner
from .shizuku_bridge import ShizukuBridge, ShizukuExecutionResult

__all__ = [
    "HealerState",
    "MeshHealer",
    "NusTransport",
    "MeshOutageDetector",
    "SessionSpawner",
    "ShizukuBridge",
    "ShizukuExecutionResult",
    "OOBMessage",
    "NusStreamDeframer",
    "NUS_SERVICE_UUID",
    "NUS_RX_UUID",
    "NUS_TX_UUID",
    "calculate_chunk_size",
    "chunk_payload",
    "is_tunneling_payload",
    "assert_not_tunneling",
    "validate_oob_command",
]
