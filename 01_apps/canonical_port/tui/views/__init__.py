"""Canonical Port TUI Views Package."""
from .chat_ide_view import ChatIdeView, TuiBetaChatIDEView
from .hardware_noc_view import HardwareNocView
from .hardware_view import HardwareView
from .biometrics_view import BiometricsView
from .architecture_explorer_view import ArchitectureExplorerView
from .agi_coding_terminal_view import AgiCodingTerminalView
from .ai_inference_view import AiInferenceView
from .training_view import TrainingView
from .governance_view import GovernanceView
from .tooling_view import ToolingView
from .optimization_view import OptimizationView
from .network_view import NetworkView

__all__ = [
    "ChatIdeView",
    "TuiBetaChatIDEView",
    "HardwareNocView",
    "HardwareView",
    "BiometricsView",
    "ArchitectureExplorerView",
    "AgiCodingTerminalView",
    "AiInferenceView",
    "TrainingView",
    "GovernanceView",
    "ToolingView",
    "OptimizationView",
    "NetworkView",
]
