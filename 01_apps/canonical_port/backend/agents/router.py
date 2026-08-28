"""
Canonical Agents & Crons API Router
Version: 3.0.0-CANONICAL

Provides REST API endpoints for:
- Autonomous agent task execution (/run)
- Background cron scheduling & job telemetry (/crons, /crons/start, /crons/stop)
- Multi-AI Quota & Rate-Limiter status (/quota)
- Specialist tools catalog (/tools)
- Mesh self-healing trigger (/self-heal)
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from .quota_governor import get_quota_governor
from .cloud_ai_router import CloudAIRouter
from .smolagents_ecosystem import SmolagentAgentWrapper
from .cron_scheduler import get_cron_scheduler
from .self_healing_daemon import get_self_healing_daemon


class AgentRunRequest(BaseModel):
    task: str = Field(..., description="Autonomous task or prompt to execute")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional tool parameters")


class SelfHealRequest(BaseModel):
    action: str = Field(default="all", description="Self-healing action to perform: all, clean_git_lock, wol")
    target_node: Optional[str] = Field(None, description="Optional target node identifier")


def create_agents_router() -> APIRouter:
    """Factory creating APIRouter for agent ecosystem endpoints."""
    router = APIRouter(prefix="/agents", tags=["Autonomous Agents Ecosystem"])
    ai_router = CloudAIRouter()
    agent_wrapper = SmolagentAgentWrapper(ai_router)

    @router.get("/quota", summary="Multi-AI Quota & Rate Limiting Status")
    def get_quota() -> Dict[str, Any]:
        """Return live status of local AI, Cloudflare free tier, and Gemini 300 req/24h Ultra quota."""
        governor = get_quota_governor()
        return governor.get_quota_status()

    @router.post("/run", summary="Run Autonomous Agent Task")
    async def post_agent_run(request: AgentRunRequest) -> Dict[str, Any]:
        """Dispatch task to Smolagents wrapper with automatic local/cloud LLM routing."""
        result = await agent_wrapper.run_autonomous_cycle(request.task, **(request.params or {}))
        return result

    @router.get("/crons", summary="List Background Cron Jobs")
    def get_crons() -> Dict[str, Any]:
        """Return catalog of background cron tasks, execution counts, and recent history."""
        scheduler = get_cron_scheduler()
        return scheduler.get_jobs_status()

    @router.post("/crons/start", summary="Start Background Cron Scheduler")
    def post_crons_start() -> Dict[str, Any]:
        """Start periodic background monitoring and self-healing crons."""
        scheduler = get_cron_scheduler()
        scheduler.start()
        return {
            "success": True,
            "message": "Cron scheduler started",
            "status": scheduler.get_jobs_status(),
        }

    @router.post("/crons/stop", summary="Stop Background Cron Scheduler")
    async def post_crons_stop() -> Dict[str, Any]:
        """Gracefully stop and cancel all background cron tasks."""
        scheduler = get_cron_scheduler()
        await scheduler.stop()
        return {
            "success": True,
            "message": "Cron scheduler stopped",
            "status": scheduler.get_jobs_status(),
        }

    @router.get("/tools", summary="List Specialist Agent Tools")
    def get_tools() -> Dict[str, Any]:
        """Return catalog of available specialist agent tools."""
        catalog = {}
        for name, tool in agent_wrapper.tools.items():
            catalog[name] = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
        return {
            "total_tools": len(catalog),
            "tools": catalog,
        }

    @router.post("/self-heal", summary="Trigger Mesh Node Self-Healing")
    async def post_self_heal(request: Optional[SelfHealRequest] = None) -> Dict[str, Any]:
        """Trigger autonomous self-healing routines across mesh nodes and locks."""
        daemon = get_self_healing_daemon()
        result = await daemon.run_self_healing_cycle()
        return result

    return router
