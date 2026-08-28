"""
smolagi.monetization — Decentralized Asset Monetization & Business Swarm Interface.

Governs Features F12 and F13:
- Standardized packaging for 5 asset classes (code, cli, mcp, sdk, compute)
- Cryptographic SHA-256 and HMAC consensus signing
- Dynamic 7-layer mesh compute cycle discovery and reserve pricing
- Multi-tier ingress transmission client (Self-Healing Hub Port 18802, Cloudflare Edge, Shopify Gateway)
- Volatile tmpfs outbox queueing with zero-flash-wear guarantee
"""

from .asset_packager import (
    DEFAULT_HMAC_KEY,
    SCHEMA_VERSION,
    URN_TYPE_MAPPING,
    VALID_ASSET_CLASSES,
    VALID_CURRENCIES,
    VALID_ENCODINGS,
    VALID_PRICING_MODELS,
    VALID_TARGET_ARCHITECTURES,
    VALID_VOTES,
    AssetPackager,
    AssetPackagingError,
    ConsensusSignature,
    MonetizationSpec,
    PayloadManifest,
    ProvenanceSpec,
    TechnicalSpec,
    ValidationError,
    validate_asset_payload,
)
from .business_client import (
    DEFAULT_ENDPOINTS,
    NODE_IDENTIFIER,
    BusinessClient,
    TransmissionReceipt,
)
from .compute_broker import (
    CANONICAL_MESH_NODES,
    ComputeBroker,
    ComputeSlice,
    MeshNodeSpec,
)

__all__ = [
    # Asset Packager
    "SCHEMA_VERSION",
    "VALID_ASSET_CLASSES",
    "URN_TYPE_MAPPING",
    "VALID_TARGET_ARCHITECTURES",
    "VALID_PRICING_MODELS",
    "VALID_CURRENCIES",
    "VALID_ENCODINGS",
    "VALID_VOTES",
    "DEFAULT_HMAC_KEY",
    "TechnicalSpec",
    "MonetizationSpec",
    "ProvenanceSpec",
    "PayloadManifest",
    "ConsensusSignature",
    "AssetPackagingError",
    "ValidationError",
    "validate_asset_payload",
    "AssetPackager",
    # Compute Broker
    "MeshNodeSpec",
    "CANONICAL_MESH_NODES",
    "ComputeSlice",
    "ComputeBroker",
    # Business Client
    "DEFAULT_ENDPOINTS",
    "NODE_IDENTIFIER",
    "TransmissionReceipt",
    "BusinessClient",
]
