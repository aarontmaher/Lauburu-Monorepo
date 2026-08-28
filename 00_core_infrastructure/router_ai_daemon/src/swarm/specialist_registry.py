"""
specialist_registry.py — Heterogeneous Specialist Taxonomy & Registry for Router AI Daemon (smolagi).

Maintains micro-specialists across diverse architectures (SmolLM2, Qwen2.5, DeepSeek),
extreme quantizations (IQ1_S, IQ2_XXS, Q4_K_M), and language/domain specializations.
Authoritative Specifications: ORIGINAL_REQUEST.md §R3 & PROJECT.md §F5.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class SpecialistSpec:
    """Immutable specification for a micro-specialist AI model instance."""

    id: str
    model: str
    quant: str
    ram_mb: float
    specialty: str
    target_layer: str
    supported_languages: List[str] = field(default_factory=list)
    architecture: str = "SmolLM2"
    context_window: int = 1024
    description: str = ""
    priority: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary format."""
        return {
            "id": self.id,
            "model": self.model,
            "quant": self.quant,
            "ram_mb": self.ram_mb,
            "specialty": self.specialty,
            "target_layer": self.target_layer,
            "supported_languages": list(self.supported_languages),
            "architecture": self.architecture,
            "context_window": self.context_window,
            "description": self.description,
            "priority": self.priority,
        }


# Canonical 6 Heterogeneous Specialists (Per spec_miner_1/analysis.md & PROJECT.md)
CANONICAL_SPECIALISTS: List[SpecialistSpec] = [
    SpecialistSpec(
        id="spec_posix_healer",
        model="SmolLM2-135M-Instruct",
        quant="IQ1_S",
        ram_mb=42.0,
        specialty="posix_healer",
        target_layer="GW",
        supported_languages=["posix", "bash", "sh", "uci", "iptables"],
        architecture="SmolLM2",
        context_window=1024,
        description="OpenWrt uci, iptables, etherwake, dropbear SSH, procfs self-healing",
        priority=1,
    ),
    SpecialistSpec(
        id="spec_movesense_dsp",
        model="SmolLM2-360M-Instruct",
        quant="IQ2_XXS",
        ram_mb=98.0,
        specialty="movesense_dsp",
        target_layer="L4",
        supported_languages=["c", "python", "dsp", "ecg", "imu"],
        architecture="SmolLM2",
        context_window=1024,
        description="128Hz IMU/ECG unpacking, Pan-Tompkins QRS, DFA-alpha1 biometrics",
        priority=2,
    ),
    SpecialistSpec(
        id="spec_ast_surgeon",
        model="Qwen2.5-Coder-0.5B",
        quant="Q4_K_M",
        ram_mb=210.0,
        specialty="ast_surgeon",
        target_layer="L3",
        supported_languages=["python", "rust", "c", "cpp", "go", "dart"],
        architecture="Qwen2.5",
        context_window=2048,
        description="AST patching, syntax healing, multi-language compiler & lint diagnostics",
        priority=3,
    ),
    SpecialistSpec(
        id="spec_tb4_dma",
        model="SmolLM2-135M-Instruct",
        quant="IQ2_XXS",
        ram_mb=55.0,
        specialty="tb4_dma",
        target_layer="L1",
        supported_languages=["rust", "c", "sockets", "dma"],
        architecture="SmolLM2",
        context_window=1024,
        description="10Gbps TB4 DMA tensor streaming, low-latency socket multiplexing",
        priority=2,
    ),
    SpecialistSpec(
        id="spec_hf_turbo",
        model="SmolLM2-135M-Instruct",
        quant="IQ1_S",
        ram_mb=42.0,
        specialty="hf_turbo",
        target_layer="GW",
        supported_languages=["python", "bash", "downloads", "gguf"],
        architecture="SmolLM2",
        context_window=1024,
        description="Multi-socket chunked GGUF downloads, SHA256 verification",
        priority=1,
    ),
    SpecialistSpec(
        id="spec_ui_fuzzer",
        model="DeepSeek-R1-Distill-1.5B",
        quant="IQ2_XXS",
        ram_mb=280.0,
        specialty="ui_fuzzer",
        target_layer="L7",
        supported_languages=["typescript", "javascript", "html", "dom"],
        architecture="DeepSeek",
        context_window=2048,
        description="Headless DOM auditing, Tailwind WCAG AA compliance, a11y fuzzing",
        priority=3,
    ),
]


class SpecialistRegistry:
    """Registry managing micro-specialist specifications across architectures & quantizations."""

    def __init__(self, initial_specs: Optional[List[SpecialistSpec]] = None) -> None:
        self._specs: Dict[str, SpecialistSpec] = {}
        if initial_specs is None:
            self.reset_to_defaults()
        else:
            for spec in initial_specs:
                self.register(spec)

    def reset_to_defaults(self) -> None:
        """Reset registry to canonical 6 micro-specialists."""
        self._specs.clear()
        for spec in CANONICAL_SPECIALISTS:
            self.register(spec)

    def register(self, spec: SpecialistSpec) -> None:
        """Register a micro-specialist specification."""
        self._specs[spec.id] = spec

    def unregister(self, spec_id: str) -> bool:
        """Unregister a specialist by its ID."""
        if spec_id in self._specs:
            del self._specs[spec_id]
            return True
        return False

    def get(self, spec_id: str) -> Optional[SpecialistSpec]:
        """Get specialist specification by ID."""
        return self._specs.get(spec_id)

    def get_by_specialty(self, specialty: str) -> Optional[SpecialistSpec]:
        """Find the first specialist matching a given specialty name."""
        for spec in self._specs.values():
            if spec.specialty.lower() == specialty.lower():
                return spec
        return None

    def find_by_specialty(self, specialty: str) -> List[SpecialistSpec]:
        """Find all specialists matching a given specialty."""
        return [
            s for s in self._specs.values()
            if s.specialty.lower() == specialty.lower()
        ]

    def find_by_language(self, language: str) -> List[SpecialistSpec]:
        """Find specialists capable of handling the specified programming language."""
        lang_lower = language.lower()
        return [
            s for s in self._specs.values()
            if any(l.lower() == lang_lower for l in s.supported_languages)
        ]

    def find_by_layer(self, layer: str) -> List[SpecialistSpec]:
        """Find specialists targeted for a specific physical mesh layer."""
        layer_upper = layer.upper()
        return [
            s for s in self._specs.values()
            if s.target_layer.upper() == layer_upper
        ]

    def find_by_quant(self, quant: str) -> List[SpecialistSpec]:
        """Find specialists with a specific quantization level (e.g., IQ1_S, IQ2_XXS, Q4_K_M)."""
        quant_upper = quant.upper()
        return [
            s for s in self._specs.values()
            if s.quant.upper() == quant_upper
        ]

    def find_by_architecture(self, arch: str) -> List[SpecialistSpec]:
        """Find specialists with a specific model architecture family."""
        arch_lower = arch.lower()
        return [
            s for s in self._specs.values()
            if s.architecture.lower() == arch_lower
        ]

    def list_all(self) -> List[SpecialistSpec]:
        """Return a list of all registered specialist specifications."""
        return list(self._specs.values())

    def list_specialties(self) -> Set[str]:
        """Return a set of all registered specialty names."""
        return {s.specialty for s in self._specs.values()}

    def to_dict(self) -> List[Dict[str, Any]]:
        """Return list of specialist specifications as dictionaries."""
        return [s.to_dict() for s in self._specs.values()]

    def count(self) -> int:
        """Return total number of registered specialists."""
        return len(self._specs)


# Global singleton instance
DEFAULT_REGISTRY = SpecialistRegistry()


def get_specialist_registry() -> SpecialistRegistry:
    """Return the global default SpecialistRegistry instance."""
    return DEFAULT_REGISTRY
