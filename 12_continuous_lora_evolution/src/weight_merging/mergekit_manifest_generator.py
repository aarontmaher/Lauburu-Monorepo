"""
MergeKit Configuration Manifest Generator (Feature F12).
Generates and validates standard MergeKit YAML configuration manifests for
DARE-TIES, TIES, and SLERP multi-adapter weight merging across Qwen 3.8 Max,
SmolLM2 1.7B, and Llama 3.2 1B base architectures.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml


@dataclass
class ModelEntry:
    """Represents a model or adapter entry in a MergeKit manifest."""
    model: str
    parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"model": self.model}
        if self.parameters is not None:
            data["parameters"] = self.parameters
        return data


@dataclass
class SliceSource:
    """Represents a slice source for SLERP / frankenmerge architectures."""
    model: str
    layer_range: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "layer_range": self.layer_range,
        }


@dataclass
class SliceEntry:
    """Represents a slice group in a MergeKit SLERP manifest."""
    sources: List[SliceSource]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": [s.to_dict() for s in self.sources]
        }


class MergeKitManifestGenerator:
    """
    Authoritative generator for MergeKit YAML configurations conforming to
    MergeKit specification (TIES, DARE-TIES, SLERP, Linear).
    """

    SUPPORTED_METHODS = {"dare_ties", "ties", "slerp", "linear", "task_arithmetic", "passthrough"}
    SUPPORTED_DTYPES = {"bfloat16", "float16", "float32"}

    # Canonical default paths in Lauburu Mesh
    QWEN38_BASE_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/qwen2.5-3b-base"
    QWEN38_REASONING_LORA = "/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/qwen38_reasoning_lora"
    QWEN38_CODE_AUDIT_LORA = "/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/qwen38_code_audit_lora"

    SMOLLM2_BASE_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/smollm2-1.7b-instruct"
    SMOLLM2_NETWORK_LORA = "/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/smollm2_network_telemetry_lora"
    SMOLLM2_TUI_LORA = "/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/smollm2_tui_actions_lora"

    LLAMA32_BASE_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/llama-3.2-1b-instruct"
    LLAMA32_AST_LORA = "/Users/aaron/DFS_UNIFIED/lora_datasets/adapters/llama32_ast_verifier_lora"

    @classmethod
    def create_dare_ties_manifest(
        cls,
        base_model: str,
        adapters_with_weights: List[Dict[str, Any]],
        base_weight: float = 1.0,
        density: float = 0.65,
        weight: float = 0.5,
        int8_mask: bool = True,
        normalize: bool = True,
        dtype: str = "bfloat16",
    ) -> Dict[str, Any]:
        """
        Creates a DARE-TIES MergeKit configuration dictionary.
        """
        models = [
            {"model": base_model, "parameters": {"weight": float(base_weight)}}
        ]
        for adapter in adapters_with_weights:
            model_path = adapter.get("model") or adapter.get("path")
            if not model_path:
                raise ValueError(f"Adapter entry must have 'model' or 'path': {adapter}")
            param_dict: Dict[str, Any] = {}
            if "weight" in adapter:
                param_dict["weight"] = float(adapter["weight"])
            if "density" in adapter:
                param_dict["density"] = float(adapter["density"])
            models.append({"model": model_path, "parameters": param_dict})

        manifest: Dict[str, Any] = {
            "models": models,
            "merge_method": "dare_ties",
            "base_model": base_model,
            "parameters": {
                "density": float(density),
                "weight": float(weight),
                "int8_mask": bool(int8_mask),
                "normalize": bool(normalize),
            },
            "dtype": dtype,
        }
        return manifest

    @classmethod
    def create_ties_manifest(
        cls,
        base_model: str,
        adapters_with_weights: List[Dict[str, Any]],
        base_weight: float = 1.0,
        density: float = 0.70,
        weight: float = 0.6,
        normalize: bool = True,
        dtype: str = "float16",
    ) -> Dict[str, Any]:
        """
        Creates a standard TIES MergeKit configuration dictionary.
        """
        models = [
            {"model": base_model, "parameters": {"weight": float(base_weight)}}
        ]
        for adapter in adapters_with_weights:
            model_path = adapter.get("model") or adapter.get("path")
            if not model_path:
                raise ValueError(f"Adapter entry must have 'model' or 'path': {adapter}")
            param_dict: Dict[str, Any] = {}
            if "weight" in adapter:
                param_dict["weight"] = float(adapter["weight"])
            if "density" in adapter:
                param_dict["density"] = float(adapter["density"])
            models.append({"model": model_path, "parameters": param_dict})

        manifest: Dict[str, Any] = {
            "models": models,
            "merge_method": "ties",
            "base_model": base_model,
            "parameters": {
                "density": float(density),
                "weight": float(weight),
                "normalize": bool(normalize),
            },
            "dtype": dtype,
        }
        return manifest

    @classmethod
    def create_slerp_manifest(
        cls,
        base_model: str,
        second_model_or_adapter: str,
        layer_range: Optional[List[int]] = None,
        t_parameters: Optional[Union[Dict[str, Any], List[Dict[str, Any]], float]] = None,
        dtype: str = "bfloat16",
    ) -> Dict[str, Any]:
        """
        Creates a SLERP (Spherical Linear Interpolation) MergeKit configuration dictionary.
        """
        if layer_range is None:
            layer_range = [0, 16]

        slices = [
            {
                "sources": [
                    {"model": base_model, "layer_range": layer_range},
                    {"model": second_model_or_adapter, "layer_range": layer_range},
                ]
            }
        ]

        if t_parameters is None:
            params: Dict[str, Any] = {
                "t": [
                    {"filter": "self_attn", "value": [0.0, 0.3, 0.5, 0.7, 1.0]},
                    {"filter": "mlp", "value": [0.2, 0.4, 0.6, 0.8, 1.0]},
                    {"value": 0.5},
                ]
            }
        elif isinstance(t_parameters, (int, float)):
            params = {"t": float(t_parameters)}
        elif isinstance(t_parameters, list):
            params = {"t": t_parameters}
        else:
            params = t_parameters

        manifest: Dict[str, Any] = {
            "slices": slices,
            "merge_method": "slerp",
            "base_model": base_model,
            "parameters": params,
            "dtype": dtype,
        }
        return manifest

    @classmethod
    def to_yaml(cls, manifest: Dict[str, Any], output_path: Optional[Union[str, Path]] = None) -> str:
        """
        Serializes manifest dictionary to clean YAML string and optionally writes to file.
        """
        # Ensure clean formatting
        yaml_str = yaml.dump(manifest, sort_keys=False, default_flow_style=False, allow_unicode=True)
        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(yaml_str)
        return yaml_str

    @classmethod
    def from_yaml(cls, yaml_path_or_str: Union[str, Path]) -> Dict[str, Any]:
        """
        Loads manifest from a YAML file or raw YAML string.
        """
        p = Path(yaml_path_or_str)
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = str(yaml_path_or_str)
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML dictionary, got {type(data)}")
        return data

    @classmethod
    def validate_manifest(cls, manifest: Union[Dict[str, Any], str, Path]) -> Tuple[bool, List[str]]:
        """
        Validates manifest schema according to MergeKit specifications.
        Returns (is_valid, error_messages).
        """
        errors: List[str] = []
        if isinstance(manifest, (str, Path)):
            try:
                data = cls.from_yaml(manifest)
            except Exception as e:
                return False, [f"YAML parsing error: {e}"]
        else:
            data = manifest

        if not isinstance(data, dict):
            return False, ["Manifest must be a top-level dictionary / object"]

        # Check merge_method
        merge_method = data.get("merge_method")
        if not merge_method:
            errors.append("Missing required field: 'merge_method'")
        elif merge_method not in cls.SUPPORTED_METHODS:
            errors.append(f"Unsupported merge_method '{merge_method}'. Must be one of {sorted(cls.SUPPORTED_METHODS)}")

        # Check base_model
        if "base_model" not in data or not data["base_model"]:
            errors.append("Missing required field: 'base_model'")

        # Check dtype
        dtype = data.get("dtype", "bfloat16")
        if dtype not in cls.SUPPORTED_DTYPES:
            errors.append(f"Invalid dtype '{dtype}'. Must be one of {sorted(cls.SUPPORTED_DTYPES)}")

        # Check structure based on merge_method
        if merge_method == "slerp":
            if "slices" not in data and "models" not in data:
                errors.append("SLERP manifest must specify 'slices' or 'models'")
            elif "slices" in data:
                slices = data["slices"]
                if not isinstance(slices, list) or len(slices) == 0:
                    errors.append("'slices' must be a non-empty list")
                else:
                    for i, sl in enumerate(slices):
                        if not isinstance(sl, dict) or "sources" not in sl:
                            errors.append(f"Slice index {i} missing 'sources'")
        else:
            if "models" not in data or not isinstance(data["models"], list) or len(data["models"]) < 2:
                errors.append("Manifest must contain 'models' list with at least 2 models (base + adapter)")

        # Validate parameters if present
        if "parameters" in data and not isinstance(data["parameters"], dict):
            errors.append("'parameters' must be a dictionary")

        return (len(errors) == 0, errors)

    @classmethod
    def generate_predefined_manifests(cls, output_dir: Union[str, Path] = "configs") -> Dict[str, Path]:
        """
        Generates canonical YAML manifest files for the three designated mesh models.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        results: Dict[str, Path] = {}

        # 1. Qwen 3.8 Max DARE-TIES
        qwen_manifest = cls.create_dare_ties_manifest(
            base_model=cls.QWEN38_BASE_PATH,
            adapters_with_weights=[
                {"model": cls.QWEN38_REASONING_LORA, "weight": 0.6, "density": 0.65},
                {"model": cls.QWEN38_CODE_AUDIT_LORA, "weight": 0.4, "density": 0.55},
            ],
            base_weight=1.0,
            density=0.65,
            weight=0.5,
            int8_mask=True,
            normalize=True,
            dtype="bfloat16",
        )
        qwen_path = out_dir / "qwen38_dare_ties.yaml"
        cls.to_yaml(qwen_manifest, qwen_path)
        results["qwen38_dare_ties"] = qwen_path

        # 2. SmolLM2 1.7B TIES
        smollm2_manifest = cls.create_ties_manifest(
            base_model=cls.SMOLLM2_BASE_PATH,
            adapters_with_weights=[
                {"model": cls.SMOLLM2_NETWORK_LORA, "weight": 0.7, "density": 0.70},
                {"model": cls.SMOLLM2_TUI_LORA, "weight": 0.5, "density": 0.60},
            ],
            base_weight=1.0,
            density=0.70,
            weight=0.6,
            normalize=True,
            dtype="float16",
        )
        smollm2_path = out_dir / "smollm2_ties.yaml"
        cls.to_yaml(smollm2_manifest, smollm2_path)
        results["smollm2_ties"] = smollm2_path

        # 3. Llama 3.2 1B SLERP
        llama32_manifest = cls.create_slerp_manifest(
            base_model=cls.LLAMA32_BASE_PATH,
            second_model_or_adapter=cls.LLAMA32_AST_LORA,
            layer_range=[0, 16],
            dtype="bfloat16",
        )
        llama32_path = out_dir / "llama32_slerp.yaml"
        cls.to_yaml(llama32_manifest, llama32_path)
        results["llama32_slerp"] = llama32_path

        return results


def generate_mergekit_manifest(
    base_model: str,
    models_with_params: List[Dict[str, Any]],
    merge_method: str = "ties",
    parameters: Optional[Dict[str, Any]] = None,
    dtype: str = "bfloat16",
    slices: Optional[List[Dict[str, Any]]] = None,
    output_file: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to generate a MergeKit manifest dictionary and optionally save to file.
    """
    manifest: Dict[str, Any] = {
        "merge_method": merge_method,
        "base_model": base_model,
        "dtype": dtype,
    }
    if slices is not None:
        manifest["slices"] = slices
    else:
        models = [{"model": base_model, "parameters": {"weight": 1.0}}]
        for m in models_with_params:
            models.append(m)
        manifest["models"] = models

    if parameters is not None:
        manifest["parameters"] = parameters

    is_valid, errors = MergeKitManifestGenerator.validate_manifest(manifest)
    if not is_valid:
        raise ValueError(f"Invalid MergeKit manifest generated: {'; '.join(errors)}")

    if output_file is not None:
        MergeKitManifestGenerator.to_yaml(manifest, output_file)

    return manifest


def validate_manifest(manifest_or_path: Union[Dict[str, Any], str, Path]) -> Tuple[bool, List[str]]:
    """
    Validates a MergeKit manifest dictionary or YAML file.
    """
    return MergeKitManifestGenerator.validate_manifest(manifest_or_path)
