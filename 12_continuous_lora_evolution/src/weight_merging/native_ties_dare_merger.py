"""
Native PyTorch In-Memory TIES/DARE/SLERP Tensor Merger (Feature F13).
Provides pure in-memory delta weight merging with zero external binary dependency.
Supports TIES (Trimming, Electing Signs, Disjoint Merge), DARE (Drop And REscale),
SLERP (Spherical Linear Interpolation), and Linear Task Arithmetic across Float16,
BFloat16, and Float32 precision tensors on CPU and Apple Silicon Metal (MPS).
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch

try:
    from safetensors.torch import load_file as load_safetensors, save_file as save_safetensors
    HAS_SAFETENSORS = True
except ImportError:
    HAS_SAFETENSORS = False

logger = logging.getLogger(__name__)


def trim_tensor_topk(tensor: torch.Tensor, density: float) -> torch.Tensor:
    """
    Trims tensor by retaining only the top-k% elements by absolute magnitude (density d).
    Remaining (1-d)% elements are zeroed out.

    Args:
        tensor: Input PyTorch tensor of any shape.
        density: Fraction of weights to keep (0.0 < density <= 1.0).

    Returns:
        Trimmed tensor with sparse zeros where magnitude was below threshold.
    """
    if density >= 1.0:
        return tensor.clone()
    if density <= 0.0:
        return torch.zeros_like(tensor)

    orig_shape = tensor.shape
    orig_dtype = tensor.dtype
    flat = tensor.reshape(-1)
    n_elements = flat.numel()
    k = max(1, int(math.ceil(n_elements * density)))

    if k >= n_elements:
        return tensor.clone()

    abs_flat = torch.abs(flat.float())
    # Find the k-th largest value threshold
    topk_vals, _ = torch.topk(abs_flat, k, largest=True, sorted=False)
    threshold = topk_vals.min()

    # Mask elements strictly below threshold
    mask = (abs_flat >= threshold)
    # If mask has more than k elements due to exact ties, refine to exactly k
    if mask.sum() > k:
        _, topk_indices = torch.topk(abs_flat, k, largest=True, sorted=False)
        mask = torch.zeros_like(mask, dtype=torch.bool)
        mask[topk_indices] = True

    trimmed = (flat * mask).reshape(orig_shape).to(orig_dtype)
    return trimmed


def elect_signs(
    deltas: List[torch.Tensor],
    weights: Optional[List[float]] = None,
) -> torch.Tensor:
    """
    Elects sign consensus across multiple delta tensors via weighted sum:
    sign_consensus = sign(Σ w_m * ΔW_m).

    Args:
        deltas: List of delta tensors with identical shapes.
        weights: Optional weighting factors for each delta.

    Returns:
        Sign consensus tensor with values in {-1.0, 0.0, 1.0}.
    """
    if not deltas:
        raise ValueError("Cannot elect signs from empty deltas list")

    if weights is None:
        weights = [1.0] * len(deltas)
    if len(weights) != len(deltas):
        raise ValueError(f"Weights length ({len(weights)}) must match deltas length ({len(deltas)})")

    weighted_sum = torch.zeros_like(deltas[0], dtype=torch.float32)
    for delta, w in zip(deltas, weights):
        weighted_sum += delta.to(torch.float32) * float(w)

    signs = torch.sign(weighted_sum)
    return signs


def disjoint_merge(
    deltas: List[torch.Tensor],
    signs: torch.Tensor,
    weights: Optional[List[float]] = None,
    eps: float = 1e-8,
) -> torch.Tensor:
    """
    Performs disjoint merge of deltas: averages only the elements whose signs
    agree with the elected sign consensus (and discards conflicting/zero signs).

    Args:
        deltas: List of delta tensors with identical shapes.
        signs: Sign consensus tensor.
        weights: Optional weighting factors for each delta.
        eps: Small epsilon to prevent division by zero.

    Returns:
        Merged delta tensor.
    """
    if not deltas:
        raise ValueError("Cannot perform disjoint merge on empty deltas list")

    if weights is None:
        weights = [1.0] * len(deltas)

    orig_dtype = deltas[0].dtype
    signs_f = signs.to(torch.float32)
    accum_sum = torch.zeros_like(deltas[0], dtype=torch.float32)
    accum_weight = torch.zeros_like(deltas[0], dtype=torch.float32)

    for delta, w in zip(deltas, weights):
        d_f = delta.to(torch.float32)
        d_sign = torch.sign(d_f)
        # Agreement: sign matches consensus and is non-zero
        agree_mask = (d_sign == signs_f) & (signs_f != 0.0)
        agree_weight = float(w) * agree_mask.to(torch.float32)

        accum_sum += d_f * agree_weight
        accum_weight += agree_weight

    # Disjoint average where at least one delta agreed
    has_agree = accum_weight > 0.0
    merged_delta = torch.zeros_like(accum_sum)
    merged_delta[has_agree] = accum_sum[has_agree] / (accum_weight[has_agree] + eps)

    return merged_delta.to(orig_dtype)


def dare_drop_and_rescale(
    tensor: torch.Tensor,
    density: float,
    seed: Optional[int] = None,
) -> torch.Tensor:
    """
    Applies DARE (Drop And REscale):
    Drops weights with probability (1 - density) and rescales retained weights
    by 1 / density to conserve total tensor energy / expectation.

    Args:
        tensor: Input delta tensor.
        density: Fraction of weights to retain (0.0 < density <= 1.0).
        seed: Optional RNG seed for deterministic dropout.

    Returns:
        Rescaled delta tensor with dropped elements set to 0.
    """
    if density >= 1.0:
        return tensor.clone()
    if density <= 0.0:
        return torch.zeros_like(tensor)

    orig_dtype = tensor.dtype
    t_f = tensor.to(torch.float32)

    if seed is not None:
        generator = torch.Generator(device=tensor.device).manual_seed(seed)
    else:
        generator = None

    # Bernoulli mask with retention probability = density
    mask = torch.bernoulli(
        torch.full_like(t_f, float(density)),
        generator=generator,
    )

    scale_factor = 1.0 / float(density)
    rescaled = t_f * mask * scale_factor
    return rescaled.to(orig_dtype)


def slerp_tensors(
    v0: torch.Tensor,
    v1: torch.Tensor,
    t: Union[float, torch.Tensor] = 0.5,
    eps: float = 1e-8,
) -> torch.Tensor:
    """
    Spherical Linear Interpolation (SLERP) between two weight tensors.
    Interpolates along the spherical manifold:
      SLERP(v0, v1; t) = (sin((1-t)θ) / sin θ) v0 + (sin(tθ) / sin θ) v1

    Args:
        v0: First weight tensor (e.g. base or checkpoint 1).
        v1: Second weight tensor (e.g. adapted or checkpoint 2).
        t: Interpolation factor in [0.0, 1.0]. t=0 gives v0, t=1 gives v1.
        eps: Small epsilon for numerical stability.

    Returns:
        Interpolated tensor with same shape and dtype as v0.
    """
    orig_shape = v0.shape
    orig_dtype = v0.dtype

    if v0.shape != v1.shape:
        raise ValueError(f"Shape mismatch for SLERP: {v0.shape} vs {v1.shape}")

    # Handle float vs tensor t
    if isinstance(t, torch.Tensor):
        t_val = float(t.mean().item())
    else:
        t_val = float(t)

    t_val = max(0.0, min(1.0, t_val))
    if t_val == 0.0:
        return v0.clone()
    if t_val == 1.0:
        return v1.clone()

    f0 = v0.reshape(-1).to(torch.float32)
    f1 = v1.reshape(-1).to(torch.float32)

    norm0 = torch.norm(f0)
    norm1 = torch.norm(f1)

    if norm0 < eps or norm1 < eps:
        # Fallback to linear interpolation for near-zero norms
        lerp = (1.0 - t_val) * f0 + t_val * f1
        return lerp.reshape(orig_shape).to(orig_dtype)

    # Unit vectors
    u0 = f0 / (norm0 + eps)
    u1 = f1 / (norm1 + eps)

    # Cosine of angle between vectors
    dot = torch.clamp(torch.dot(u0, u1), -1.0, 1.0)
    theta = torch.acos(dot)

    sin_theta = torch.sin(theta)
    if sin_theta.abs() < 1e-6 or theta < 1e-6:
        # Collinear or parallel: linear interpolation
        lerp = (1.0 - t_val) * f0 + t_val * f1
        return lerp.reshape(orig_shape).to(orig_dtype)

    # SLERP formula
    scale0 = torch.sin((1.0 - t_val) * theta) / sin_theta
    scale1 = torch.sin(t_val * theta) / sin_theta

    slerp_unit = scale0 * u0 + scale1 * u1
    # Interpolate magnitude
    target_norm = (1.0 - t_val) * norm0 + t_val * norm1
    res = slerp_unit * target_norm

    return res.reshape(orig_shape).to(orig_dtype)


def merge_tensors(
    base: torch.Tensor,
    deltas: List[torch.Tensor],
    method: str = "ties",
    density: float = 0.6,
    weights: Optional[List[float]] = None,
    rescale: bool = True,
    t: float = 0.5,
    seed: Optional[int] = None,
) -> torch.Tensor:
    """
    Merges delta tensors into a base tensor using the specified algorithm.

    Args:
        base: Base model weight tensor.
        deltas: List of delta weight tensors (ΔW = W_adapted - W_base).
        method: One of "ties", "dare_ties", "dare_linear", "slerp", "linear", "task_arithmetic".
        density: Retained parameter fraction for TIES/DARE.
        weights: Weights for each adapter delta.
        rescale: Whether to apply energy rescaling in DARE.
        t: Interpolation factor for SLERP.
        seed: Optional RNG seed.

    Returns:
        Merged weight tensor.
    """
    if not deltas:
        return base.clone()

    method_clean = method.lower().replace("-", "_")

    if method_clean == "slerp":
        # SLERP blends base and (base + delta)
        target = base + deltas[0]
        return slerp_tensors(base, target, t=t)

    if method_clean == "linear" or method_clean == "task_arithmetic":
        if weights is None:
            weights = [1.0] * len(deltas)
        total_delta = torch.zeros_like(base, dtype=torch.float32)
        for d, w in zip(deltas, weights):
            total_delta += d.to(torch.float32) * float(w)
        return (base.to(torch.float32) + total_delta).to(base.dtype)

    # DARE step (Drop & Rescale)
    processed_deltas = []
    for i, d in enumerate(deltas):
        if "dare" in method_clean:
            d_proc = dare_drop_and_rescale(d, density=density, seed=(seed + i if seed else None))
        else:
            d_proc = trim_tensor_topk(d, density=density)
        processed_deltas.append(d_proc)

    if method_clean == "dare_linear":
        if weights is None:
            weights = [1.0] * len(processed_deltas)
        total_delta = torch.zeros_like(base, dtype=torch.float32)
        for d, w in zip(processed_deltas, weights):
            total_delta += d.to(torch.float32) * float(w)
        return (base.to(torch.float32) + total_delta).to(base.dtype)

    # TIES / DARE-TIES step
    signs = elect_signs(processed_deltas, weights=weights)
    merged_delta = disjoint_merge(processed_deltas, signs, weights=weights)

    return (base.to(torch.float32) + merged_delta.to(torch.float32)).to(base.dtype)


def merge_state_dicts(
    base_sd: Dict[str, torch.Tensor],
    delta_sds: List[Dict[str, torch.Tensor]],
    method: str = "ties",
    density: float = 0.6,
    weights: Optional[List[float]] = None,
    rescale: bool = True,
    t: float = 0.5,
    device: str = "cpu",
    seed: Optional[int] = None,
) -> Dict[str, torch.Tensor]:
    """
    In-memory state dict delta weight merger across all parameter tensors.

    Args:
        base_sd: Base model state dictionary {param_name: tensor}.
        delta_sds: List of delta state dictionaries {param_name: ΔW}.
        method: Merge algorithm ("ties", "dare_ties", "slerp", "linear", etc.).
        density: Retained density fraction.
        weights: List of weights per adapter.
        rescale: Whether to apply DARE rescaling.
        t: SLERP interpolation parameter.
        device: Target compute device ("cpu", "mps").
        seed: Optional RNG seed.

    Returns:
        Merged state dictionary.
    """
    merged_sd: Dict[str, torch.Tensor] = {}

    for key, base_param in base_sd.items():
        # Check if key is modified in delta state dicts
        active_deltas = []
        active_weights = []
        for i, d_sd in enumerate(delta_sds):
            if key in d_sd:
                active_deltas.append(d_sd[key].to(device))
                w = weights[i] if weights is not None else 1.0
                active_weights.append(w)

        if not active_deltas:
            merged_sd[key] = base_param.to(device).clone()
            continue

        merged_param = merge_tensors(
            base=base_param.to(device),
            deltas=active_deltas,
            method=method,
            density=density,
            weights=active_weights,
            rescale=rescale,
            t=t,
            seed=seed,
        )
        merged_sd[key] = merged_param

    return merged_sd


class NativeTensorMerger:
    """
    High-level orchestrator for native PyTorch weight merging without external tools.
    Handles safetensors, PyTorch checkpoints, PEFT adapters, and metadata.
    """

    def __init__(self, device: str = "cpu"):
        if device == "mps" and not torch.backends.mps.is_available():
            logger.warning("MPS device requested but not available. Falling back to CPU.")
            self.device = "cpu"
        else:
            self.device = device

    def load_state_dict_from_path(self, path: Union[str, Path]) -> Dict[str, torch.Tensor]:
        """Loads state dictionary from directory or single file (.safetensors, .bin, .pt)."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Weight path does not exist: {p}")

        if p.is_file():
            if p.suffix == ".safetensors" and HAS_SAFETENSORS:
                return load_safetensors(str(p), device=self.device)
            return torch.load(str(p), map_location=self.device, weights_only=True)

        # Directory: inspect for safetensors or pytorch_model.bin
        st_files = list(p.glob("*.safetensors"))
        if st_files and HAS_SAFETENSORS:
            combined_sd = {}
            for st_file in sorted(st_files):
                sd = load_safetensors(str(st_file), device=self.device)
                combined_sd.update(sd)
            return combined_sd

        bin_files = list(p.glob("*.bin")) + list(p.glob("*.pt"))
        if bin_files:
            combined_sd = {}
            for bf in sorted(bin_files):
                sd = torch.load(str(bf), map_location=self.device, weights_only=True)
                if isinstance(sd, dict):
                    combined_sd.update(sd)
            return combined_sd

        raise ValueError(f"No valid weight files found in directory: {p}")

    def save_state_dict(
        self,
        state_dict: Dict[str, torch.Tensor],
        output_dir: Union[str, Path],
        safe_serialization: bool = True,
    ) -> Path:
        """Saves merged state dict to output directory."""
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)

        if safe_serialization and HAS_SAFETENSORS:
            # Ensure tensors are contiguous
            clean_sd = {k: v.contiguous() for k, v in state_dict.items()}
            target_file = out_p / "model.safetensors"
            save_safetensors(clean_sd, str(target_file))
        else:
            target_file = out_p / "pytorch_model.bin"
            torch.save(state_dict, str(target_file))

        return target_file

    def compute_deltas(
        self,
        base_sd: Dict[str, torch.Tensor],
        adapter_sds: List[Dict[str, torch.Tensor]],
    ) -> List[Dict[str, torch.Tensor]]:
        """
        Computes delta weight dictionaries: ΔW = W_adapter - W_base.
        If adapter_sd is already a delta state dict (e.g. from LoRA decomposition),
        it is returned directly.
        """
        deltas: List[Dict[str, torch.Tensor]] = []
        for adapter_sd in adapter_sds:
            delta_dict: Dict[str, torch.Tensor] = {}
            for k, v in adapter_sd.items():
                if k in base_sd:
                    # Check if tensor represents full adapted weight or delta
                    if v.shape == base_sd[k].shape:
                        delta_dict[k] = v.to(self.device) - base_sd[k].to(self.device)
                else:
                    # If key not in base, assume it's already a delta or specialized parameter
                    delta_dict[k] = v.to(self.device)
            deltas.append(delta_dict)
        return deltas

    def merge(
        self,
        base_model: Union[str, Path, Dict[str, torch.Tensor]],
        adapters: List[Union[str, Path, Dict[str, torch.Tensor]]],
        output_dir: Optional[Union[str, Path]] = None,
        method: str = "ties",
        density: float = 0.6,
        weights: Optional[List[float]] = None,
        rescale: bool = True,
        t: float = 0.5,
        save_tokenizer: bool = True,
        seed: Optional[int] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        End-to-end merge execution.
        """
        # Load base state dict
        if isinstance(base_model, dict):
            base_sd = {k: v.to(self.device) for k, v in base_model.items()}
            base_path = None
        else:
            base_sd = self.load_state_dict_from_path(base_model)
            base_path = Path(base_model) if Path(base_model).is_dir() else Path(base_model).parent

        # Load adapter state dicts
        adapter_sds = []
        for ad in adapters:
            if isinstance(ad, dict):
                adapter_sds.append({k: v.to(self.device) for k, v in ad.items()})
            else:
                adapter_sds.append(self.load_state_dict_from_path(ad))

        # Compute deltas
        deltas = self.compute_deltas(base_sd, adapter_sds)

        # Merge
        merged_sd = merge_state_dicts(
            base_sd=base_sd,
            delta_sds=deltas,
            method=method,
            density=density,
            weights=weights,
            rescale=rescale,
            t=t,
            device=self.device,
            seed=seed,
        )

        # Save if output_dir specified
        if output_dir is not None:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            self.save_state_dict(merged_sd, out_p)

            # Copy config and tokenizer files from base model if available
            if base_path and base_path.is_dir():
                for cfg_file in base_path.glob("*.json"):
                    if not (out_p / cfg_file.name).exists():
                        shutil.copy2(cfg_file, out_p / cfg_file.name)
                if save_tokenizer:
                    for tok_file in list(base_path.glob("tokenizer*")) + list(base_path.glob("vocab*")) + list(base_path.glob("merges.txt")):
                        if not (out_p / tok_file.name).exists():
                            shutil.copy2(tok_file, out_p / tok_file.name)

        return merged_sd


def merge_adapters(
    base_model_path: Union[str, Path, Dict[str, torch.Tensor]],
    adapter_paths: List[Union[str, Path, Dict[str, torch.Tensor]]],
    output_dir: Optional[Union[str, Path]] = None,
    method: str = "ties",
    density: float = 0.6,
    weights: Optional[List[float]] = None,
    rescale: bool = True,
    t: float = 0.5,
    device: str = "cpu",
    save_tokenizer: bool = True,
    seed: Optional[int] = None,
) -> Dict[str, torch.Tensor]:
    """
    Standard interface contract function matching PROJECT.md for adapter weight merging.

    Args:
        base_model_path: Path to base HuggingFace model or state dict.
        adapter_paths: List of paths to adapter checkpoints or state dicts.
        output_dir: Optional output directory to write merged HuggingFace model.
        method: Merge algorithm ("ties", "dare_ties", "slerp", "linear").
        density: Retained weight density (0.0 < density <= 1.0).
        weights: Optional weighting factors for each adapter.
        rescale: Whether to apply DARE norm rescaling.
        t: Interpolation factor for SLERP.
        device: Hardware device ("cpu", "mps").
        save_tokenizer: Whether to copy tokenizer files to output directory.
        seed: Optional RNG seed.

    Returns:
        Merged PyTorch state dictionary.
    """
    merger = NativeTensorMerger(device=device)
    return merger.merge(
        base_model=base_model_path,
        adapters=adapter_paths,
        output_dir=output_dir,
        method=method,
        density=density,
        weights=weights,
        rescale=rescale,
        t=t,
        save_tokenizer=save_tokenizer,
        seed=seed,
    )
