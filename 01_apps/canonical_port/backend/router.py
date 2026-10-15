"""
Canonical App Router & Spec Modules API
Version: 3.0.0-CANONICAL

Provides unified REST routing for all 12 Lauburu Spec Modules,
mesh telemetry streams, and module-specific custom action endpoints.
"""

import sys
import json
import time
import datetime
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Header, status

from .models import (
    GlobalBackendSummary,
    MeshNodeState,
    ModuleActionRequest,
    ModuleActionResponse,
    SpecModuleHealthCheckResult,
    SpecModuleMetadata,
    SpecModuleStatus,
    SpecModuleTelemetry,
    TelemetrySchemaDefinition,
    current_utc_time,
)
from .state import BackendStateStore, get_backend_state


def create_app_router(state_store: Optional[BackendStateStore] = None) -> APIRouter:
    """
    Factory creating the canonical /api/v1 APIRouter.
    Binds all 12 spec modules and their sub-routers.
    """
    store = state_store or get_backend_state()
    router = APIRouter(prefix="/api/v1", tags=["Canonical Port API v1"])

    # ========================================================================
    # Global & System Endpoints
    # ========================================================================

    @router.get("/health", response_model=Dict[str, Any], summary="Central Backend Health")
    def get_health() -> Dict[str, Any]:
        """Return central backend health check summary."""
        summary = store.get_global_summary()
        return {
            "status": "HEALTHY" if summary["storage_healthy"] else "DEGRADED",
            "version": summary["version"],
            "uptime_seconds": summary["uptime_seconds"],
            "total_modules": summary["total_modules"],
            "healthy_modules": summary["healthy_modules"],
            "storage_healthy": summary["storage_healthy"],
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/mesh/nodes", summary="7-Layer Physical Mesh Topology")
    def get_mesh_nodes() -> Dict[str, Any]:
        """Return status for all 7 physical mesh network nodes."""
        return {"nodes": store.get_mesh_nodes()}

    @router.post("/mesh/wake", summary="Dispatches Line 1 Bluetooth Proximity Wake ➔ Line 2 WoL")
    @router.get("/mesh/wake", summary="Dispatches Line 1 Bluetooth Proximity Wake ➔ Line 2 WoL")
    def wake_mesh_nodes(device: Optional[str] = None) -> Dict[str, Any]:
        """Dispatches Line 1 Bluetooth Proximity Wake followed by UDP WoL and ADB."""
        sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling"))
        try:
            from mesh.wol_manager import WoLEngine
            engine = WoLEngine()
            if device:
                return engine.wake_device(device)
            return engine.wake_all()
        except Exception as e:
            return {"error": f"Mesh wake failed: {e}", "success": False}

    @router.post("/mesh/heal", summary="Trigger Mesh Autonomous Self-Healing (Bluetooth First)")
    @router.get("/mesh/heal", summary="Trigger Mesh Autonomous Self-Healing (Bluetooth First)")
    def heal_mesh_nodes() -> Dict[str, Any]:
        """Executes mesh autonomous self-healing starting with Line 1 Bluetooth Proximity Wake."""
        sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling"))
        try:
            from mesh.wol_manager import WoLEngine
            engine = WoLEngine()
            return engine.wake_all()
        except Exception as e:
            return {"error": f"Mesh heal failed: {e}", "success": False}

    @router.post("/chat", summary="In-App Edge AI Chat Stream over prima.cpp & llama.cpp")
    def post_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chat inference over Qwen 3.8 Max / Qwen 3.8 Max Abliterated."""
        from .edge_chat_engine import UnifiedInAppEdgeEngine, QWEN_MODELS
        message = payload.get("message") or payload.get("prompt", "")
        history = payload.get("history", [])
        model_id = payload.get("model", "qwen_38_max")
        max_tokens = payload.get("max_tokens")
        return UnifiedInAppEdgeEngine.process_user_query(message, chat_history=history, model_id=model_id, max_tokens=max_tokens)

    @router.get("/chat/models", summary="Available Chat AI Models")
    def get_chat_models() -> Dict[str, Any]:
        """Return available chat models (Qwen 3.8 Max, Qwen 3.8 Max Abliterated)."""
        from .edge_chat_engine import QWEN_MODELS
        return {"models": list(QWEN_MODELS.values())}

    # ========================================================================
    # Apple Neural Engine (ANE) & Unified RAM Coprocessor Endpoints
    # ========================================================================

    @router.get("/npu/telemetry", summary="Apple Neural Engine (ANE) Telemetry")
    def get_npu_telemetry() -> Dict[str, Any]:
        """Return real-time ANE 16-Core hardware metrics, systolic latency, and active TOPS."""
        from .npu_unified_engine import NpuUnifiedEngine
        return NpuUnifiedEngine.get_instance().get_telemetry()

    @router.get("/npu/unified-ram", summary="Apple Silicon Unified Memory Profile")
    def get_npu_unified_ram() -> Dict[str, Any]:
        """Return deep architecture profile of Apple Silicon Unified RAM (24GB @ 273 GB/s)."""
        from .npu_unified_engine import NpuUnifiedEngine
        return NpuUnifiedEngine.get_instance().get_unified_ram_profile()

    # ========================================================================
    # Bluetooth Serial Terminal & Router Dongle Endpoints
    # ========================================================================

    @router.get("/terminal/bluetooth/status", summary="Bluetooth Serial Terminal & Router Dongle State")
    def get_bluetooth_terminal_status() -> Dict[str, Any]:
        """Returns live status of Bluetooth Serial Terminal and OpenWrt Router Dongle."""
        import socket
        daemon_online = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                daemon_online = (s.connect_ex(("127.0.0.1", 4005)) == 0)
        except Exception:
            pass

        movesense_info = {
            "device": "Movesense 261030002013",
            "mac": "74:92:BA:11:36:D6",
            "connected": False,
            "heart_rate_bpm": None,
            "battery_pct": None,
            "status": "WAITING_FOR_SENSOR (--)"
        }
        try:
            movesense_path = Path(__file__).resolve().parent.parent.parent.parent / "03_biometrics_and_telemetry" / "movesense_readiness_live.json"
            if movesense_path.exists():
                with open(movesense_path, "r") as mf:
                    mdata = json.load(mf)
                    st = mdata.get("sensor_telemetry", {})
                    movesense_info["connected"] = bool(st.get("connected", False))
                    movesense_info["heart_rate_bpm"] = st.get("heart_rate_bpm")
                    movesense_info["status"] = mdata.get("status", "WAITING_FOR_SENSOR")
        except Exception:
            pass

        return {
            "serial_daemon": {
                "port": 4005,
                "online": daemon_online,
                "protocol": "Bluetooth SPP / RFCOMM Bridge",
                "tty_device": "/dev/tty.Bluetooth-Incoming-Port"
            },
            "router_dongle": {
                "adapter": "Lauburu-Router-BT",
                "mac": "8C:86:DD:00:26:41",
                "version": "Bluetooth 5.1 (Realtek)",
                "spp_channel": 1,
                "target_device": "GL-MT3600BE Gateway (100.122.185.123)"
            },
            "movesense_telemetry": movesense_info,
            "connected_peripherals": [
                {"name": "Samsung Galaxy S20", "role": "Kai Morich Serial Bluetooth Terminal Client", "adb_target": "100.84.40.95:5555"}
            ],
            "ai_engines": {
                "llama_cpp": "http://127.0.0.1:8081",
                "prima_cpp": "http://127.0.0.1:8082"
            }
        }

    @router.post("/npu/infer", summary="Zero-Copy NPU Systolic Biometrics Inference")
    def post_npu_infer(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sub-millisecond systolic INT8 inference over 512Hz ECG or signal array."""
        from .npu_unified_engine import NpuUnifiedEngine
        signal_data = payload.get("signal", [0.0] * 256)
        out = NpuUnifiedEngine.get_instance().infer_biometric_anomaly(signal_data)
        return {
            "task_id": out.task_id,
            "executed_on": out.executed_on,
            "active_tops": out.active_tops,
            "latency_us": out.latency_us,
            "zero_copy_ram_bytes": out.zero_copy_ram_bytes,
            "ram_sanctuary_ok": out.ram_sanctuary_ok,
            "result": out.result
        }

    @router.post("/npu/classify", summary="Zero-Copy Prompt Intent Classification")
    def post_npu_classify(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute on-device NPU intent classification with 0.0 MB RAM overhead."""
        from .npu_unified_engine import NpuUnifiedEngine
        prompt = payload.get("prompt") or payload.get("message", "")
        out = NpuUnifiedEngine.get_instance().classify_prompt_intent(prompt)
        return {
            "task_id": out.task_id,
            "executed_on": out.executed_on,
            "latency_us": out.latency_us,
            "zero_copy_ram_bytes": out.zero_copy_ram_bytes,
            "result": out.result
        }

    @router.post("/npu/speculative-draft", summary="Speculative Token Draft Generation")
    def post_npu_speculative_draft(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate speculative draft tokens on ANE systolic array (>2,000 tok/s)."""
        from .npu_unified_engine import NpuUnifiedEngine
        prefix = payload.get("prefix", "")
        max_tokens = int(payload.get("max_tokens", 5))
        out = NpuUnifiedEngine.get_instance().generate_speculative_draft(prefix, max_tokens=max_tokens)
        return {
            "task_id": out.task_id,
            "executed_on": out.executed_on,
            "latency_us": out.latency_us,
            "result": out.result
        }

    @router.post("/npu/analyze-data", summary="Global NPU Data & Trend Analysis")
    def post_npu_analyze_data(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute zero-copy systolic time-series trend analysis and outlier detection."""
        from .npu_unified_engine import NpuUnifiedEngine
        values = payload.get("values", [1.0, 2.0, 3.0])
        name = payload.get("dataset_name", "telemetry_stream")
        z_thresh = float(payload.get("z_threshold", 2.5))
        out = NpuUnifiedEngine.get_instance().analyze_timeseries_stream(values, dataset_name=name, z_threshold=z_thresh)
        return {
            "task_id": out.task_id,
            "executed_on": out.executed_on,
            "latency_us": out.latency_us,
            "zero_copy_ram_bytes": out.zero_copy_ram_bytes,
            "ram_sanctuary_ok": out.ram_sanctuary_ok,
            "result": out.result
        }

    @router.get("/npu/training/e2e-status", summary="End-to-End App Dev Workflow 24/7 Training Status")
    def get_e2e_training_status() -> Dict[str, Any]:
        """Return real-time state of the 24/7 E2E App Dev Workflow Training Protocol and Overnight Daemon."""
        e2e_state_path = Path("/tmp/e2e_app_dev_training_state.json")
        overnight_state_path = Path("/tmp/overnight_training_state.json")

        e2e_data = {}
        if e2e_state_path.exists():
            try:
                with open(e2e_state_path, "r", encoding="utf-8") as f:
                    e2e_data = json.load(f)
            except Exception:
                pass

        overnight_data = {}
        if overnight_state_path.exists():
            try:
                with open(overnight_state_path, "r", encoding="utf-8") as f:
                    overnight_data = json.load(f)
            except Exception:
                pass

        return {
            "status": "HEALTHY",
            "e2e_workflow_training": e2e_data,
            "overnight_npu_training": overnight_data,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    # ========================================================================
    # Global SRAM Optimizer & Co-Working AI Endpoints
    # ========================================================================

    @router.get("/sram/profile", summary="Global SRAM Hardware Profile & Pool Efficiency")
    def get_sram_profile() -> Dict[str, Any]:
        """Return global SRAM hardware specs, active tile pools, and monorepo audit."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "00_core_infrastructure/sram_optimizer"))
        try:
            from sram_global_optimizer import SramGlobalOptimizer
            opt = SramGlobalOptimizer.get_instance()
            return opt.audit_monorepo_sram_efficiency()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    @router.post("/sram/compact", summary="Trigger Zero-Copy SRAM Memoryview Compaction")
    def post_sram_compact() -> Dict[str, Any]:
        """Clear stale pointers and defragment on-chip SRAM memoryview tile pool."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "00_core_infrastructure/sram_optimizer"))
        try:
            from sram_global_optimizer import SramGlobalOptimizer
            opt = SramGlobalOptimizer.get_instance()
            return opt.compact_memory()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    @router.post("/ai/co-working-infer", summary="Speculative Tri-Tier Co-Working Inference (NPU + Local + Cloud)")
    def post_coworking_infer(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute speculative tri-tier inference collaborative across NPU, local LLMs, and cloud."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "02_ai_models_and_inference"))
        try:
            from npu_co_working_orchestrator import NpuCoWorkingOrchestrator, CoWorkingInferenceRequest
            prompt = payload.get("prompt", "Check system status")
            target_tier = payload.get("target_tier", "AUTO")
            k_draft = int(payload.get("draft_tokens_k", 4))
            enable_red = bool(payload.get("enable_red_team_audit", False))

            orch = NpuCoWorkingOrchestrator.get_instance()
            req = CoWorkingInferenceRequest(
                prompt=prompt,
                target_tier=target_tier,
                draft_tokens_k=k_draft,
                enable_red_team_audit=enable_red
            )
            res = orch.dispatch(req)
            return res.to_dict()
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    @router.post("/ai/npu-validate-syntax", summary="NPU Micro-Syntax & Bracket Validator (Tier 0 Code Gate)")
    def post_npu_validate_syntax(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validates syntax and bracket balance at >2,800 tok/s on on-chip SRAM with 0 MB host RAM."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "02_ai_models_and_inference"))
        try:
            from npu_micro_syntax_validator import NpuMicroSyntaxValidator
            code_str = payload.get("code", "")
            language = payload.get("language", "python")
            validator = NpuMicroSyntaxValidator.get_instance()
            res = validator.validate_code(code_str, language=language)
            return {
                "is_valid": res.is_valid,
                "language": res.language,
                "latency_us": res.latency_us,
                "error_message": res.error_message,
                "bracket_balanced": res.bracket_balanced,
                "token_count": res.token_count,
                "host_ram_mb": res.host_ram_mb,
                "metal_gpu_load": res.metal_gpu_load,
                "metrics": validator.get_metrics()
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    @router.post("/sram/calculate-elo", summary="NPU Bradley-Terry ELO Calculation in On-Chip SRAM")
    def post_sram_calculate_elo(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates 1.13 µs Bradley-Terry ELO updates with incentive bonuses for verified models."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "00_core_infrastructure"))
        try:
            from npu_numerical_sentinel import NpuNumericalSentinel
            r_a = float(payload.get("r_a", 1500.0))
            r_b = float(payload.get("r_b", 1500.0))
            actual_score = float(payload.get("actual_score", 1.0))
            sentinel = NpuNumericalSentinel.get_instance()
            res = sentinel.calculate_elo_update(r_a, r_b, actual_score)
            return {"status": "SUCCESS", "data": res}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    @router.get("/sram/telemetry-anomaly", summary="NPU 16-Channel Hardware Telemetry Anomaly & RAM Sanctuary")
    def get_sram_telemetry_anomaly() -> Dict[str, Any]:
        """Evaluates live 16-channel telemetry and flags Rule 3 RAM sanctuary breaches in <1.5 ms."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "00_core_infrastructure"))
        try:
            from npu_numerical_sentinel import NpuNumericalSentinel
            sentinel = NpuNumericalSentinel.get_instance()
            report = sentinel.evaluate_telemetry_anomaly()
            return {
                "status": "SUCCESS",
                "anomaly_score": report.anomaly_score,
                "is_nominal": report.is_nominal,
                "sanctuary_ok": report.sanctuary_ok,
                "ram_free_gb": report.ram_free_gb,
                "latency_us": report.latency_us,
                "anomalies_flagged": report.anomalies_flagged,
                "evacuation_required": report.evacuation_required,
                "hardware_core": report.hardware_core,
                "metrics": sentinel.get_metrics()
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}


    # ========================================================================
    # Neo Project Graph, Structuring & Organization Endpoints
    # ========================================================================

    @router.get("/neo/graph", summary="Neo Multi-Domain Monorepo Project App Graph")
    def get_neo_graph() -> Dict[str, Any]:
        """Return full 8-domain interactive graph of TUIs, webapps, notebooks, and hardware nodes."""
        from .neo_project_graph_service import NeoProjectGraphService
        return NeoProjectGraphService.get_full_graph()

    @router.get("/neo/structure", summary="Neo Monorepo Structuring & Organization Index")
    def get_neo_structure() -> Dict[str, Any]:
        """Scan and organize all 8 monorepo domains, AST distributions, and module cohesion."""
        from .neo_project_graph_service import NeoProjectGraphService
        return NeoProjectGraphService.get_project_structure_and_organization()

    @router.post("/neo/sync-obsidian", summary="Sync Neo Project App Graph to Obsidian Vault")
    def post_neo_sync_obsidian() -> Dict[str, Any]:
        """Generate and serialize the multi-domain interactive graph to Obsidian Vault."""
        from .neo_project_graph_service import NeoProjectGraphService
        return NeoProjectGraphService.sync_graph_to_obsidian()

    # ========================================================================
    # Network & Device Analysis for Compute Payment Endpoints
    # ========================================================================

    @router.get("/compute/analysis", summary="Network & Device Analysis for Compute Payment")
    def get_compute_analysis() -> Dict[str, Any]:
        """Analyze 7-layer mesh nodes, physical cable bottlenecks, and compute credit balance."""
        from .compute_payment_engine import ComputePaymentEngine
        return ComputePaymentEngine.analyze_network_and_devices()

    @router.get("/compute/ledger", summary="Compute Credit Ledger")
    def get_compute_ledger() -> Dict[str, Any]:
        """Return full compute credit ledger, token balances, and transaction history."""
        from .compute_payment_engine import ComputePaymentEngine
        return ComputePaymentEngine.load_ledger()

    @router.post("/compute/record", summary="Record Token Contribution / Consumption")
    def post_compute_record(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Record token transactions against the compute ledger."""
        from .compute_payment_engine import ComputePaymentEngine
        device_id = payload.get("device_id", "Mac_Node")
        tokens = int(payload.get("tokens", 0))
        is_contrib = bool(payload.get("is_contribution", False))
        desc = payload.get("description", "")
        tx = ComputePaymentEngine.record_token_transaction(device_id, tokens, is_contrib, desc)
        return {"success": True, "transaction": tx}

    # ========================================================================
    # Shopify Membership & Feature Gating Endpoints
    # ========================================================================

    @router.get("/commerce/membership/status", summary="Shopify Membership Status")
    def get_membership_status(customer_id: Optional[str] = Query(None)) -> Dict[str, Any]:
        """Return active subscription tier, features unlocked, and net credit offset."""
        from .shopify_membership_service import ShopifyMembershipService
        return ShopifyMembershipService.get_status(customer_id)

    @router.get("/commerce/membership/tiers", summary="Shopify Membership Tiers Catalog")
    def get_membership_tiers() -> Dict[str, Any]:
        """Return available subscription tiers and feature matrices."""
        from .shopify_membership_service import ShopifyMembershipService
        return {"tiers": ShopifyMembershipService.get_tiers()}

    @router.post("/commerce/membership/checkout", summary="Create Shopify Storefront Checkout Cart")
    def post_membership_checkout(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate checkout cart URL for specified membership tier."""
        from .shopify_membership_service import ShopifyMembershipService
        tier_id = payload.get("tier_id", "athlete_starter")
        return ShopifyMembershipService.create_checkout_cart(tier_id)

    @router.post("/commerce/membership/override", summary="Sovereign Operator Tier Override")
    def post_membership_override(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Instantly override active membership tier for sovereign testing."""
        from .shopify_membership_service import ShopifyMembershipService
        tier_id = payload.get("tier_id", "mesh_gym_master")
        res = ShopifyMembershipService.set_tier_override(tier_id)
        return {"success": True, "status": res}

    @router.post("/commerce/webhook/shopify", summary="Shopify Webhook Callback Listener")
    def post_shopify_webhook(
        payload: Dict[str, Any],
        x_shopify_topic: Optional[str] = Header(None, alias="X-Shopify-Topic"),
        x_shopify_hmac_sha256: Optional[str] = Header(None, alias="X-Shopify-Hmac-Sha256")
    ) -> Dict[str, Any]:
        """Process incoming Shopify webhook event (orders, subscriptions, app uninstall)."""
        from .shopify_membership_service import ShopifyMembershipService
        topic = x_shopify_topic or payload.get("topic", "orders/paid")
        return ShopifyMembershipService.process_webhook(topic, payload, x_shopify_hmac_sha256)

    # ========================================================================
    # SeaweedFS Distributed Storage & IDE Bridge Endpoints
    # ========================================================================

    @router.get("/storage/seaweed/status", summary="SeaweedFS Distributed Storage Health")
    def get_seaweed_status() -> Dict[str, Any]:
        """Probe SeaweedFS Master, Filer, WebDAV, and FUSE mount health."""
        from .seaweed_ide_bridge import SeaweedIDEBridge
        return SeaweedIDEBridge.get_status()

    @router.get("/storage/seaweed/tree", summary="SeaweedFS Distributed VFS Tree")
    def get_seaweed_tree(path: str = Query("/", description="VFS directory path")) -> Dict[str, Any]:
        """Browse distributed VFS entries from SeaweedFS Filer."""
        from .seaweed_ide_bridge import SeaweedIDEBridge
        return SeaweedIDEBridge.list_filer_directory(path)

    @router.post("/storage/seaweed/heal", summary="Self-Heal SeaweedFS FUSE Mount")
    def post_seaweed_heal() -> Dict[str, Any]:
        """Execute autonomous reflex arc to recover hung FUSE mounts."""
        from .seaweed_ide_bridge import SeaweedIDEBridge
        return SeaweedIDEBridge.heal_mount()

    @router.post("/storage/seaweed/offload_asan", summary="Offload ASan Minidump to DFS")
    def post_seaweed_offload_asan(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Offload AddressSanitizer crash log or compiler minidump to SeaweedFS DFS."""
        from .seaweed_ide_bridge import SeaweedIDEBridge
        crash_id = payload.get("crash_id", f"crash_{int(time.time())}")
        error_type = payload.get("error_type", "ASAN_REPORT")
        crash_log = payload.get("crash_log", "")
        source_file = payload.get("source_file", "unknown")
        return SeaweedIDEBridge.offload_asan_minidump(crash_id, error_type, crash_log, source_file)

    # ========================================================================
    # Google Cloud $1,400 Credit Escalation & Spot GPU Governor Endpoints
    # ========================================================================

    @router.get("/cloud/gcp/status", summary="Google Cloud $1,400 Credit Status")
    def get_gcp_credit_status() -> Dict[str, Any]:
        """Return live status of the $1,400 AUD credit grant and circuit breaker."""
        from .cloud_governor_service import CloudGovernorService
        return CloudGovernorService.get_credit_status()

    @router.get("/cloud/gcp/batches", summary="GCP Staged Distillation Batches")
    def get_gcp_batches() -> Dict[str, Any]:
        """Return the 4 staged student model distillation batches."""
        from .cloud_governor_service import CloudGovernorService
        return {"batches": CloudGovernorService.get_staged_batches()}

    @router.post("/cloud/gcp/burst/preview", summary="Preview Spot GPU Burst Run")
    def post_gcp_burst_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate micro-burst spending cap and calculate Spot L4 duration."""
        from .cloud_governor_service import CloudGovernorService
        batch_id = payload.get("batch_id", "BATCH_01_EDGE_SLMS")
        projected_spend = float(payload.get("projected_spend_aud", 8.50))
        return CloudGovernorService.preview_burst(batch_id, projected_spend)

    @router.post("/cloud/gcp/dataset/export", summary="Export Lakehouse LoRA Dataset for Vertex AI")
    def post_gcp_dataset_export(payload: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Extract validated instruction pairs from Lakehouse for Vertex AI batch distillation."""
        from .cloud_governor_service import CloudGovernorService
        limit = int(payload.get("limit", 500))
        return CloudGovernorService.export_lakehouse_dataset_for_vertex(limit)

    # ========================================================================
    # Local AI Multi-Model Training Telemetry Endpoints
    # ========================================================================

    @router.get("/training/status", summary="Local AI Multi-Model Training Telemetry")
    def get_training_status() -> Dict[str, Any]:
        """Return real-time telemetry across all 4 local AI training daemons and Lakehouse."""
        from .training_telemetry_service import TrainingTelemetryService
        return TrainingTelemetryService.get_training_overview()

    # ========================================================================
    # Autonomous Mesh Opportunities & Anomaly Hunter Endpoints
    # ========================================================================

    @router.get("/telemetry/opportunities", summary="Scan Telemetry for Optimization Opportunities")
    def get_telemetry_opportunities() -> Dict[str, Any]:
        """Scans live mesh telemetry across biometrics, network, cloud, and models."""
        from .telemetry_opportunity_engine import TelemetryOpportunityEngine
        return TelemetryOpportunityEngine.scan_opportunities()

    @router.post("/telemetry/opportunities/resolve", summary="Resolve Opportunity via AI Debate")
    def post_telemetry_opportunity_resolve(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ratifies and records a resolution for a detected opportunity under /ai-debate."""
        from .telemetry_opportunity_engine import TelemetryOpportunityEngine
        opp_id = payload.get("opportunity_id", "OPP_01_MOVESENSE_DSP")
        return TelemetryOpportunityEngine.resolve_opportunity_via_debate(opp_id)

    # ========================================================================
    # Neo Monorepo Project App Graph & Live Bicep ECG Endpoints
    # ========================================================================

    @router.get("/graph/topology", summary="Neo Monorepo Project App Graph")
    def get_graph_topology() -> Dict[str, Any]:
        """Return comprehensive node-link topology across TUIs, Web Apps, Notebooks, Mesh, and Storage."""
        from .neo_project_graph_service import NeoProjectGraphService
        return NeoProjectGraphService.get_full_graph()

    @router.get("/biometrics", summary="Live Biometrics State for Dashboard")
    def get_biometrics_state() -> Dict[str, Any]:
        movesense_stream_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/movesense_live_stream.json")
        readiness_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_readiness_live.json")
        
        # Default mock structure
        bio = {
            "movesenseStream": {
                "connected": False,
                "sensorId": "Movesense 261030002013",
                "samplingRateHz": 512,
                "profile": "zone2",
                "batteryPct": 0,
                "ecgSnrDb": 28.5,
                "medicalClass": "Class IIa",
                "firmware": "2.1.0-MED"
            },
            "kamathFilter": {
                "filterName": "Kamath 20% Clinical RR Filter",
                "thresholdPct": 20.0,
                "windowSize": 60,
                "rejectionRatePct": 0.0,
                "isActive": True
            },
            "heartRateBpm": None,
            "rrIntervalsMs": [],
            "rmssdMs": None,
            "dfaAlpha1": None,
            "zone2Status": "AWAITING SENSOR",
            "pttBloodPressure": {
                "systolicMmhg": None,
                "diastolicMmhg": None,
                "pulseTransitTimeMs": 182.4,
                "status": "WAITING"
            },
            "grapplingMap": {
                "activePosition": "Side Control",
                "totalNodes": 31,
                "totalTransitions": 57
            }
        }
        
        try:
            if movesense_stream_path.exists():
                import json
                with open(movesense_stream_path, "r") as f:
                    data = json.load(f)
                    
                if "devices" in data:
                    bio["devices"] = data["devices"]
                else:
                    bio["movesenseStream"]["connected"] = data.get("connected", False)
                    bio["movesenseStream"]["sensorId"] = data.get("device_name", "Movesense")
                    bio["movesenseStream"]["device_address"] = data.get("device_address", "C1DB5043-8F89-88E8-46A3-BBD4ED83FC88")
                    bio["movesenseStream"]["mac"] = data.get("mac", "74:92:BA:11:36:D6")
                    bio["movesenseStream"]["batteryPct"] = data.get("battery_pct", 0)
                    bio["movesenseStream"]["profile"] = data.get("dsp_profile", "zone2")
                    bio["kamathFilter"]["rejectionRatePct"] = data.get("kamath_rejection_rate", 0.0)
                    bio["heartRateBpm"] = data.get("heart_rate_bpm")
                    bio["rrIntervalsMs"] = data.get("rr_intervals_recent", [])
                    bio["rmssdMs"] = data.get("rmssd_ms")
                    bio["dfaAlpha1"] = data.get("dfa_alpha1")
        except Exception:
            pass
            
        try:
            if readiness_path.exists():
                import json
                with open(readiness_path, "r") as f:
                    rdata = json.load(f)
                    
                sensor_t = rdata.get("sensor_telemetry", {})
                if sensor_t:
                    if sensor_t.get("connected") is not None:
                        bio["movesenseStream"]["connected"] = bool(bio["movesenseStream"]["connected"] or sensor_t.get("connected"))
                    if sensor_t.get("device"):
                        bio["movesenseStream"]["sensorId"] = sensor_t["device"]
                    if sensor_t.get("device_address"):
                        bio["movesenseStream"]["device_address"] = sensor_t["device_address"]
                    if sensor_t.get("mac"):
                        bio["movesenseStream"]["mac"] = sensor_t["mac"]
                    elif "mac" not in bio["movesenseStream"]:
                        bio["movesenseStream"]["mac"] = "74:92:BA:11:36:D6"
                    if sensor_t.get("battery_pct") is not None:
                        bio["movesenseStream"]["batteryPct"] = sensor_t["battery_pct"]
                    if bio["heartRateBpm"] is None and sensor_t.get("heart_rate_bpm") is not None:
                        bio["heartRateBpm"] = sensor_t["heart_rate_bpm"]
                    if bio["rmssdMs"] is None and sensor_t.get("rmssd_ms") is not None:
                        bio["rmssdMs"] = sensor_t["rmssd_ms"]
                    if bio["dfaAlpha1"] is None and sensor_t.get("dfa_alpha1") is not None:
                        bio["dfaAlpha1"] = sensor_t["dfa_alpha1"]

                ptt = rdata.get("blood_pressure_ptt", {})
                if ptt.get("systolic_bp_mmhg"):
                    bio["pttBloodPressure"]["systolicMmhg"] = ptt["systolic_bp_mmhg"]
                if ptt.get("diastolic_bp_mmhg"):
                    bio["pttBloodPressure"]["diastolicMmhg"] = ptt["diastolic_bp_mmhg"]
                bio["pttBloodPressure"]["status"] = ptt.get("status", "NOMINAL")
                
                activity = rdata.get("activity_and_workout", {})
                if activity.get("training_zone"):
                    bio["zone2Status"] = activity["training_zone"]
                    
                if "tinyml_trend" in rdata:
                    bio["tinymlTrend"] = rdata["tinyml_trend"]
        except Exception:
            pass
            
        return bio

    @router.post("/biometrics/connect", summary="Connect to Bluetooth Devices")
    def post_biometrics_connect(payload: Dict[str, Any]) -> Dict[str, Any]:
        devices = payload.get("devices", ["Movesense Chest", "Movesense Bicep", "Whoop"])
        try:
            import subprocess
            
            def is_reachable(ip: str) -> bool:
                try:
                    subprocess.run(["ping", "-c", "1", "-W", "1", ip], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except subprocess.CalledProcessError:
                    return False
                    
            target_ip = "100.73.38.87" if is_reachable("100.73.38.87") else "100.114.215.68"

            # Start the Kai Morich app via Shizuku!
            subprocess.Popen([
                "ssh", "-p", "8022", f"u0_a363@{target_ip}", 
                "/data/data/com.termux/files/home/rish -c 'am start -n de.kai_morich.serial_bluetooth_terminal/.MainActivity' 2>&1"
            ])
        except Exception as e:
            pass
            
        return {
            "status": "awaiting_pixel_bridge",
            "devices": devices,
            "instructions": "Due to Android OS sandboxing, bleak does not work natively in Termux. We have automatically launched the Kai Morich Serial Terminal via Shizuku for you to connect to the Movesense!"
        }

    @router.get("/biometrics/ansi", summary="Live ANSI Log")
    def get_biometrics_ansi() -> Dict[str, Any]:
        ansi_file = Path("/tmp/bluetooth_terminal_stream.ansi")
        if ansi_file.exists():
            with open(ansi_file, "r") as f:
                return {"logs": f.read().splitlines()[-50:]}
        return {"logs": []}

    @router.get("/biometrics/movesense/live", summary="Live Bicep ECG Telemetry Stream")
    def get_movesense_bicep_ecg() -> Dict[str, Any]:
        """Return live Bicep ECG telemetry with Kamath 20% clinical filter and Zone 2 heart rate classification."""
        from .neo_project_graph_service import NeoProjectGraphService
        return NeoProjectGraphService.get_live_bicep_ecg()


    class ECGAnalyzeRequest(BaseModel):
        model_id: str = "medgemma"
        prompt: str = "Analyze the following ECG telemetry for arrhythmias, heart rate variability, and clinical insights:"
        data: Optional[Dict[str, Any]] = None

    @router.post("/biometrics/movesense/analyze", summary="Analyze Live ECG Stream using Medical AI Models")
    async def analyze_movesense_ecg(req: ECGAnalyzeRequest) -> Dict[str, Any]:
        """Feed live Movesense ECG telemetry through specialized Medical AI models."""
        import json
        import requests
        import httpx
        from .neo_project_graph_service import NeoProjectGraphService
        
        MODELS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/biomedical")
        
        # If we are running on the Pixel (standalone gym mode) and the heavy models aren't here,
        # proxy the request to the Mac Mini Host (100.119.199.76 or its Tailscale IP)
        if not MODELS_DIR.exists():
            try:
                # The Mac Mini's Tailscale IP is 100.119.199.76 (L1 Mac Host)
                # Call the Mac Mini's canonical port (running on 8005)
                mac_mini_api = "http://100.119.199.76:8005/api/v1/biometrics/movesense/analyze"
                resp = await asyncio.to_thread(requests.post, mac_mini_api, json=req.dict(), timeout=120)
                return resp.json()
            except Exception as e:
                return {
                    "error": "Local models not found on Pixel and Mac Mini is unreachable.",
                    "details": str(e),
                    "status": "error"
                }

        # 40GB OpenBioLLM-70B removed to preserve Rule 3 Mac Mini RAM sanctuary
        MODEL_MAP = {
            "medgemma": MODELS_DIR / "Meditron3-8B.Q4_K_M.gguf",
            "meditron": MODELS_DIR / "meditron-7b.Q4_K_M.gguf",
            "biomistral": MODELS_DIR / "BioMistral-7B.Q4_K_M.gguf",
        }
        
        if req.model_id not in MODEL_MAP:
            return {"error": f"Invalid model_id. Choose from {list(MODEL_MAP.keys())}"}
            
        model_path = MODEL_MAP[req.model_id]
        if not model_path.exists():
            return {"error": f"Model file not found: {model_path.name}"}
            
        ecg_data = req.data if req.data else NeoProjectGraphService.get_live_bicep_ecg()
        ecg_text = json.dumps(ecg_data, indent=2)
        
        full_prompt = f"{req.prompt}\n\n{ecg_text}"

        payload = {
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 512,
            "temperature": 0.2
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("http://127.0.0.1:8090/v1/chat/completions", json=payload, timeout=60.0)
                if resp.status_code == 200:
                    data = resp.json()
                    analysis = data["choices"][0]["message"]["content"].strip()
                else:
                    return {"error": "Invalid response from llama-server"}
                
                # Screen Lens Telemetry hook
                try:
                    await client.post("http://127.0.0.1:3037/telemetry", json={"action": "ecg_analysis", "analysis": analysis}, timeout=2.0)
                except Exception:
                    pass
                    
                return {"analysis": analysis, "model": req.model_id}
        except Exception as e:
            return {"error": f"Failed to connect to llama-server: {e}"}


    @router.post("/graph/sync_vault", summary="Sync Neo Project App Graph to Obsidian Vault")
    def post_graph_sync_vault() -> Dict[str, Any]:
        """Synthesize and write updated graph to Obsidian Vault with Mermaid diagrams and Wikilinks."""
        from .neo_project_graph_service import NeoProjectGraphService
        return NeoProjectGraphService.sync_graph_to_obsidian()

    # ========================================================================
    # Spec Modules Core Endpoints
    # ========================================================================

    @router.get("/apps", summary="List All 12 Spec Modules")
    def list_apps() -> Dict[str, Any]:
        """Return metadata catalog for all registered spec modules."""
        modules = store.list_modules()
        catalog = [mod.get_metadata().model_dump() for mod in modules]
        return {
            "total_modules": len(catalog),
            "modules": catalog,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/apps/summary", summary="Global Spec Modules Summary")
    def get_apps_summary() -> Dict[str, Any]:
        """Return full global status summary across all 12 spec modules."""
        return store.get_global_summary()

    @router.get("/apps/{module_id}", summary="Spec Module Details")
    def get_app_details(module_id: str) -> Dict[str, Any]:
        """Return metadata and current status for a specific module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return {
            "metadata": mod.get_metadata().model_dump(),
            "status": mod.get_status(),
        }

    @router.get("/apps/{module_id}/status", summary="Spec Module Real-Time Status")
    def get_app_status(module_id: str) -> Dict[str, Any]:
        """Return live real-time status of specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return mod.get_status()

    @router.get("/apps/{module_id}/telemetry", summary="Spec Module Telemetry")
    def get_app_telemetry(
        module_id: str,
        limit: int = Query(20, ge=1, le=100, description="Max history records to return"),
    ) -> Dict[str, Any]:
        """Return recent telemetry history or live snapshot for specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        history = store.get_telemetry_history(mod.module_id, limit=limit)
        current_telemetry = mod.collect_telemetry()
        return {
            "module_id": mod.module_id,
            "current": current_telemetry,
            "history_count": len(history),
            "history": history,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/apps/{module_id}/schema", summary="Spec Module Telemetry Schema")
    def get_app_schema(module_id: str) -> Dict[str, Any]:
        """Return telemetry data schema definition for specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return mod.get_telemetry_schema()

    @router.get("/apps/{module_id}/health", summary="Spec Module Health Check")
    def get_app_health(module_id: str) -> Dict[str, Any]:
        """Execute active diagnostic health check on specified module."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        return mod.health_check()

    @router.post("/apps/{module_id}/action", summary="Execute Spec Module Action")
    def post_app_action(module_id: str, request: ModuleActionRequest) -> Dict[str, Any]:
        """Execute an action on specified module with parameters."""
        mod = store.get_module(module_id)
        if not mod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spec module '{module_id}' not found",
            )
        res = mod.execute_action(request.action, request.params)
        return res

    # ========================================================================
    # Network Analysis Pipeline Endpoints
    # ========================================================================
    from .pipeline import get_network_pipeline

    @router.get("/network/metrics", summary="Aggregated 7-Layer Mesh Telemetry")
    def get_network_metrics() -> Dict[str, Any]:
        """Return non-blocking aggregated view of all known mesh nodes."""
        pipeline = get_network_pipeline()
        return pipeline.get_aggregated_metrics()

    @router.get("/network/anomalies", summary="Mesh Network Anomalies Log")
    def get_network_anomalies(
        limit: int = Query(50, ge=1, le=200, description="Max anomalies to return"),
        severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, WARNING, INFO"),
    ) -> Dict[str, Any]:
        """Return recent recorded anomalies across all mesh nodes."""
        pipeline = get_network_pipeline()
        anomalies = pipeline.get_anomalies(limit=limit, severity=severity)
        return {
            "total_anomalies": len(anomalies),
            "severity_filter": severity,
            "anomalies": anomalies,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.post("/network/ingest", summary="Ingest Mesh Telemetry Payload")
    async def post_network_ingest(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronously ingest a telemetry payload for a mesh node."""
        pipeline = get_network_pipeline()
        node_id = payload.get("node_id", "UNKNOWN")
        detected = await pipeline.ingest_payload(node_id, payload)
        return {
            "success": True,
            "node_id": node_id,
            "anomalies_detected": len(detected),
            "anomalies": detected,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.post("/network/obsidian/sync", summary="Trigger Obsidian Vault Telemetry Sync")
    def post_network_obsidian_sync() -> Dict[str, Any]:
        """Trigger Obsidian Vault markdown file synchronization for all nodes."""
        pipeline = get_network_pipeline()
        written = pipeline.sync_vault()
        metrics = pipeline.get_aggregated_metrics()
        anomalies = pipeline.get_anomalies(limit=20)
        daily_path = pipeline.vault_engine.generate_daily_log(metrics, anomalies)
        return {
            "success": True,
            "vault_dir": pipeline.vault_dir,
            "notes_synced": len(written),
            "synced_nodes": list(written.keys()),
            "daily_log_path": daily_path,
            "timestamp": current_utc_time().isoformat(),
        }

    @router.get("/network/buffer/{node_id}", summary="Node Time-Series Buffer")
    def get_network_node_buffer(
        node_id: str,
        limit: int = Query(50, ge=1, le=500, description="Max buffer samples to return"),
    ) -> Dict[str, Any]:
        """Return time-series ring buffer samples and statistics for a specific node."""
        pipeline = get_network_pipeline()
        buf = pipeline.get_node_buffer(node_id)
        if not buf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No buffer found for node '{node_id}'",
            )
        return {
            "node_id": node_id,
            "buffer_size": buf.size(),
            "stats": buf.get_stats(),
            "samples": [
                {"timestamp": t, "rtt_ms": v, "metadata": m}
                for t, v, m in buf.get_recent(limit)
            ],
            "timestamp": current_utc_time().isoformat(),
        }

    # ========================================================================
    # Autonomous Agents & Crons Ecosystem Endpoints
    # ========================================================================
    from .agents import create_agents_router

    agents_router = create_agents_router()
    router.include_router(agents_router)

    # ========================================================================
    # Attach Module-Specific Custom Sub-Routers
    # ========================================================================
    for mod in store.list_modules():
        sub_router = mod.get_routes()
        if sub_router:
            router.include_router(sub_router, prefix="/apps/custom")

    return router


# Module-level default router instance
app_router = create_app_router()
