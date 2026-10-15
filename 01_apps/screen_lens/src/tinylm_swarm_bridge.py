#!/usr/bin/env python3
"""
tinylm_swarm_bridge.py
======================
Screen Lens Sovereign Bridge to the TinyLM Swarm and 8B Specialist.
Integrates into the Screen Lens live observation loop (Port 3037 / 4003):
- Gating: Checks whether screen state / command telemetry requires frontier escalation
- Speculation: Predicts next UI/CLI action distribution
- Telemetry: Returns latency and token sparing estimates directly into Screen Lens
"""

import os
import sys

SWARM_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/frontier_specialist_swarm"
sys.path.insert(0, SWARM_DIR)

try:
    from tinylm_swarm_coordinator import TinyLMSwarm
    from frontier_telemetry_larger_model_bridge import query_local_8b_specialist
    _SWARM_AVAILABLE = True
except Exception as e:
    _SWARM_AVAILABLE = False
    _INIT_ERROR = str(e)

_swarm_instance = None

def get_swarm():
    global _swarm_instance
    if _swarm_instance is None and _SWARM_AVAILABLE:
        _swarm_instance = TinyLMSwarm()
    return _swarm_instance

def audit_and_speculate(command_or_window_title, telemetry_output):
    """
    Evaluates telemetry through the TinyLM Swarm:
    1. Returns escalation decision
    2. Returns predicted tool/action
    3. If escalated, offers local 8B specialist fallback before cloud
    """
    if not _SWARM_AVAILABLE:
        return {"status": "UNAVAILABLE", "error": _INIT_ERROR}

    swarm = get_swarm()
    res = swarm.process_telemetry(command_or_window_title, telemetry_output)

    # If TinyLM escalation gate triggers ESCALATE_TO_FRONTIER,
    # invoke the local 8B Specialist first to spare cloud tokens
    if res.get("escalation_gate", {}).get("verdict") == "ESCALATE_TO_FRONTIER":
        spec_8b = query_local_8b_specialist(
            prompt="Analyze this escalation event and recommend immediate remediation.",
            telemetry=f"{command_or_window_title}\n{telemetry_output[:300]}"
        )
        res["local_8b_specialist_analysis"] = spec_8b

    return res

if __name__ == "__main__":
    import json
    print("Testing Screen Lens TinyLM Swarm Bridge...")
    out = audit_and_speculate("Screen Lens OCR Frame: terminal window active", "Exit Code 0: mesh sync active")
    print(json.dumps(out, indent=2))
