"""
Lauburu Canonical 12 Spec Modules Package
Version: 3.0.0-CANONICAL

Exports concrete implementations for all 12 spec modules (Spec-00 through Spec-12).
"""

from typing import Dict, List, Type

from ..base_module import BaseSpecModule
from .spec_00_core_infra import Spec00CoreInfraModule
from .spec_01_apps_ecosystem import Spec01AppsEcosystemModule
from .spec_02_ai_inference import Spec02AiInferenceModule
from .spec_03_biometrics_dsp import Spec03BiometricsDspModule
from .spec_04_data_memory import Spec04DataMemoryModule
from .spec_05_agents_swarms import Spec05AgentsSwarmsModule
from .spec_06_scripts_tooling import Spec06ScriptsToolingModule
from .spec_07_docs_architecture import Spec07DocsArchitectureModule
from .spec_08_business_commerce import Spec08BusinessCommerceModule
from .spec_09_app_store_production import Spec09AppStoreProductionModule
from .spec_10_spatial_grappling import Spec10SpatialGrapplingModule
from .spec_11_security import Spec11SecurityModule
from .spec_12_continuous_lora import Spec12ContinuousLoraModule
from .spec_11_12_security_lora import Spec1112SecurityLoraModule

# Canonical list of all 12 primary spec module classes (Spec-00 to Spec-12)
CANONICAL_SPEC_MODULE_CLASSES: List[Type[BaseSpecModule]] = [
    Spec00CoreInfraModule,
    Spec01AppsEcosystemModule,
    Spec02AiInferenceModule,
    Spec03BiometricsDspModule,
    Spec04DataMemoryModule,
    Spec05AgentsSwarmsModule,
    Spec06ScriptsToolingModule,
    Spec07DocsArchitectureModule,
    Spec08BusinessCommerceModule,
    Spec09AppStoreProductionModule,
    Spec10SpatialGrapplingModule,
    Spec11SecurityModule,
    Spec12ContinuousLoraModule,
]


def create_all_spec_modules() -> List[BaseSpecModule]:
    """Instantiate and return fresh instances of all 12 canonical spec modules."""
    return [cls() for cls in CANONICAL_SPEC_MODULE_CLASSES]


def create_spec_module_map() -> Dict[str, BaseSpecModule]:
    """Instantiate and return mapping of module_id -> instance for all 12 modules."""
    modules = create_all_spec_modules()
    return {mod.module_id: mod for mod in modules}


__all__ = [
    "BaseSpecModule",
    "Spec00CoreInfraModule",
    "Spec01AppsEcosystemModule",
    "Spec02AiInferenceModule",
    "Spec03BiometricsDspModule",
    "Spec04DataMemoryModule",
    "Spec05AgentsSwarmsModule",
    "Spec06ScriptsToolingModule",
    "Spec07DocsArchitectureModule",
    "Spec08BusinessCommerceModule",
    "Spec09AppStoreProductionModule",
    "Spec10SpatialGrapplingModule",
    "Spec11SecurityModule",
    "Spec12ContinuousLoraModule",
    "Spec1112SecurityLoraModule",
    "CANONICAL_SPEC_MODULE_CLASSES",
    "create_all_spec_modules",
    "create_spec_module_map",
]
