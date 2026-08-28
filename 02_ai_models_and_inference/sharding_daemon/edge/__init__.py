"""
02_ai_models_and_inference/sharding_daemon/edge/__init__.py
===========================================================
Edge compute and mobile deployment module for the Lauburu AI Mesh.
Governs Android Termux execution, thermal telemetry, keepalive daemons,
and cross-node distributed tensor forward steps.
"""

from .pixel_termux_node import (
    PixelThermalSentinel,
    ThermalStatus,
    ThermalAction,
    PixelMemoryGovernor,
    PixelKeepaliveManager,
    PixelEdgeComputeEngine,
    PixelTermuxServer,
    PixelTermuxDeployer,
    EdgeNodeClient,
    get_termux_deployment_command,
    get_keepalive_commands,
)

__all__ = [
    "PixelThermalSentinel",
    "ThermalStatus",
    "ThermalAction",
    "PixelMemoryGovernor",
    "PixelKeepaliveManager",
    "PixelEdgeComputeEngine",
    "PixelTermuxServer",
    "PixelTermuxDeployer",
    "EdgeNodeClient",
    "get_termux_deployment_command",
    "get_keepalive_commands",
]
