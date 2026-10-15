"""
================================================================================
Lauburu Sovereign Mesh: Omni Terminal Notebook Plugin
================================================================================
Subsystem: 01_apps/omniterminal_notebook_plugin
Version: 1.0.0-NOTEBOOK-PLUGIN-CANONICAL
Lauburu Mesh Ecosystem — 2026

Interactive Notebook Plugin providing:
1. %omni line magic for instant PTY status and snapshot HUD
2. %%omni_polyglot <lang> cell magic for multi-language coding practice & GRPO rewards
3. %%omni_training <protocol> cell magic for High-ROI AI training & Port 4004 stream
4. %omni_telemetry line magic for 7-layer authentic hardware analysis
5. %omni_widget line magic for embedded HTML5/WebSocket terminal canvas
================================================================================
"""

import sys
from pathlib import Path

pkg_dir = str(Path(__file__).parent)
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from .hardware_hud import NotebookHardwareAnalyzer, HardwareTelemetrySnapshot
from .polyglot_runner import NotebookPolyglotRunner, PolyglotExecutionResult
from .training_bridge import NotebookTrainingBridge
from .terminal_widget import OmniterminalNotebookWidget
from .magics import OmniterminalMagics


def load_ipython_extension(ipython):
    """Called by IPython when user runs: %load_ext omniterminal_notebook_plugin"""
    magics_instance = OmniterminalMagics(shell=ipython)
    ipython.register_magics(magics_instance)
    print("🚀 Lauburu Omni Terminal Notebook Plugin Loaded!")
    print("   Available Magics:")
    print("   • %omni [status|snapshot|telemetry|widget]")
    print("   • %%omni_polyglot <python|rust|bash|go|cpp>")
    print("   • %%omni_training <grpo_compiler_reward|dpo_debate_consensus|gbnf_serial_constrained>")
    print("   • %omni_telemetry (Authentic 7-Layer Hardware HUD)")
    print("   • %omni_widget (Interactive HTML5 Terminal Canvas)")


def unload_ipython_extension(ipython):
    """Called when user runs: %unload_ext omniterminal_notebook_plugin"""
    print("Lauburu Omni Terminal Notebook Plugin Unloaded.")


__all__ = [
    "load_ipython_extension",
    "unload_ipython_extension",
    "OmniterminalMagics",
    "NotebookHardwareAnalyzer",
    "HardwareTelemetrySnapshot",
    "NotebookPolyglotRunner",
    "PolyglotExecutionResult",
    "NotebookTrainingBridge",
    "OmniterminalNotebookWidget",
]

__version__ = "1.0.0"
