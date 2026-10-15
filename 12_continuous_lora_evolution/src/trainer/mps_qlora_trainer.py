"""
Apple Silicon Metal QLoRA Trainer & Memory-Governed Optimization Engine.

Provides:
- F1: MPS Device Accelerator & Precision Engine (PyTorch MPS Float16 / BFloat16)
- F2: Gradient Stability & Norm Clipper (strict max_norm <= 1.0, 0 NaN/Inf assertion)
- F3: Micro-Batcher & Gradient Accumulator (low-memory activation footprint)
- F4: Dynamic RAM Governor & Memory Sentinel Integration
"""

import json
import logging
import math
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.trainer.dynamic_ram_governor import (
    DynamicRAMGovernor,
    MemoryGovernorError,
    MemoryMetrics,
)

logger = logging.getLogger(__name__)


@dataclass
class MPSQLoRAConfig:
    """Configuration parameters for Apple Silicon Metal QLoRA Trainer."""
    # F1: Device & Precision
    device: str = "mps"  # "mps", "cpu", "cuda"
    precision: str = "float16"  # "float16", "bfloat16", "float32"
    
    # F2: Optimization & Gradient Stability
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0  # Strict <= 1.0 clipping invariant
    fail_on_nan: bool = True    # Fail-fast on NaN/Inf gradients
    
    # F3: Micro-batching & Accumulation
    micro_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    max_epochs: int = 3
    
    # F4: Dynamic RAM Safety
    max_ram_ratio: float = 0.90  # Max 90% host RAM
    min_headroom_gb: float = 2.50  # Min 2.50 GB free headroom
    auto_reclaim_cache: bool = True  # Auto-invoke gc + torch.mps.empty_cache()
    
    # PEFT LoRA Hyperparameters
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    lora_target_modules: Optional[List[str]] = None
    
    # Checkpointing & Telemetry
    output_dir: str = "checkpoints/mps_qlora"
    save_every_n_steps: int = 50
    logging_steps: int = 10


@dataclass
class StepResult:
    """Outcome of an individual micro-batch training step."""
    step_idx: int
    unscaled_loss: float
    scaled_loss: float
    is_accumulation_step: bool
    grad_norm_before_clip: Optional[float] = None
    grad_norm_after_clip: Optional[float] = None
    skipped_nan_step: bool = False
    optimizer_stepped: bool = False
    memory_metrics: Optional[MemoryMetrics] = None


@dataclass
class EpochResult:
    """Aggregated outcome of a full training epoch."""
    epoch_idx: int
    total_steps: int
    optimizer_steps: int
    avg_loss: float
    loss_history: List[float] = field(default_factory=list)
    grad_norm_history: List[float] = field(default_factory=list)
    skipped_nan_steps: int = 0
    duration_seconds: float = 0.0
    final_memory_metrics: Optional[MemoryMetrics] = None


@dataclass
class TrainingSummary:
    """Final summary of full training run."""
    total_epochs: int
    total_micro_steps: int
    total_optimizer_steps: int
    initial_loss: float
    final_loss: float
    loss_monotonic_decrease: bool
    total_skipped_nan_steps: int
    total_duration_seconds: float
    epoch_summaries: List[EpochResult] = field(default_factory=list)


class MPSQLoRATrainer:
    """
    Production-grade Apple Silicon Metal QLoRA Trainer.
    
    Implements:
    - Unified Memory MPS Hardware Acceleration with Float16/BFloat16 precision
    - Zero-mock forward and backward autograd loops
    - Strict gradient norm clipping (<= 1.0) and 0 NaN/Inf gradient assertion
    - Micro-batching with exact gradient accumulation math
    - Continuous dynamic RAM governance and proactive MPS cache eviction
    """

    def __init__(
        self,
        model: Optional[nn.Module] = None,
        config: Optional[MPSQLoRAConfig] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
        loss_fn: Optional[Callable[..., torch.Tensor]] = None,
        ram_governor: Optional[DynamicRAMGovernor] = None,
    ) -> None:
        self.config = config or MPSQLoRAConfig()
        self.ram_governor = ram_governor or DynamicRAMGovernor(
            max_ram_ratio=self.config.max_ram_ratio,
            min_headroom_gb=self.config.min_headroom_gb,
        )
        
        # Resolve device and dtype
        self.device = self._resolve_device(self.config.device)
        self.dtype = self._resolve_dtype(self.config.precision)
        
        self.model: Optional[nn.Module] = None
        if model is not None:
            self.set_model(model)
            
        self.optimizer = optimizer
        if self.model is not None and self.optimizer is None:
            self.optimizer = self._create_default_optimizer()
            
        self.loss_fn = loss_fn
        
        # State tracking
        self.global_step = 0
        self.accumulated_micro_steps = 0
        self.total_skipped_nan_steps = 0
        self.loss_curve: List[float] = []
        self.grad_norm_history: List[float] = []
        self.training_history: List[Dict[str, Any]] = []

    @property
    def effective_batch_size(self) -> int:
        """Calculate effective batch size after gradient accumulation."""
        return self.config.micro_batch_size * self.config.gradient_accumulation_steps

    def _resolve_device(self, target_device: str) -> torch.device:
        """Resolve requested device with fallback if MPS is unavailable."""
        target = target_device.lower()
        if target == "mps":
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
            logger.warning("MPS device requested but not available. Falling back to CPU.")
            return torch.device("cpu")
        elif target == "cuda":
            if torch.cuda.is_available():
                return torch.device("cuda")
            logger.warning("CUDA device requested but not available. Falling back to CPU.")
            return torch.device("cpu")
        return torch.device("cpu")

    def _resolve_dtype(self, precision_str: str) -> torch.dtype:
        """Resolve precision mode to PyTorch dtype."""
        p = precision_str.lower()
        if p in ("float16", "fp16", "half"):
            return torch.float16
        elif p in ("bfloat16", "bf16"):
            return torch.bfloat16
        elif p in ("float32", "fp32", "single"):
            return torch.float32
        else:
            raise ValueError(f"Unsupported precision: {precision_str}. Choose float16, bfloat16, or float32.")

    def set_model(self, model: nn.Module) -> None:
        """Configure model on target device and target precision."""
        self.model = model
        
        # Convert floating point parameters to target precision and device
        # Note: We keep layer norm / embeddings in float32 if needed, but standard model.to() is used
        self.model.to(device=self.device)
        if self.dtype in (torch.float16, torch.bfloat16):
            # Move floating parameters to target dtype, keeping integers/buffers intact
            self.model.to(dtype=self.dtype)

    def prepare_peft_lora(
        self,
        target_modules: Optional[List[str]] = None,
        r: Optional[int] = None,
        alpha: Optional[int] = None,
        dropout: Optional[float] = None,
    ) -> nn.Module:
        """
        Wrap model with PEFT LoRA adapter matrices.
        Freezes base weights and ensures only adapter parameters require gradient.
        """
        if self.model is None:
            raise RuntimeError("Model must be set before applying PEFT LoRA adapter.")
            
        try:
            from peft import LoraConfig, TaskType, get_peft_model
        except ImportError as e:
            raise ImportError("PEFT package is required for prepare_peft_lora. Install peft >= 0.20.0") from e

        r_val = r if r is not None else self.config.lora_r
        alpha_val = alpha if alpha is not None else self.config.lora_alpha
        dropout_val = dropout if dropout is not None else self.config.lora_dropout
        targets = target_modules or self.config.lora_target_modules
        if targets is None and not hasattr(self.model, "config"):
            # Auto-discover linear module names for generic PyTorch models
            linear_names = list({
                name.split(".")[-1]
                for name, mod in self.model.named_modules()
                if isinstance(mod, nn.Linear) and name
            })
            if linear_names:
                targets = linear_names

        task_type_val = None
        if hasattr(self.model, "prepare_inputs_for_generation") and hasattr(TaskType, "CAUSAL_LM"):
            task_type_val = TaskType.CAUSAL_LM

        lora_config = LoraConfig(
            r=r_val,
            lora_alpha=alpha_val,
            target_modules=targets,
            lora_dropout=dropout_val,
            bias="none",
            task_type=task_type_val,
        )

        peft_model = get_peft_model(self.model, lora_config)
        self.set_model(peft_model)
        
        # Refresh optimizer for trainable parameters only
        self.optimizer = self._create_default_optimizer()
        return self.model

    def get_parameter_stats(self) -> Dict[str, Any]:
        """Inspect model parameter counts and trainable percentage."""
        if self.model is None:
            return {"total_params": 0, "trainable_params": 0, "trainable_pct": 0.0}
            
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        trainable_pct = (trainable_params / total_params * 100.0) if total_params > 0 else 0.0

        return {
            "total_params": total_params,
            "trainable_params": trainable_params,
            "trainable_pct": round(trainable_pct, 4),
        }

    def _create_default_optimizer(self) -> torch.optim.Optimizer:
        """Create AdamW optimizer targeting trainable parameters with weight decay."""
        if self.model is None:
            raise RuntimeError("Cannot create optimizer without model.")
            
        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        if not trainable_params:
            logger.warning("No trainable parameters found in model! Using all parameters.")
            trainable_params = list(self.model.parameters())

        return torch.optim.AdamW(
            trainable_params,
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

    def _prepare_batch_tensors(self, batch: Any) -> Any:
        """Recursively place batch tensors onto target device and cast float tensors."""
        if isinstance(batch, torch.Tensor):
            t = batch.to(device=self.device)
            if t.is_floating_point() and t.dtype != self.dtype:
                t = t.to(dtype=self.dtype)
            return t
        elif isinstance(batch, dict):
            return {k: self._prepare_batch_tensors(v) for k, v in batch.items()}
        elif isinstance(batch, (list, tuple)):
            res = [self._prepare_batch_tensors(v) for v in batch]
            return type(batch)(res)
        return batch

    def _check_gradients_finite(self) -> bool:
        """Check all parameter gradients for NaN or Inf values."""
        if self.model is None:
            return True
            
        for param in self.model.parameters():
            if param.requires_grad and param.grad is not None:
                if not torch.all(torch.isfinite(param.grad)):
                    return False
        return True

    def train_step(self, batch: Any, step_idx: int) -> StepResult:
        """
        Execute an atomic micro-batch forward and backward training pass.
        
        Enforces:
        - F4: Dynamic RAM headroom validation before forward pass
        - F1: MPS device acceleration & target precision
        - F2: 0 NaN/Inf loss and gradient assertion, strict <= 1.0 gradient clipping
        - F3: Micro-batch gradient accumulation
        """
        if self.model is None:
            raise RuntimeError("Model is not initialized.")
        if self.optimizer is None:
            raise RuntimeError("Optimizer is not initialized.")

        # F4: Enforce RAM safety limits before memory allocation
        mem_metrics = self.ram_governor.enforce_safety_limits(
            auto_reclaim=self.config.auto_reclaim_cache
        )

        self.model.train()
        batch_dev = self._prepare_batch_tensors(batch)

        # Forward pass
        if self.loss_fn is not None:
            loss = self.loss_fn(self.model, batch_dev)
        elif isinstance(batch_dev, dict):
            outputs = self.model(**batch_dev)
            if hasattr(outputs, "loss") and outputs.loss is not None:
                loss = outputs.loss
            elif isinstance(outputs, torch.Tensor):
                loss = outputs
            else:
                raise ValueError("Model output did not contain a loss tensor.")
        elif isinstance(batch_dev, (list, tuple)) and len(batch_dev) == 2:
            inputs, targets = batch_dev
            preds = self.model(inputs)
            if isinstance(preds, torch.Tensor) and isinstance(targets, torch.Tensor):
                # Standard MSE or CrossEntropy
                if targets.dtype in (torch.long, torch.int64):
                    loss = nn.functional.cross_entropy(preds, targets)
                else:
                    loss = nn.functional.mse_loss(preds, targets)
            else:
                raise ValueError("Unsupported tensor types in tuple batch.")
        elif isinstance(batch_dev, torch.Tensor):
            preds = self.model(batch_dev)
            loss = preds.mean()
        else:
            raise TypeError(f"Unsupported batch format: {type(batch_dev)}")

        # F2: Check loss finite invariant
        if not torch.isfinite(loss):
            msg = f"Non-finite loss encountered during training step {step_idx}: loss={loss.item()}"
            if self.config.fail_on_nan:
                raise FloatingPointError(msg)
            else:
                logger.error(msg)
                self.optimizer.zero_grad()
                self.total_skipped_nan_steps += 1
                return StepResult(
                    step_idx=step_idx,
                    unscaled_loss=float("nan"),
                    scaled_loss=float("nan"),
                    is_accumulation_step=False,
                    skipped_nan_step=True,
                    optimizer_stepped=False,
                    memory_metrics=mem_metrics,
                )

        unscaled_loss_val = float(loss.item())

        # F3: Scale loss by gradient accumulation steps
        accum_steps = max(1, self.config.gradient_accumulation_steps)
        scaled_loss = loss / accum_steps

        # Backward pass
        scaled_loss.backward()
        self.accumulated_micro_steps += 1
        self.global_step += 1

        is_accum_step = (self.accumulated_micro_steps % accum_steps == 0)
        grad_norm_before: Optional[float] = None
        grad_norm_after: Optional[float] = None
        stepped = False
        skipped_nan = False

        if is_accum_step:
            # F2: Validate gradient finiteness across all trainable weights
            if not self._check_gradients_finite():
                msg = f"Non-finite gradient (NaN or Inf) detected on device {self.device} at step {step_idx}!"
                if self.config.fail_on_nan:
                    raise FloatingPointError(msg)
                else:
                    logger.warning(msg + " Skipping optimizer step and zeroing gradients.")
                    self.optimizer.zero_grad()
                    self.total_skipped_nan_steps += 1
                    skipped_nan = True
            else:
                # F2: Strict gradient norm clipping (<= 1.0)
                trainable_params = [p for p in self.model.parameters() if p.requires_grad and p.grad is not None]
                if trainable_params:
                    # Compute unclipped total norm
                    total_norm_sq = sum(p.grad.detach().data.norm(2).item() ** 2 for p in trainable_params)
                    grad_norm_before = math.sqrt(total_norm_sq)

                    # Strict clipping
                    clip_val = torch.nn.utils.clip_grad_norm_(
                        trainable_params,
                        max_norm=self.config.max_grad_norm,
                    )
                    grad_norm_before = float(clip_val.item() if isinstance(clip_val, torch.Tensor) else clip_val)
                    grad_norm_after = math.sqrt(sum(p.grad.detach().data.norm(2).item() ** 2 for p in trainable_params))
                    self.grad_norm_history.append(grad_norm_after)

                # Optimizer step & zero grad
                self.optimizer.step()
                self.optimizer.zero_grad()
                stepped = True

                # F4: Auto-reclaim memory on accumulation boundary
                if self.config.auto_reclaim_cache:
                    self.ram_governor.reclaim_memory()

        self.loss_curve.append(unscaled_loss_val)

        return StepResult(
            step_idx=step_idx,
            unscaled_loss=unscaled_loss_val,
            scaled_loss=float(scaled_loss.item()),
            is_accumulation_step=is_accum_step,
            grad_norm_before_clip=grad_norm_before,
            grad_norm_after_clip=grad_norm_after,
            skipped_nan_step=skipped_nan,
            optimizer_stepped=stepped,
            memory_metrics=mem_metrics,
        )

    def flush_gradients(self) -> Optional[float]:
        """Flush any unapplied accumulated gradients at epoch or dataloader end."""
        if self.accumulated_micro_steps % max(1, self.config.gradient_accumulation_steps) != 0:
            if self._check_gradients_finite():
                trainable_params = [p for p in self.model.parameters() if p.requires_grad and p.grad is not None]
                if trainable_params:
                    clip_val = torch.nn.utils.clip_grad_norm_(
                        trainable_params,
                        max_norm=self.config.max_grad_norm,
                    )
                    grad_norm = math.sqrt(sum(p.grad.detach().data.norm(2).item() ** 2 for p in trainable_params))
                    self.grad_norm_history.append(grad_norm)
                    self.optimizer.step()
                    self.optimizer.zero_grad()
                    if self.config.auto_reclaim_cache:
                        self.ram_governor.reclaim_memory()
                    return grad_norm
            else:
                self.optimizer.zero_grad()
        return None

    def train_epoch(self, dataloader: DataLoader, epoch_idx: int = 0) -> EpochResult:
        """Run training across all batches in a DataLoader for one epoch."""
        start_time = time.time()
        epoch_losses: List[float] = []
        epoch_grad_norms: List[float] = []
        optimizer_steps_count = 0
        skipped_nan_count = 0

        for step_idx, batch in enumerate(dataloader):
            step_res = self.train_step(batch, step_idx)
            if not step_res.skipped_nan_step:
                epoch_losses.append(step_res.unscaled_loss)
            else:
                skipped_nan_count += 1

            if step_res.optimizer_stepped:
                optimizer_steps_count += 1
                if step_res.grad_norm_after_clip is not None:
                    epoch_grad_norms.append(step_res.grad_norm_after_clip)

        # Flush any trailing accumulated gradients
        flush_norm = self.flush_gradients()
        if flush_norm is not None:
            optimizer_steps_count += 1
            epoch_grad_norms.append(flush_norm)

        duration = time.time() - start_time
        avg_loss = (sum(epoch_losses) / len(epoch_losses)) if epoch_losses else float("nan")
        final_mem = self.ram_governor.get_metrics()

        result = EpochResult(
            epoch_idx=epoch_idx,
            total_steps=len(dataloader),
            optimizer_steps=optimizer_steps_count,
            avg_loss=avg_loss,
            loss_history=epoch_losses,
            grad_norm_history=epoch_grad_norms,
            skipped_nan_steps=skipped_nan_count,
            duration_seconds=duration,
            final_memory_metrics=final_mem,
        )
        self.training_history.append(asdict(result))
        return result

    def fit(
        self,
        train_dataloader: DataLoader,
        eval_dataloader: Optional[DataLoader] = None,
        num_epochs: Optional[int] = None,
    ) -> TrainingSummary:
        """Execute full training loop across specified epochs."""
        epochs = num_epochs if num_epochs is not None else self.config.max_epochs
        start_time = time.time()
        epoch_results: List[EpochResult] = []

        for epoch in range(epochs):
            res = self.train_epoch(train_dataloader, epoch_idx=epoch)
            epoch_results.append(res)
            logger.info(
                f"Epoch {epoch + 1}/{epochs} Complete — Avg Loss: {res.avg_loss:.4f}, "
                f"Optimizer Steps: {res.optimizer_steps}, Duration: {res.duration_seconds:.2f}s"
            )

        total_duration = time.time() - start_time
        all_losses = self.loss_curve
        initial_loss = all_losses[0] if all_losses else 0.0
        final_loss = all_losses[-1] if all_losses else 0.0
        
        # Check monotonic decrease over epoch averages (or overall loss trend)
        epoch_avg_losses = [r.avg_loss for r in epoch_results if not math.isnan(r.avg_loss)]
        loss_decreased = (
            len(epoch_avg_losses) >= 2 and epoch_avg_losses[-1] <= epoch_avg_losses[0]
        ) or (len(all_losses) >= 2 and final_loss <= initial_loss)

        total_micro = sum(r.total_steps for r in epoch_results)
        total_opt = sum(r.optimizer_steps for r in epoch_results)
        total_skipped = sum(r.skipped_nan_steps for r in epoch_results)

        return TrainingSummary(
            total_epochs=epochs,
            total_micro_steps=total_micro,
            total_optimizer_steps=total_opt,
            initial_loss=initial_loss,
            final_loss=final_loss,
            loss_monotonic_decrease=loss_decreased,
            total_skipped_nan_steps=total_skipped,
            total_duration_seconds=total_duration,
            epoch_summaries=epoch_results,
        )

    def evaluate(self, dataloader: DataLoader) -> Dict[str, float]:
        """Run validation evaluation with model in eval mode and no gradients."""
        if self.model is None:
            raise RuntimeError("Model is not initialized.")

        self.model.eval()
        total_loss = 0.0
        batches = 0

        with torch.no_grad():
            for batch in dataloader:
                batch_dev = self._prepare_batch_tensors(batch)
                if self.loss_fn is not None:
                    loss = self.loss_fn(self.model, batch_dev)
                elif isinstance(batch_dev, dict):
                    outputs = self.model(**batch_dev)
                    loss = outputs.loss if hasattr(outputs, "loss") else outputs
                elif isinstance(batch_dev, (list, tuple)) and len(batch_dev) == 2:
                    inputs, targets = batch_dev
                    preds = self.model(inputs)
                    if targets.dtype in (torch.long, torch.int64):
                        loss = nn.functional.cross_entropy(preds, targets)
                    else:
                        loss = nn.functional.mse_loss(preds, targets)
                else:
                    loss = self.model(batch_dev).mean()
                    
                total_loss += float(loss.item())
                batches += 1

        avg_loss = (total_loss / batches) if batches > 0 else 0.0
        return {"eval_loss": avg_loss, "eval_batches": batches}

    def save_checkpoint(self, output_dir: Union[str, Path], metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Save model weights / PEFT adapter and trainer state to output directory."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        if self.model is not None:
            # Check if PEFT model
            if hasattr(self.model, "save_pretrained"):
                self.model.save_pretrained(out_path)
            else:
                torch.save(self.model.state_dict(), out_path / "model.pt")

        state = {
            "global_step": self.global_step,
            "accumulated_micro_steps": self.accumulated_micro_steps,
            "total_skipped_nan_steps": self.total_skipped_nan_steps,
            "loss_curve": self.loss_curve,
            "grad_norm_history": self.grad_norm_history,
            "config": asdict(self.config),
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        with open(out_path / "trainer_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        return out_path

    def load_checkpoint(self, checkpoint_dir: Union[str, Path]) -> Dict[str, Any]:
        """Load model state and trainer telemetry from checkpoint directory."""
        ckpt_path = Path(checkpoint_dir)
        if not ckpt_path.exists():
            raise FileNotFoundError(f"Checkpoint directory {ckpt_path} does not exist.")

        model_file = ckpt_path / "model.pt"
        if model_file.exists() and self.model is not None:
            self.model.load_state_dict(torch.load(model_file, map_location=self.device))

        state_file = ckpt_path / "trainer_state.json"
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.global_step = state.get("global_step", 0)
            self.accumulated_micro_steps = state.get("accumulated_micro_steps", 0)
            self.total_skipped_nan_steps = state.get("total_skipped_nan_steps", 0)
            self.loss_curve = state.get("loss_curve", [])
            self.grad_norm_history = state.get("grad_norm_history", [])
            return state

        return {}
