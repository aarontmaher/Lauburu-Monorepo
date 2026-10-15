"""
Weight Merging and Quantization Module for Subsystem 12 (Continuous LoRA Evolution).
Provides MergeKit manifest generation, pure PyTorch in-memory TIES/DARE/SLERP merging,
and GGUF quantization toolchains.
"""

from .mergekit_manifest_generator import (
    MergeKitManifestGenerator,
    generate_mergekit_manifest,
    validate_manifest,
)
from .native_ties_dare_merger import (
    NativeTensorMerger,
    dare_drop_and_rescale,
    disjoint_merge,
    elect_signs,
    merge_adapters,
    merge_state_dicts,
    merge_tensors,
    slerp_tensors,
    trim_tensor_topk,
)
from .gguf_quantizer import (
    GGUFMetadata,
    GGUFQuantizer,
    QuantizationResult,
    convert_hf_to_gguf,
    inspect_gguf,
    quantize_gguf,
    quantize_model,
    validate_gguf,
)

__all__ = [
    "MergeKitManifestGenerator",
    "generate_mergekit_manifest",
    "validate_manifest",
    "NativeTensorMerger",
    "merge_adapters",
    "merge_state_dicts",
    "merge_tensors",
    "trim_tensor_topk",
    "elect_signs",
    "disjoint_merge",
    "dare_drop_and_rescale",
    "slerp_tensors",
    "GGUFQuantizer",
    "GGUFMetadata",
    "QuantizationResult",
    "convert_hf_to_gguf",
    "quantize_gguf",
    "quantize_model",
    "inspect_gguf",
    "validate_gguf",
]
