"""
Canonical Port TUI Screens Package
Version: 4.0.0-HARMONIZED
9-Screen Stability Hierarchy:
- Screen 1: ChatIdeScreen / AgiCodingTerminalScreen (Home / Screen 1) — Key 'c' or '1' (Default startup screen)
- Screen 2: NetworkScreen (Layer 0 Primary) — Key 'n' or '2'
- Screen 3: HardwareScreen (Layer 1) — Key 'h' or '3'
- Screen 4: BiometricsScreen (Layer 2) — Key 'b' or '4'
- Screen 5: AiInferenceScreen (Layer 3) — Key 'i' or '5'
- Screen 6: TrainingScreen (Layer 4) — Key 't' or '6'
- Screen 7: GovernanceScreen (Layer 5) — Key 'g' or '7'
- Screen 8: ToolingScreen (Layer 6) — Key 's' or '8'
- Screen 9: OptimizationScreen (Shells) — Key 'o' or '9'
"""

from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.chat_ide_screen import ChatIdeScreen
from screens.network_screen import NetworkScreen
from screens.hardware_screen import HardwareScreen
from screens.biometrics_screen import BiometricsScreen
from screens.ai_inference_screen import AiInferenceScreen
from screens.training_screen import TrainingScreen
from screens.governance_screen import GovernanceScreen
from screens.tooling_screen import ToolingScreen
from screens.optimization_screen import OptimizationScreen
from screens.all_tabs_screen import AllTabsGridScreen
from screens.architecture_explorer_screen import ArchitectureExplorerScreen

__all__ = [
    "AgiCodingTerminalScreen",
    "ChatIdeScreen",
    "NetworkScreen",
    "HardwareScreen",
    "BiometricsScreen",
    "AiInferenceScreen",
    "TrainingScreen",
    "GovernanceScreen",
    "ToolingScreen",
    "OptimizationScreen",
    "AllTabsGridScreen",
    "ArchitectureExplorerScreen",
]
