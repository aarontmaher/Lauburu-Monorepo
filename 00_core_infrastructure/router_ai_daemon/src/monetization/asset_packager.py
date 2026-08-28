"""
asset_packager.py — Standardized 5-Class Asset Packaging & Cryptographic Signing.

Governs Feature F12 (Decentralized Asset Packaging):
1. Standardized packaging for 5 asset classes:
   - `code_component` (AST snippets, SIMD kernels, DSP routines)
   - `cli_tool` (standalone binaries, shell/Python utilities)
   - `mcp_server` (Model Context Protocol tool servers)
   - `sdk_package` (client libraries across languages)
   - `surplus_compute` (idle NPU/VRAM/bandwidth compute slices)
2. Strict JSON Schema validation conforming to draft 2020-12 / LauburuMarketplaceAssetPayload.
3. SHA-256 content hashing, URN formatting, and HMAC consensus signing.
4. Volatile tmpfs outbox staging (/tmp/business_queue/) for zero-flash-wear transmission.

Authoritative Reference: ORIGINAL_REQUEST.md § R7 & PROJECT.md Feature F12.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"

VALID_ASSET_CLASSES: Set[str] = {
    "code_component",
    "cli_tool",
    "mcp_server",
    "sdk_package",
    "surplus_compute",
}

URN_TYPE_MAPPING: Dict[str, str] = {
    "code_component": "code",
    "cli_tool": "cli",
    "mcp_server": "mcp",
    "sdk_package": "sdk",
    "surplus_compute": "compute",
}

VALID_TARGET_ARCHITECTURES: Set[str] = {
    "arm64",
    "x86_64",
    "mips",
    "wasm",
    "agnostic",
}

VALID_PRICING_MODELS: Set[str] = {
    "one_time_purchase",
    "pay_per_execution",
    "hourly_lease",
    "subscription_tier",
}

VALID_CURRENCIES: Set[str] = {
    "LCT",
    "AUD",
    "USD",
    "CREDITS",
}

VALID_ENCODINGS: Set[str] = {
    "base64_tar_gz",
    "raw_text_json",
    "uri_reference",
}

VALID_VOTES: Set[str] = {
    "RATIFIED",
    "REJECTED",
}

URN_REGEX = re.compile(
    r"^urn:lauburu:asset:(code|cli|mcp|sdk|compute):[a-f0-9]{12,64}$"
)
SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+$")
HEX64_REGEX = re.compile(r"^[a-f0-9]{64}$")
ISO_DATE_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

DEFAULT_HMAC_KEY = os.getenv("LAUBURU_HMAC_KEY", "lauburu_secret_master_key")


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class AssetPackagingError(Exception):
    """Base exception for asset packaging failures."""
    pass


class ValidationError(AssetPackagingError):
    """Raised when an asset payload violates the JSON Schema."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        message = f"Asset payload schema validation failed with {len(errors)} error(s):\n  - " + "\n  - ".join(errors)
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class TechnicalSpec:
    target_architecture: List[str]
    runtime_environment: str
    ram_footprint_mb: float
    benchmark_metrics: Optional[Dict[str, Any]] = None
    compute_specs: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "target_architecture": list(self.target_architecture),
            "runtime_environment": self.runtime_environment,
            "ram_footprint_mb": float(self.ram_footprint_mb),
        }
        if self.benchmark_metrics is not None:
            d["benchmark_metrics"] = self.benchmark_metrics
        if self.compute_specs is not None:
            d["compute_specs"] = self.compute_specs
        return d


@dataclass
class MonetizationSpec:
    pricing_model: str
    floor_price_lct: float
    suggested_price_lct: float
    currency: str = "LCT"
    fiat_equivalent_estimate_aud: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "pricing_model": self.pricing_model,
            "floor_price_lct": float(self.floor_price_lct),
            "suggested_price_lct": float(self.suggested_price_lct),
            "currency": self.currency,
        }
        if self.fiat_equivalent_estimate_aud is not None:
            d["fiat_equivalent_estimate_aud"] = float(self.fiat_equivalent_estimate_aud)
        return d


@dataclass
class ProvenanceSpec:
    discovering_agent_id: str
    timestamp_utc: str
    verification_run_id: str
    merkle_state_root: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discovering_agent_id": self.discovering_agent_id,
            "timestamp_utc": self.timestamp_utc,
            "verification_run_id": self.verification_run_id,
            "merkle_state_root": self.merkle_state_root,
        }


@dataclass
class PayloadManifest:
    content_encoding: str
    payload_sha256: str
    payload_data_or_uri: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_encoding": self.content_encoding,
            "payload_sha256": self.payload_sha256,
            "payload_data_or_uri": self.payload_data_or_uri,
        }


@dataclass
class ConsensusSignature:
    dual_core_ratified: bool
    smolagi_vote: str
    genetic_router_vote: str
    hmac_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dual_core_ratified": bool(self.dual_core_ratified),
            "smolagi_vote": self.smolagi_vote,
            "genetic_router_vote": self.genetic_router_vote,
            "hmac_sha256": self.hmac_sha256,
        }


# ---------------------------------------------------------------------------
# Strict Schema Validation
# ---------------------------------------------------------------------------

def validate_asset_payload(payload: Dict[str, Any], raise_exception: bool = False) -> Tuple[bool, List[str]]:
    """
    Validates an asset payload against the canonical LauburuMarketplaceAssetPayload schema.
    Returns (is_valid, error_list).
    """
    errors: List[str] = []

    if not isinstance(payload, dict):
        errors.append("Payload must be a dictionary.")
        if raise_exception:
            raise ValidationError(errors)
        return False, errors

    # Top-level required fields
    required_top = [
        "schema_version",
        "asset_id",
        "asset_type",
        "title",
        "description",
        "version",
        "tags",
        "technical_spec",
        "monetization",
        "provenance",
        "payload_manifest",
        "consensus_signature",
    ]

    for req in required_top:
        if req not in payload:
            errors.append(f"Missing required top-level field: '{req}'")

    if errors:
        if raise_exception:
            raise ValidationError(errors)
        return False, errors

    # 1. schema_version
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Invalid schema_version '{payload.get('schema_version')}', must be '{SCHEMA_VERSION}'")

    # 2. asset_type
    asset_type = payload.get("asset_type")
    if asset_type not in VALID_ASSET_CLASSES:
        errors.append(f"Invalid asset_type '{asset_type}', must be one of {sorted(VALID_ASSET_CLASSES)}")

    # 3. asset_id URN
    asset_id = payload.get("asset_id", "")
    if not isinstance(asset_id, str) or not URN_REGEX.match(asset_id):
        errors.append(f"Invalid asset_id '{asset_id}', must match pattern ^urn:lauburu:asset:(code|cli|mcp|sdk|compute):[a-f0-9]{{12,64}}$")
    else:
        # Check type alignment in URN
        if asset_type in VALID_ASSET_CLASSES:
            expected_prefix = f"urn:lauburu:asset:{URN_TYPE_MAPPING[asset_type]}:"
            if not asset_id.startswith(expected_prefix):
                errors.append(f"asset_id prefix '{asset_id}' does not match expected '{expected_prefix}' for asset_type '{asset_type}'")

    # 4. title
    title = payload.get("title")
    if not isinstance(title, str) or len(title) < 5 or len(title) > 120:
        errors.append(f"Title must be a string with length between 5 and 120 characters (got {len(title) if isinstance(title, str) else type(title)})")

    # 5. description
    description = payload.get("description")
    if not isinstance(description, str) or len(description) < 20 or len(description) > 2000:
        errors.append(f"Description must be a string with length between 20 and 2000 characters (got {len(description) if isinstance(description, str) else type(description)})")

    # 6. version
    version = payload.get("version")
    if not isinstance(version, str) or not SEMVER_REGEX.match(version):
        errors.append(f"Version '{version}' must match semantic versioning format (e.g. '1.0.0')")

    # 7. tags
    tags = payload.get("tags")
    if not isinstance(tags, list) or len(tags) < 1 or not all(isinstance(t, str) and len(t) > 0 for t in tags):
        errors.append("Tags must be a non-empty list of non-empty strings")

    # 8. technical_spec
    tech = payload.get("technical_spec")
    if not isinstance(tech, dict):
        errors.append("technical_spec must be a dictionary")
    else:
        for tf in ["target_architecture", "runtime_environment", "ram_footprint_mb"]:
            if tf not in tech:
                errors.append(f"technical_spec missing required field '{tf}'")

        target_arch = tech.get("target_architecture")
        if not isinstance(target_arch, list) or not target_arch or not all(a in VALID_TARGET_ARCHITECTURES for a in target_arch):
            errors.append(f"target_architecture must be a non-empty list of valid architectures: {sorted(VALID_TARGET_ARCHITECTURES)}")

        runtime_env = tech.get("runtime_environment")
        if not isinstance(runtime_env, str) or not runtime_env.strip():
            errors.append("runtime_environment must be a non-empty string")

        ram_mb = tech.get("ram_footprint_mb")
        if not isinstance(ram_mb, (int, float)) or ram_mb < 0.1:
            errors.append(f"ram_footprint_mb must be a number >= 0.1 (got {ram_mb})")

        bench = tech.get("benchmark_metrics")
        if bench is not None:
            if not isinstance(bench, dict):
                errors.append("benchmark_metrics must be a dictionary")
            else:
                pass_rate = bench.get("test_pass_rate_pct")
                if pass_rate is not None and (not isinstance(pass_rate, (int, float)) or pass_rate < 0.0 or pass_rate > 100.0):
                    errors.append(f"benchmark_metrics.test_pass_rate_pct must be between 0.0 and 100.0 (got {pass_rate})")

    # 9. monetization
    mon = payload.get("monetization")
    if not isinstance(mon, dict):
        errors.append("monetization must be a dictionary")
    else:
        for mf in ["pricing_model", "floor_price_lct", "suggested_price_lct", "currency"]:
            if mf not in mon:
                errors.append(f"monetization missing required field '{mf}'")

        pricing_model = mon.get("pricing_model")
        if pricing_model not in VALID_PRICING_MODELS:
            errors.append(f"Invalid pricing_model '{pricing_model}', must be one of {sorted(VALID_PRICING_MODELS)}")

        floor_price = mon.get("floor_price_lct")
        if not isinstance(floor_price, (int, float)) or floor_price < 0.0:
            errors.append(f"floor_price_lct must be a non-negative number (got {floor_price})")

        suggested_price = mon.get("suggested_price_lct")
        if not isinstance(suggested_price, (int, float)) or suggested_price < 0.0:
            errors.append(f"suggested_price_lct must be a non-negative number (got {suggested_price})")

        if isinstance(floor_price, (int, float)) and isinstance(suggested_price, (int, float)):
            if floor_price > suggested_price:
                errors.append(f"floor_price_lct ({floor_price}) cannot exceed suggested_price_lct ({suggested_price})")

        currency = mon.get("currency")
        if currency not in VALID_CURRENCIES:
            errors.append(f"Invalid currency '{currency}', must be one of {sorted(VALID_CURRENCIES)}")

    # 10. provenance
    prov = payload.get("provenance")
    if not isinstance(prov, dict):
        errors.append("provenance must be a dictionary")
    else:
        for pf in ["discovering_agent_id", "timestamp_utc", "verification_run_id", "merkle_state_root"]:
            if pf not in prov:
                errors.append(f"provenance missing required field '{pf}'")

        disc_id = prov.get("discovering_agent_id")
        if not isinstance(disc_id, str) or not disc_id.strip():
            errors.append("discovering_agent_id must be a non-empty string")

        ts = prov.get("timestamp_utc")
        if not isinstance(ts, str) or not ISO_DATE_REGEX.match(ts):
            errors.append(f"timestamp_utc '{ts}' must be an ISO 8601 UTC date-time string")

        v_run = prov.get("verification_run_id")
        if not isinstance(v_run, str) or not v_run.strip():
            errors.append("verification_run_id must be a non-empty string")

        merkle = prov.get("merkle_state_root")
        if not isinstance(merkle, str) or not HEX64_REGEX.match(merkle):
            errors.append(f"merkle_state_root must be a 64-character lowercase hex string (got '{merkle}')")

    # 11. payload_manifest
    manifest = payload.get("payload_manifest")
    if not isinstance(manifest, dict):
        errors.append("payload_manifest must be a dictionary")
    else:
        for mf in ["content_encoding", "payload_sha256", "payload_data_or_uri"]:
            if mf not in manifest:
                errors.append(f"payload_manifest missing required field '{mf}'")

        encoding = manifest.get("content_encoding")
        if encoding not in VALID_ENCODINGS:
            errors.append(f"Invalid content_encoding '{encoding}', must be one of {sorted(VALID_ENCODINGS)}")

        sha = manifest.get("payload_sha256")
        if not isinstance(sha, str) or not HEX64_REGEX.match(sha):
            errors.append(f"payload_sha256 must be a 64-character lowercase hex string (got '{sha}')")

        data_uri = manifest.get("payload_data_or_uri")
        if not isinstance(data_uri, str):
            errors.append("payload_data_or_uri must be a string")

    # 12. consensus_signature
    sig = payload.get("consensus_signature")
    if not isinstance(sig, dict):
        errors.append("consensus_signature must be a dictionary")
    else:
        for sf in ["dual_core_ratified", "smolagi_vote", "genetic_router_vote", "hmac_sha256"]:
            if sf not in sig:
                errors.append(f"consensus_signature missing required field '{sf}'")

        ratified = sig.get("dual_core_ratified")
        if not isinstance(ratified, bool):
            errors.append("dual_core_ratified must be a boolean")

        s_vote = sig.get("smolagi_vote")
        if s_vote not in VALID_VOTES:
            errors.append(f"Invalid smolagi_vote '{s_vote}', must be RATIFIED or REJECTED")

        g_vote = sig.get("genetic_router_vote")
        if g_vote not in VALID_VOTES:
            errors.append(f"Invalid genetic_router_vote '{g_vote}', must be RATIFIED or REJECTED")

        hmac_sig = sig.get("hmac_sha256")
        if not isinstance(hmac_sig, str) or not HEX64_REGEX.match(hmac_sig):
            errors.append(f"hmac_sha256 must be a 64-character lowercase hex string (got '{hmac_sig}')")

    is_valid = len(errors) == 0
    if not is_valid and raise_exception:
        raise ValidationError(errors)

    return is_valid, errors


# ---------------------------------------------------------------------------
# Canonical Asset Packager
# ---------------------------------------------------------------------------

class AssetPackager:
    """
    Production-grade asset packager for the 5 canonical monetizable asset classes.
    Provides strict schema validation, SHA-256 payload hashing, URN formatting,
    HMAC consensus signing, and tmpfs outbox queueing.
    """

    VALID_CLASSES = VALID_ASSET_CLASSES

    def __init__(self, hmac_key: str = DEFAULT_HMAC_KEY, outbox_dir: Optional[Union[str, Path]] = None):
        self.hmac_key = hmac_key
        self.outbox_dir = Path(outbox_dir) if outbox_dir else Path("/tmp/business_queue")

    def package_asset(
        self,
        asset_type: str,
        title: str,
        description: str,
        version: str,
        tags: List[str],
        technical_spec: Union[Dict[str, Any], TechnicalSpec],
        monetization: Union[Dict[str, Any], MonetizationSpec],
        provenance: Union[Dict[str, Any], ProvenanceSpec],
        raw_content: bytes,
        content_encoding: str = "raw_text_json",
        smolagi_vote: str = "RATIFIED",
        genetic_router_vote: str = "RATIFIED",
        dual_core_ratified: Optional[bool] = None,
        custom_asset_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Packages raw content and metadata into a signed, schema-compliant dictionary.
        """
        if asset_type not in self.VALID_CLASSES:
            raise ValueError(f"Invalid asset class '{asset_type}'. Must be one of {sorted(self.VALID_CLASSES)}")

        # Convert dataclasses to dicts if passed
        tech_dict = technical_spec.to_dict() if isinstance(technical_spec, TechnicalSpec) else dict(technical_spec)
        mon_dict = monetization.to_dict() if isinstance(monetization, MonetizationSpec) else dict(monetization)
        prov_dict = provenance.to_dict() if isinstance(provenance, ProvenanceSpec) else dict(provenance)

        # Content hashing
        payload_sha256 = hashlib.sha256(raw_content).hexdigest()

        # Asset ID generation
        type_prefix = URN_TYPE_MAPPING.get(asset_type, "code")
        if custom_asset_id:
            asset_id = custom_asset_id
        else:
            asset_id = f"urn:lauburu:asset:{type_prefix}:{payload_sha256[:16]}"

        # Encode content
        if content_encoding == "base64_tar_gz":
            payload_str = base64.b64encode(raw_content).decode("ascii")
        else:
            payload_str = raw_content.decode("utf-8", errors="replace")

        manifest = {
            "content_encoding": content_encoding,
            "payload_sha256": payload_sha256,
            "payload_data_or_uri": payload_str,
        }

        # Consensus votes & ratification
        if dual_core_ratified is None:
            is_ratified = (smolagi_vote == "RATIFIED" and genetic_router_vote == "RATIFIED")
        else:
            is_ratified = bool(dual_core_ratified)

        # HMAC consensus signature
        active_hmac_key = hmac_key or self.hmac_key
        sig_data = f"{asset_id}:{version}:{payload_sha256}".encode("utf-8")
        sig_hmac = hmac.new(active_hmac_key.encode("utf-8"), sig_data, hashlib.sha256).hexdigest()

        consensus_sig = {
            "dual_core_ratified": is_ratified,
            "smolagi_vote": smolagi_vote,
            "genetic_router_vote": genetic_router_vote,
            "hmac_sha256": sig_hmac,
        }

        payload: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "title": title,
            "description": description,
            "version": version,
            "tags": list(tags),
            "technical_spec": tech_dict,
            "monetization": mon_dict,
            "provenance": prov_dict,
            "payload_manifest": manifest,
            "consensus_signature": consensus_sig,
        }

        # Validate against strict schema
        validate_asset_payload(payload, raise_exception=True)

        return payload

    def sign_payload(self, asset_id: str, version: str, payload_sha256: str, hmac_key: Optional[str] = None) -> str:
        """Computes HMAC-SHA256 consensus signature."""
        key = hmac_key or self.hmac_key
        sig_data = f"{asset_id}:{version}:{payload_sha256}".encode("utf-8")
        return hmac.new(key.encode("utf-8"), sig_data, hashlib.sha256).hexdigest()

    def verify_signature(self, payload: Dict[str, Any], hmac_key: Optional[str] = None) -> bool:
        """Verifies that the consensus signature matches the payload content."""
        try:
            key = hmac_key or self.hmac_key
            asset_id = payload["asset_id"]
            version = payload["version"]
            payload_sha256 = payload["payload_manifest"]["payload_sha256"]
            expected_hmac = payload["consensus_signature"]["hmac_sha256"]
            computed_hmac = self.sign_payload(asset_id, version, payload_sha256, key)
            return hmac.compare_digest(expected_hmac, computed_hmac)
        except (KeyError, TypeError):
            return False

    def save_to_outbox(
        self,
        payload: Dict[str, Any],
        outbox_dir: Optional[Union[str, Path]] = None,
        indent: int = 2,
    ) -> Path:
        """
        Saves packaged asset payload to the volatile tmpfs outbox queue.
        Zero-flash-wear invariant: writes to /tmp/business_queue/.
        """
        target_dir = Path(outbox_dir) if outbox_dir else self.outbox_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Validate before writing
        validate_asset_payload(payload, raise_exception=True)

        filename_suffix = payload["asset_id"].split(":")[-1]
        out_file = target_dir / f"{filename_suffix}.json"

        # Atomic write to avoid partial read
        tmp_file = target_dir / f".{filename_suffix}.json.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=indent)

        tmp_file.replace(out_file)
        return out_file
