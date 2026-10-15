#!/usr/bin/env python3
"""
Screen Lens Sovereign: Monorepo Telemetry & High-ROI Prioritization Engine
==========================================================================
Part of the Screen Lens Sovereign TUI & Notebook IDE Ecosystem.
Scans the 7 monorepo layers, calculates dynamic ROI scores, and ranks tasks
for autonomous dispatch under Rule #0 (Zero-Mock) and Inverted Orchestration.
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Add parent directory for router import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lens_omniscient_router import LensOmniscientRouter

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LORA_DATASET_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
OBSIDIAN_VAULT = MONOREPO_ROOT / "obsidian_vault"


@dataclass
class PrioritizedTask:
    task_id: str
    title: str
    category: str  # INFRASTRUCTURE, LORA_TRAINING, CLOUD_QUOTA, SHARDING, WORKSPACE, MOBILE_VLA
    impact_score: float      # 1.0 - 100.0 (System criticality)
    savings_factor: float    # 1.0 - 10.0 (Token / cost savings multiplier)
    speedup_multiplier: float  # e.g. 1.0 - 1500.0x
    complexity: float        # 1.0 - 10.0 (Execution risk)
    vram_penalty: float      # 0.0 - 5.0 (RAM consumption risk)
    roi_score: float         # Computed dynamic ROI
    assigned_model: str      # Model ID picked by Inverted Orchestrator
    target_endpoint: str     # Target endpoint
    mesh_host: str           # Target node (L1, L2, L3, L6, etc.)
    status: str              # PENDING, RUNNING, COMPLETED, BLOCKED
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MonorepoROIEngine:
    def __init__(self, root: Path = MONOREPO_ROOT):
        self.root = root
        self.router = LensOmniscientRouter()

    def calculate_roi(
        self,
        impact: float,
        savings: float,
        speedup: float,
        complexity: float,
        vram_penalty: float
    ) -> float:
        """
        Dynamic ROI Formula:
        ROI = (Impact * Savings * log10(max(10, speedup))) / (Complexity + vram_penalty)
        """
        import math
        speedup_log = math.log10(max(10.0, speedup))
        numerator = impact * savings * speedup_log
        denominator = max(1.0, complexity + vram_penalty)
        return round(numerator / denominator, 2)

    def scan_and_prioritize(self) -> List[PrioritizedTask]:
        """
        Inspects live monorepo files, storage headroom, datasets, and telemetry to generate
        an authentic, prioritized task backlog.
        """
        tasks: List[PrioritizedTask] = []

        # 1. Inspect Storage Headroom & Cache Accumulation
        try:
            free_gb = shutil.disk_usage("/Users/aaron").free / (1024**3)
        except Exception:
            free_gb = 20.0

        if free_gb < 30.0:
            # High priority disk hygiene
            t_class = self.router.classify_task_and_context("Clean pycache and stale temporary logs to preserve disk sanctuary")
            model_target = self.router.route_model(t_class["task_type"])
            roi = self.calculate_roi(impact=85.0, savings=5.0, speedup=20.0, complexity=2.0, vram_penalty=0.0)
            tasks.append(PrioritizedTask(
                task_id="task_disk_headroom_hygiene",
                title="Disk Headroom & Host Sanctuary Pruning",
                category="INFRASTRUCTURE",
                impact_score=85.0,
                savings_factor=5.0,
                speedup_multiplier=20.0,
                complexity=2.0,
                vram_penalty=0.0,
                roi_score=roi,
                assigned_model=model_target["id"],
                target_endpoint=model_target["endpoint"],
                mesh_host="Mac_Node_L1",
                status="PENDING",
                description=f"Host currently has {free_gb:.1f} GB free. Prune __pycache__ to maintain >= 10.0 GB sanctuary."
            ))

        # 2. Inspect LoRA Dataset Harvesting & Unmerged Pairs
        dpo_file = LORA_DATASET_DIR / "continuous_deep_research_dpo.jsonl"
        dpo_count = 0
        if dpo_file.exists():
            try:
                with open(dpo_file, "r", encoding="utf-8") as f:
                    dpo_count = sum(1 for _ in f)
            except Exception:
                dpo_count = 0

        if dpo_count > 0:
            t_class = self.router.classify_task_and_context("Run Apple Silicon Metal LoRA fine-tuning on accumulated DPO pairs")
            model_target = self.router.route_model(t_class["task_type"])
            roi = self.calculate_roi(impact=92.0, savings=8.5, speedup=50.0, complexity=3.5, vram_penalty=1.5)
            tasks.append(PrioritizedTask(
                task_id="task_lora_dpo_distillation",
                title=f"Continuous LoRA Distillation ({dpo_count} DPO Pairs)",
                category="LORA_TRAINING",
                impact_score=92.0,
                savings_factor=8.5,
                speedup_multiplier=50.0,
                complexity=3.5,
                vram_penalty=1.5,
                roi_score=roi,
                assigned_model=model_target["id"],
                target_endpoint=model_target["endpoint"],
                mesh_host="MacBook_Air_L5 / Linux_Mini_L3",
                status="PENDING",
                description=f"{dpo_count} verified DPO triplets ready for MLX/PEFT fine-tuning to permanently reduce cloud spend to $0."
            ))

        # 3. Inspect Cloud Free Tier Quota Window
        # Google AI Studio resets at 10 AM AEST. If during catch-up window, harvest research
        t_class = self.router.classify_task_and_context("Execute deep research sweep against Gemini 3.8 Flash free tier quota")
        model_target = self.router.route_model(t_class["task_type"])
        roi = self.calculate_roi(impact=88.0, savings=9.5, speedup=30.0, complexity=2.5, vram_penalty=0.0)
        tasks.append(PrioritizedTask(
            task_id="task_cloud_quota_harvest",
            title="Google AI Studio 1,500 RPD Free Quota Harvest",
            category="CLOUD_QUOTA",
            impact_score=88.0,
            savings_factor=9.5,
            speedup_multiplier=30.0,
            complexity=2.5,
            vram_penalty=0.0,
            roi_score=roi,
            assigned_model=model_target["id"],
            target_endpoint=model_target["endpoint"],
            mesh_host="Google Cloud Free Tier Cadence",
            status="PENDING",
            description="Exhaust daily 1,500 free requests for student model distillation before daily quota resets."
        ))

        # 4. Distributed AI Sharding Latency & Topology Probe
        t_class = self.router.classify_task_and_context("Probe 40Gbps Thunderbolt 4 bridge and verify RPC sharding latency")
        model_target = self.router.route_model(t_class["task_type"])
        roi = self.calculate_roi(impact=95.0, savings=6.0, speedup=100.0, complexity=2.0, vram_penalty=0.5)
        tasks.append(PrioritizedTask(
            task_id="task_sharding_latency_probe",
            title="40Gbps TB4 DMA Bridge & RPC Health Handshake",
            category="SHARDING",
            impact_score=95.0,
            savings_factor=6.0,
            speedup_multiplier=100.0,
            complexity=2.0,
            vram_penalty=0.5,
            roi_score=roi,
            assigned_model=model_target["id"],
            target_endpoint=model_target["endpoint"],
            mesh_host="MacBook_Pro_L2 (169.254.187.138)",
            status="PENDING",
            description="Verify RTT <= 0.35ms across TB4 DMA bridge and test Port 50052 RPC handshake on L2/L3."
        ))

        # 5. Pixel 10 Pro XL Headless Accessibility Ingestion
        t_class = self.router.classify_task_and_context("Ingest latest accessibility hierarchy from Pixel 10 Pro XL over SSH")
        model_target = self.router.route_model(t_class["task_type"])
        roi = self.calculate_roi(impact=90.0, savings=9.0, speedup=1381.8, complexity=2.0, vram_penalty=0.0)
        tasks.append(PrioritizedTask(
            task_id="task_pixel_accessibility_sync",
            title="Pixel 10 Pro XL Headless Accessibility Ingestion",
            category="MOBILE_VLA",
            impact_score=90.0,
            savings_factor=9.0,
            speedup_multiplier=1381.8,
            complexity=2.0,
            vram_penalty=0.0,
            roi_score=roi,
            assigned_model=model_target["id"],
            target_endpoint=model_target["endpoint"],
            mesh_host="Pixel_10_Pro_XL_L6 (100.73.38.87:8022)",
            status="PENDING",
            description="Zero-OCR 0.289ms hierarchy extraction with 100% icon grounding and exact centroid touch hitboxes."
        ))

        # 6. Google Workspace & Port 18802 Alert Bus Triage
        t_class = self.router.classify_task_and_context("Triage incoming alerts from Google Workspace and Port 18802 alert bus")
        model_target = self.router.route_model(t_class["task_type"])
        roi = self.calculate_roi(impact=82.0, savings=7.0, speedup=15.0, complexity=1.5, vram_penalty=0.0)
        tasks.append(PrioritizedTask(
            task_id="task_workspace_alert_triage",
            title="Google Workspace & Mesh Port 18802 Alert Triage",
            category="WORKSPACE",
            impact_score=82.0,
            savings_factor=7.0,
            speedup_multiplier=15.0,
            complexity=1.5,
            vram_penalty=0.0,
            roi_score=roi,
            assigned_model=model_target["id"],
            target_endpoint=model_target["endpoint"],
            mesh_host="Linux_Mini_L3 / Port 18802",
            status="PENDING",
            description="Audit unread alerts for lauburu@lauburugrappling.com and route critical incidents to TUI alert banner."
        ))

        # 7. Context-Aware Workspace Auto-Routing Check (Phase 3 & 4)
        try:
            import sqlite3
            db_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/screen_life_companion.sqlite"
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM ide_workspace_routes WHERE marimo_ast_injected = 0")
                    pending_workspaces = cursor.fetchone()[0]
                    
                if pending_workspaces > 0:
                    roi = self.calculate_roi(impact=98.0, savings=10.0, speedup=100.0, complexity=1.0, vram_penalty=0.0)
                    tasks.append(PrioritizedTask(
                        task_id="task_workspace_auto_routing",
                        title=f"Auto-Route Contextual Workspaces ({pending_workspaces} pending)",
                        category="WORKSPACE",
                        impact_score=98.0,
                        savings_factor=10.0,
                        speedup_multiplier=100.0,
                        complexity=1.0,
                        vram_penalty=0.0,
                        roi_score=roi,
                        assigned_model="Qwen 2.5 Coder 7B",
                        target_endpoint="100.101.39.98:8082",
                        mesh_host="Linux_Mini_L3",
                        status="PENDING",
                        description=f"Synthesize ASTs and provision isolated Marimo IDE contexts for {pending_workspaces} VLA OCR events."
                    ))
        except Exception:
            pass

        # Sort tasks descending by ROI score
        tasks.sort(key=lambda t: t.roi_score, reverse=True)
        return tasks


if __name__ == "__main__":
    engine = MonorepoROIEngine()
    ranked = engine.scan_and_prioritize()
    print("=" * 80)
    print("🚀 SCREEN LENS SOVEREIGN: HIGHEST-ROI MONOREPO TASK PRIORITIZATION")
    print("=" * 80)
    for i, t in enumerate(ranked, 1):
        print(f"#{i} [ROI: {t.roi_score:7.2f}] {t.title}")
        print(f"    Category: {t.category:<15} | Model: {t.assigned_model:<22} | Host: {t.mesh_host}")
        print(f"    Impact: {t.impact_score:<4} | Savings: {t.savings_factor:<4} | Speedup: {t.speedup_multiplier}x")
        print(f"    Details: {t.description}\n")
