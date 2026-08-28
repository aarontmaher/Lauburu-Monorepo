"""
Spec-11 & Spec-12: Combined Security & Continuous LoRA Evolution Module
Governs Hardware Isolation, HMAC Encryption, and Continuous 24/7 LoRA Distillation.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter

from .spec_11_security import Spec11SecurityModule
from .spec_12_continuous_lora import Spec12ContinuousLoraModule
from ..base_module import BaseSpecModule
from ..models import ModuleCategory, ModuleHealthStatus, current_utc_time


class Spec1112SecurityLoraModule(BaseSpecModule):
    """Unified Spec-11 and Spec-12 Security & Continuous LoRA Evolution."""

    module_id: str = "spec-11-12"
    display_name: str = "Spec-11/12 Security & LoRA Evolution"
    spec_version: str = "3.0.0"
    category: ModuleCategory = ModuleCategory.SECURITY
    description: str = "Hardware Isolation, HMAC Authentication, Continuous 24/7 LoRA Distillation & Model Merging"
    spec_path: Optional[str] = None
    dependencies: List[str] = ["spec-00"]
    tags: ["security", "hmac", "lora", "distillation", "red_blue_team"]

    def __init__(self) -> None:
        super().__init__()
        self.security_submodule = Spec11SecurityModule()
        self.lora_submodule = Spec12ContinuousLoraModule()

    def get_status(self) -> Dict[str, Any]:
        """Return combined status."""
        sec_status = self.security_submodule.get_status()
        lora_status = self.lora_submodule.get_status()

        status = ModuleHealthStatus.HEALTHY
        metrics = {
            "security": sec_status.get("metrics", {}),
            "lora": lora_status.get("metrics", {}),
            "threat_level": sec_status.get("metrics", {}).get("threat_level", "LOW"),
            "current_lora_loss": lora_status.get("metrics", {}).get("current_loss", 0.0),
            "uptime_seconds": round(self.uptime_seconds, 2),
        }

        return {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "status": status.value,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "last_check": current_utc_time().isoformat(),
            "message": f"Security & LoRA systems operational (Threat: {metrics['threat_level']}, LoRA Loss: {metrics['current_lora_loss']})",
            "metrics": metrics,
            "active_connections": 2,
            "error_count": self.error_count,
            "endpoints": {
                "security": "sec://mesh-isolation-gate",
                "lora": "lora://continuous-peft-distiller",
            },
        }

    def get_telemetry_schema(self) -> Dict[str, Any]:
        """Return combined telemetry schema."""
        return {
            "module_id": self.module_id,
            "schema_name": "security_lora_combined_telemetry",
            "version": self.spec_version,
            "description": "Combined telemetry for security perimeters and continuous LoRA training",
            "fields": [
                {"field_name": "threat_level", "field_type": "string", "required": True},
                {"field_name": "current_lora_loss", "field_type": "float", "required": True},
                {"field_name": "uptime_seconds", "field_type": "float", "unit": "s", "required": True},
            ],
        }

    def health_check(self) -> Dict[str, Any]:
        """Execute health checks on both submodules."""
        t0 = time.time() if "time" in globals() else 0.0
        import time as _t
        t0 = _t.time()
        sec_hc = self.security_submodule.health_check()
        lora_hc = self.lora_submodule.health_check()
        latency_ms = (_t.time() - t0) * 1000.0

        healthy = sec_hc.get("healthy", False) and lora_hc.get("healthy", False)
        status = ModuleHealthStatus.HEALTHY if healthy else ModuleHealthStatus.DEGRADED

        return {
            "module_id": self.module_id,
            "healthy": healthy,
            "status": status.value,
            "latency_ms": round(latency_ms, 2),
            "checks": {
                "security_submodule_ok": sec_hc.get("healthy", False),
                "lora_submodule_ok": lora_hc.get("healthy", False),
            },
            "details": {"security": sec_hc, "lora": lora_hc},
            "timestamp": current_utc_time().isoformat(),
            "error_message": None if healthy else "Submodule health check failed",
        }

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate action to appropriate submodule."""
        if action.startswith("sec_") or action in ("verify_token", "run_security_scan"):
            return self.security_submodule.execute_action(action, params)
        elif action.startswith("lora_") or action in ("get_training_metrics", "merge_lora_weights"):
            return self.lora_submodule.execute_action(action, params)
        return super().execute_action(action, params)

    def get_routes(self) -> APIRouter:
        """Return combined APIRouter."""
        router = APIRouter(prefix="/spec-11-12", tags=["Spec-11/12 Security & LoRA"])

        @router.get("/combined-status")
        def get_combined():
            return self.get_status()

        return router


# Also export individual classes for clean discrete registry access
__all__ = [
    "Spec1112SecurityLoraModule",
    "Spec11SecurityModule",
    "Spec12ContinuousLoraModule",
]
