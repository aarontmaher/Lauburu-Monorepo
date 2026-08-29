"""
Qwen Math Trend Optimizer Engine & Textual Application.
=======================================================
Subsystem: 01_apps/operator_and_dev/qwen_math_trend_optimizer/presentation/optimizer.py
"""

import sys
import time
from typing import Optional, Dict, Any, List

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.text import Text

from ..core.config import MathOptimizerConfig
from ..models.latency_proofs import compute_inverse_variance_weights
from ..models.ram_headroom import compute_ram_safety_headroom
from ..models.loss_trajectory import compute_loss_trajectory, compute_optimal_learning_rate
from ..models.cardiac_coherence import compute_cardiac_coherence
from .dataset_logger import LoraDatasetLogger

class AutonomousMathTrendOptimizer:
    """Analytical governor calculating closed-form proofs and telemetry trends."""

    def __init__(self, config: Optional[MathOptimizerConfig] = None):
        self.config = config or MathOptimizerConfig()
        self.logger = LoraDatasetLogger(config=self.config)
        self.step_count = 0

    def compute_loss_trajectory(self, steps: Optional[List[int]] = None) -> Dict[str, float]:
        forecast = compute_loss_trajectory(steps)
        return forecast.step_samples

    def compute_optimal_learning_rate(self, batch_size: int = 2, grad_accum: int = 1) -> float:
        return compute_optimal_learning_rate(batch_size, grad_accum)

    def compute_ram_headroom(self, **kwargs) -> Dict[str, Any]:
        proof = compute_ram_safety_headroom(**kwargs)
        return {
            "host_physical_ram_gb": proof.host_physical_ram_gb,
            "governor_ceiling_gb": proof.governor_ceiling_gb,
            "base_model_vram_gb": proof.base_model_vram_gb,
            "kv_cache_vram_gb": proof.kv_cache_vram_gb,
            "activation_vram_gb": proof.activation_vram_gb,
            "total_active_vram_gb": proof.total_active_vram_gb,
            "ram_headroom_gb": proof.ram_headroom_gb,
            "is_safe": proof.is_safe,
            "ram_safety_status": proof.status,
            "equation": proof.equation
        }

    def evaluate_all(self) -> Dict[str, Any]:
        self.step_count += 1
        latency_proofs = compute_inverse_variance_weights(tb4_rtt=0.27, wg_rtt=1.85, wifi_rtt=4.20)
        ram_proof = compute_ram_safety_headroom()
        loss_forecast = compute_loss_trajectory()
        coherence = compute_cardiac_coherence(hr_bpm=72.0, rmssd_ms=48.0)

        summary = {
            "step": self.step_count,
            "tb4_weight": latency_proofs[0].inverse_variance_weight,
            "ram_headroom_gb": ram_proof.ram_headroom_gb,
            "loss_1000": loss_forecast.step_samples.get("step_1000"),
            "optimal_lr": loss_forecast.optimal_learning_rate,
            "cardiac_coherence": coherence.coherence_ratio
        }
        self.logger.log_optimization_step(summary)

        return {
            "latency_proofs": latency_proofs,
            "ram_proof": ram_proof,
            "loss_forecast": loss_forecast,
            "coherence": coherence,
            "summary": summary
        }

class QwenMathOptimizerApp(App):
    """Textual TUI for Standalone Qwen Math Trend Optimizer."""

    TITLE = "🧮 QWEN MATH TELEMETRY & TREND OPTIMIZER"
    SUB_TITLE = "Closed-Form Latency Proofs • RAM Headroom Governor • 24/7 LoRA SFT/DPO"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #top-bar {
        height: 3;
        background: #0b111c;
        border-bottom: solid #1e293b;
        align: center middle;
    }
    #main-container {
        height: 1fr;
        margin: 1 1;
    }
    .math-box {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1 2;
    }
    #footer-bar {
        height: 3;
        background: #0b111c;
        border-top: solid #1e293b;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "recompute", "Recompute Proofs"),
    ]

    def __init__(self):
        super().__init__()
        self.optimizer = AutonomousMathTrendOptimizer()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-bar"):
            yield Static("🧮 Autonomous Mathematical Proofs & Continuous Trend Optimization", id="header-text")

        with Horizontal(id="main-container"):
            yield Static(id="proofs-box", classes="math-box")
            yield Static(id="ram-loss-box", classes="math-box")

        with Horizontal(id="footer-bar"):
            yield Static("⚡ Press [r] Recompute Proofs • [q] Quit", id="status-text")
        yield Footer()

    def on_mount(self) -> None:
        self.update_view()
        self.set_interval(1.0, self.update_view)

    def update_view(self) -> None:
        data = self.optimizer.evaluate_all()
        
        # Left Box: Latency & Coherence
        t_left = Text()
        t_left.append("⚡ MULTI-TRANSPORT INVERSE-VARIANCE WEIGHTS\n", style="bold cyan")
        t_left.append("Formula: w_i = (1 / RTT_i^2) / Σ(1 / RTT_j^2)\n\n", style="dim")
        for lp in data["latency_proofs"]:
            primary_tag = " [PRIMARY OPTIMAL]" if lp.is_optimal_primary else ""
            t_left.append(f"• {lp.transport_name}: RTT={lp.rtt_ms}ms -> Weight={lp.inverse_variance_weight*100:.1f}%{primary_tag}\n", style="white")

        t_left.append("\n💓 CARDIAC COHERENCE & RSA SPECTRAL PROOF\n", style="bold magenta")
        coh = data["coherence"]
        t_left.append(f"• Baseline HR: {coh.hr_bpm} BPM | RMSSD: {coh.rmssd_ms} ms\n", style="white")
        t_left.append(f"• Coherence Ratio: {coh.coherence_ratio:.3f} | RSA Synchrony: {coh.rsa_synchrony:.3f}\n", style="bold green")
        t_left.append(f"• Zone 2 Metabolic Optimal: {'YES' if coh.is_zone2_optimal else 'NO'}", style="bold yellow")
        self.query_one("#proofs-box", Static).update(t_left)

        # Right Box: RAM & Loss Trajectory
        t_right = Text()
        t_right.append("🧠 RAM HEADROOM GOVERNOR (M4 PRO 24.0GB CEILING)\n", style="bold green")
        rp = data["ram_proof"]
        t_right.append(f"• {rp.equation}\n", style="yellow")
        t_right.append(f"• Status: {rp.status}\n\n", style="bold cyan")

        t_right.append("📉 LOSS TRAJECTORY & LEARNING RATE SCALING\n", style="bold blue")
        lf = data["loss_forecast"]
        t_right.append(f"• Formula: {lf.formula}\n", style="dim")
        t_right.append(f"• Optimal Learning Rate η: {lf.optimal_learning_rate}\n", style="bold green")
        for step, loss in list(lf.step_samples.items())[:3]:
            t_right.append(f"  - {step}: L={loss:.4f}\n", style="white")
        t_right.append("• 24/7 LoRA SFT/DPO Dataset: LOGGING ACTIVE", style="bold green")
        self.query_one("#ram-loss-box", Static).update(t_right)

    def action_recompute(self) -> None:
        self.update_view()

def run_optimizer():
    """Runs the Qwen Math Trend Optimizer Textual TUI Application."""
    app = QwenMathOptimizerApp()
    app.run()

if __name__ == "__main__":
    run_optimizer()
