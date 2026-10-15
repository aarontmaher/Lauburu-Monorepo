#!/usr/bin/env python3
"""
Canonical delegation wrapper for Google Jules 300/day Autonomous Orchestrator.
Routes all calls directly to 06_scripts_and_tooling/integrations_and_mcp/jules_debate_dispatcher.py.
"""
import sys
from pathlib import Path

INTEGRATIONS_DIR = Path(__file__).resolve().parent / "integrations_and_mcp"
if str(INTEGRATIONS_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATIONS_DIR))

from jules_debate_dispatcher import (  # noqa: E402,F401
    MONOREPO_ROOT,
    LOG_FILE,
    BACKLOG_FILE,
    SESSIONS_FILE,
    JULES_AUTOMATION_ENABLED,
    MAX_CONCURRENT_SESSIONS,
    DAILY_TASK_LIMIT,
    get_daily_dispatch_count,
    ensure_backlog,
    execute_tri_orchestrator_debate,
    dispatch_to_jules,
    pull_and_audit_sessions,
    run_cycle,
)

if __name__ == "__main__":
    run_cycle()
