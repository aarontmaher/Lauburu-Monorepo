"""
test_monetization.py — Comprehensive Unit & Integration Tests for Milestone M6.
Validates Features F12 & F13:
1. AssetPackager: 5 canonical asset classes, strict schema validation, SHA-256 hashing, HMAC consensus signing, outbox persistence.
2. ComputeBroker: 7-layer physical mesh idle capacity detection, reserve & floor pricing math, compute slice packaging.
3. BusinessClient: Multi-tier ingress transmission, custom protocol headers, exponential backoff retries, failover, tmpfs outbox lifecycle.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from src.monetization import (
    AssetPackager,
    BusinessClient,
    CANONICAL_MESH_NODES,
    ComputeBroker,
    ComputeSlice,
    ConsensusSignature,
    MeshNodeSpec,
    MonetizationSpec,
    PayloadManifest,
    ProvenanceSpec,
    TechnicalSpec,
    TransmissionReceipt,
    ValidationError,
    validate_asset_payload,
)


# ---------------------------------------------------------------------------
# Test Suite 1: Asset Packaging & Schema Validation (Feature F12)
# ---------------------------------------------------------------------------

class TestAssetPackaging:
    """Validates 5-class asset packaging, schema validation, and cryptographic signing."""

    def test_package_all_five_asset_classes(self, tmp_path):
        """Validates that all 5 canonical asset classes package cleanly with valid schemas."""
        packager = AssetPackager(outbox_dir=tmp_path / "outbox")
        classes = ["code_component", "cli_tool", "mcp_server", "sdk_package", "surplus_compute"]

        for ac in classes:
            payload = packager.package_asset(
                asset_type=ac,
                title=f"Canonical Asset for {ac}",
                description=f"Standard test description for asset class {ac} meeting length constraints.",
                version="1.0.0",
                tags=["production", ac],
                technical_spec=TechnicalSpec(
                    target_architecture=["arm64", "x86_64"],
                    runtime_environment="musl_c99",
                    ram_footprint_mb=32.0,
                    benchmark_metrics={"speedup_multiplier": 2.5, "latency_reduction_pct": 40.0, "test_pass_rate_pct": 100.0},
                ),
                monetization=MonetizationSpec(
                    pricing_model="one_time_purchase",
                    floor_price_lct=10.0,
                    suggested_price_lct=25.0,
                    currency="LCT",
                    fiat_equivalent_estimate_aud=37.5,
                ),
                provenance=ProvenanceSpec(
                    discovering_agent_id="smolagi_gw_01",
                    timestamp_utc="2026-08-27T08:00:00Z",
                    verification_run_id=f"run_{ac}_01",
                    merkle_state_root="0" * 64,
                ),
                raw_content=f"payload_content_for_{ac}".encode("utf-8"),
            )

            assert payload["schema_version"] == "1.0.0"
            assert payload["asset_type"] == ac
            assert payload["consensus_signature"]["dual_core_ratified"] is True
            assert payload["consensus_signature"]["smolagi_vote"] == "RATIFIED"
            assert payload["consensus_signature"]["genetic_router_vote"] == "RATIFIED"

            # Check signature verification
            assert packager.verify_signature(payload) is True

    def test_urn_prefix_mapping(self):
        """Verifies URN prefix matches the asset class."""
        packager = AssetPackager()
        mapping = {
            "code_component": "urn:lauburu:asset:code:",
            "cli_tool": "urn:lauburu:asset:cli:",
            "mcp_server": "urn:lauburu:asset:mcp:",
            "sdk_package": "urn:lauburu:asset:sdk:",
            "surplus_compute": "urn:lauburu:asset:compute:",
        }

        for ac, prefix in mapping.items():
            payload = packager.package_asset(
                asset_type=ac,
                title=f"Sample Title for {ac}",
                description="Long enough description to satisfy validation.",
                version="2.1.0",
                tags=[ac],
                technical_spec={"target_architecture": ["arm64"], "runtime_environment": "posix", "ram_footprint_mb": 5.0},
                monetization={"pricing_model": "hourly_lease", "floor_price_lct": 1.0, "suggested_price_lct": 2.0, "currency": "LCT"},
                provenance={"discovering_agent_id": "gw", "timestamp_utc": "2026-08-27T08:00:00Z", "verification_run_id": "vr1", "merkle_state_root": "a" * 64},
                raw_content=b"content",
            )
            assert payload["asset_id"].startswith(prefix)

    def test_base64_tar_gz_encoding(self):
        """Verifies base64_tar_gz encoding option."""
        packager = AssetPackager()
        raw_binary = b"\x1f\x8b\x08\x00\x00\x00\x00\x00_binary_tar_gz_data"
        payload = packager.package_asset(
            asset_type="cli_tool",
            title="Binary CLI Utility",
            description="Standalone compiled ARM64 binary tool package.",
            version="1.0.0",
            tags=["binary", "cli"],
            technical_spec={"target_architecture": ["arm64"], "runtime_environment": "musl", "ram_footprint_mb": 1.5},
            monetization={"pricing_model": "one_time_purchase", "floor_price_lct": 5.0, "suggested_price_lct": 10.0, "currency": "LCT"},
            provenance={"discovering_agent_id": "gw", "timestamp_utc": "2026-08-27T08:00:00Z", "verification_run_id": "vr2", "merkle_state_root": "b" * 64},
            raw_content=raw_binary,
            content_encoding="base64_tar_gz",
        )
        assert payload["payload_manifest"]["content_encoding"] == "base64_tar_gz"
        decoded = base64.b64decode(payload["payload_manifest"]["payload_data_or_uri"])
        assert decoded == raw_binary

    def test_tampered_signature_rejection(self):
        """Verifies signature verification detects tampered content or signature."""
        packager = AssetPackager(hmac_key="master_key_123")
        payload = packager.package_asset(
            asset_type="code_component",
            title="DSP Filter Code",
            description="High efficiency DSP filter implementation in C.",
            version="1.0.0",
            tags=["dsp"],
            technical_spec={"target_architecture": ["arm64"], "runtime_environment": "c99", "ram_footprint_mb": 4.0},
            monetization={"pricing_model": "one_time_purchase", "floor_price_lct": 1.0, "suggested_price_lct": 2.0, "currency": "LCT"},
            provenance={"discovering_agent_id": "gw", "timestamp_utc": "2026-08-27T08:00:00Z", "verification_run_id": "vr3", "merkle_state_root": "c" * 64},
            raw_content=b"int dsp() { return 1; }",
        )

        assert packager.verify_signature(payload) is True

        # Tamper payload manifest hash
        tampered_payload = json.loads(json.dumps(payload))
        tampered_payload["payload_manifest"]["payload_sha256"] = "f" * 64
        assert packager.verify_signature(tampered_payload) is False

        # Wrong key
        assert packager.verify_signature(payload, hmac_key="different_key") is False

    def test_save_and_read_from_outbox(self, tmp_path):
        """Verifies atomic write to tmpfs outbox directory."""
        outbox = tmp_path / "business_queue"
        packager = AssetPackager(outbox_dir=outbox)

        payload = packager.package_asset(
            asset_type="mcp_server",
            title="Router Metrics MCP",
            description="Exposes router thermal and bandwidth telemetry via MCP.",
            version="1.0.0",
            tags=["mcp"],
            technical_spec={"target_architecture": ["arm64"], "runtime_environment": "python3", "ram_footprint_mb": 18.0},
            monetization={"pricing_model": "hourly_lease", "floor_price_lct": 2.0, "suggested_price_lct": 5.0, "currency": "LCT"},
            provenance={"discovering_agent_id": "gw", "timestamp_utc": "2026-08-27T08:00:00Z", "verification_run_id": "vr4", "merkle_state_root": "d" * 64},
            raw_content=b'{"tools": []}',
        )

        out_file = packager.save_to_outbox(payload)
        assert out_file.exists()
        loaded = json.loads(out_file.read_text())
        assert loaded["asset_id"] == payload["asset_id"]
        assert loaded["title"] == payload["title"]


# ---------------------------------------------------------------------------
# Test Suite 2: Schema Validation Edge Cases & Rejections
# ---------------------------------------------------------------------------

class TestSchemaValidationRejections:
    """Validates that schema validator rejects invalid or corrupted payloads."""

    @pytest.fixture
    def valid_base_payload(self) -> Dict[str, Any]:
        packager = AssetPackager()
        return packager.package_asset(
            asset_type="code_component",
            title="Valid Component Title",
            description="A comprehensive description that exceeds twenty characters.",
            version="1.0.0",
            tags=["valid"],
            technical_spec={"target_architecture": ["arm64"], "runtime_environment": "musl", "ram_footprint_mb": 10.0},
            monetization={"pricing_model": "one_time_purchase", "floor_price_lct": 5.0, "suggested_price_lct": 10.0, "currency": "LCT"},
            provenance={"discovering_agent_id": "gw", "timestamp_utc": "2026-08-27T08:00:00Z", "verification_run_id": "vr_test", "merkle_state_root": "e" * 64},
            raw_content=b"valid_code()",
        )

    def test_reject_missing_required_fields(self, valid_base_payload):
        """Rejects payload with missing top-level keys."""
        for key in ["schema_version", "asset_id", "monetization", "provenance", "consensus_signature"]:
            corrupt = dict(valid_base_payload)
            del corrupt[key]
            is_valid, errors = validate_asset_payload(corrupt)
            assert is_valid is False
            assert any(key in e for e in errors)
            with pytest.raises(ValidationError):
                validate_asset_payload(corrupt, raise_exception=True)

    def test_reject_invalid_asset_type(self, valid_base_payload):
        """Rejects unrecognized asset types."""
        corrupt = dict(valid_base_payload)
        corrupt["asset_type"] = "invalid_hardware_device"
        is_valid, errors = validate_asset_payload(corrupt)
        assert is_valid is False
        assert any("asset_type" in e for e in errors)

    def test_reject_invalid_semver(self, valid_base_payload):
        """Rejects non-semver version strings."""
        corrupt = dict(valid_base_payload)
        corrupt["version"] = "v1.0-beta"
        is_valid, errors = validate_asset_payload(corrupt)
        assert is_valid is False
        assert any("Version" in e or "version" in e for e in errors)

    def test_reject_short_title_and_description(self, valid_base_payload):
        """Rejects titles < 5 chars or descriptions < 20 chars."""
        c1 = dict(valid_base_payload)
        c1["title"] = "abc"
        assert validate_asset_payload(c1)[0] is False

        c2 = dict(valid_base_payload)
        c2["description"] = "too short"
        assert validate_asset_payload(c2)[0] is False

    def test_reject_floor_exceeding_suggested_price(self, valid_base_payload):
        """Rejects monetization where floor_price > suggested_price."""
        corrupt = dict(valid_base_payload)
        corrupt["monetization"] = {
            "pricing_model": "one_time_purchase",
            "floor_price_lct": 100.0,
            "suggested_price_lct": 50.0,
            "currency": "LCT",
        }
        is_valid, errors = validate_asset_payload(corrupt)
        assert is_valid is False
        assert any("floor_price_lct" in e for e in errors)

    def test_reject_negative_prices(self, valid_base_payload):
        """Rejects negative prices."""
        corrupt = dict(valid_base_payload)
        corrupt["monetization"] = {
            "pricing_model": "one_time_purchase",
            "floor_price_lct": -5.0,
            "suggested_price_lct": 10.0,
            "currency": "LCT",
        }
        assert validate_asset_payload(corrupt)[0] is False

    def test_reject_invalid_merkle_state_root(self, valid_base_payload):
        """Rejects non-64-hex merkle roots."""
        corrupt = dict(valid_base_payload)
        corrupt["provenance"] = dict(corrupt["provenance"])
        corrupt["provenance"]["merkle_state_root"] = "invalid_short_hash"
        is_valid, errors = validate_asset_payload(corrupt)
        assert is_valid is False
        assert any("merkle_state_root" in e for e in errors)


# ---------------------------------------------------------------------------
# Test Suite 3: Compute Broker & 7-Layer Mesh Pricing (Feature F12)
# ---------------------------------------------------------------------------

class TestComputeBroker:
    """Validates 7-layer mesh compute discovery, pricing formulas, and slice packaging."""

    def test_canonical_mesh_nodes_initialization(self):
        """Verifies 7-layer canonical mesh hardware specs."""
        broker = ComputeBroker()
        assert len(broker.nodes) == 8  # GW, L1-L7
        assert "L1" in broker.nodes
        assert "L2" in broker.nodes
        assert "L6" in broker.nodes

        # L1 Apple M4 Pro Mac Mini
        assert broker.nodes["L1"].npu_tops == 38.0
        assert broker.nodes["L1"].vram_headroom_gb == 21.6

        # L2 MacBook Pro (10Gbps TB4 DMA)
        assert broker.nodes["L2"].bandwidth_gbps == 10.0

        # L6 Pixel 10 Pro XL Tensor G5 NPU
        assert broker.nodes["L6"].npu_tops == 45.0

    def test_surplus_compute_detection_and_filtering(self):
        """Verifies surplus detection filters busy or offline nodes."""
        broker = ComputeBroker()

        # Mark L3 as 90% busy (load > 70% threshold)
        broker.update_node_status("L3", active_load_pct=90.0)
        # Mark L4 as offline
        broker.update_node_status("L4", is_online=False)

        slices = broker.detect_surplus_compute(min_vram_gb=2.0, max_load_pct=70.0)
        slice_layers = [s.node_layer for s in slices]

        assert "L1" in slice_layers
        assert "L2" in slice_layers
        assert "L6" in slice_layers
        assert "L3" not in slice_layers  # Filtered due to 90% load
        assert "L4" not in slice_layers  # Filtered due to offline
        assert "GW" not in slice_layers  # Router gateway does not sell compute

    def test_reserve_pricing_calculation(self):
        """Verifies reserve floor and suggested pricing calculations."""
        broker = ComputeBroker()

        # L1 plugged in Mac Mini M4 Pro: 38 TOPS, 21.6GB VRAM, 1Gbps BW
        node_l1 = broker.nodes["L1"]
        pricing_l1 = broker.calculate_reserve_pricing(node_l1)

        # Base: (38 * 0.50) + (21.6 * 1.00) + (1.0 * 0.80) = 19 + 21.6 + 0.8 = 41.4 LCT
        assert pricing_l1.floor_price_lct >= 40.0
        assert pricing_l1.suggested_price_lct > pricing_l1.floor_price_lct
        assert pricing_l1.fiat_equivalent_estimate_aud is not None
        assert pricing_l1.currency == "LCT"

        # L2 MacBook Pro (TB4 DMA 10Gbps, Battery): 18 TOPS, 14GB VRAM
        node_l2 = broker.nodes["L2"]
        pricing_l2 = broker.calculate_reserve_pricing(node_l2)
        assert pricing_l2.floor_price_lct > 0.0

    def test_battery_and_thermal_multipliers(self):
        """Verifies battery and thermal throttling pricing penalties/multipliers."""
        broker = ComputeBroker()
        node = MeshNodeSpec(
            layer="L9",
            name="Test_Node",
            ip="192.168.8.99",
            total_ram_mb=16384.0,
            ai_cap_mb=12000.0,
            npu_tops=20.0,
            vram_headroom_gb=10.0,
            bandwidth_gbps=1.0,
            arch="arm64",
            is_battery=False,
            temperature_c=45.0,
        )

        p_cool = broker.calculate_reserve_pricing(node)

        # High temperature (> 75C)
        node_hot = MeshNodeSpec(**node.__dict__)
        node_hot.temperature_c = 85.0
        p_hot = broker.calculate_reserve_pricing(node_hot)

        assert p_hot.floor_price_lct > p_cool.floor_price_lct

        # Battery powered
        node_bat = MeshNodeSpec(**node.__dict__)
        node_bat.is_battery = True
        p_bat = broker.calculate_reserve_pricing(node_bat)

        assert p_bat.floor_price_lct > p_cool.floor_price_lct

    def test_package_compute_slice_to_valid_asset(self, tmp_path):
        """Verifies packaging a ComputeSlice into a signed marketplace asset."""
        broker = ComputeBroker()
        slices = broker.detect_surplus_compute()
        assert len(slices) > 0

        c_slice = slices[0]
        packaged = broker.package_compute_slice(c_slice)

        assert packaged["schema_version"] == "1.0.0"
        assert packaged["asset_type"] == "surplus_compute"
        assert packaged["asset_id"].startswith("urn:lauburu:asset:compute:")
        assert packaged["consensus_signature"]["dual_core_ratified"] is True
        assert packaged["technical_spec"]["compute_specs"]["node_identifier"] == c_slice.node_name


# ---------------------------------------------------------------------------
# Test Suite 4: Business Transmission Client (Feature F13)
# ---------------------------------------------------------------------------

class TestBusinessClient:
    """Validates transmission client, multi-tier endpoints, exponential backoff, and outbox."""

    @pytest.fixture
    def sample_payload(self) -> Dict[str, Any]:
        packager = AssetPackager()
        return packager.package_asset(
            asset_type="cli_tool",
            title="OpenWrt Auto Healer",
            description="Automatic posix network link healing tool for travel routers.",
            version="1.0.0",
            tags=["cli", "openwrt"],
            technical_spec={"target_architecture": ["arm64", "mips"], "runtime_environment": "posix_sh", "ram_footprint_mb": 2.0},
            monetization={"pricing_model": "one_time_purchase", "floor_price_lct": 5.0, "suggested_price_lct": 12.0, "currency": "LCT"},
            provenance={"discovering_agent_id": "gw", "timestamp_utc": "2026-08-27T08:00:00Z", "verification_run_id": "vr_client_test", "merkle_state_root": "f" * 64},
            raw_content=b"#!/bin/sh\necho ok\n",
        )

    def test_client_headers_generation(self, sample_payload):
        """Verifies canonical security and consensus headers."""
        client = BusinessClient(node_id="GL_INET_ROUTER_GW")
        headers = client.build_headers(sample_payload)

        assert headers["Content-Type"] == "application/json"
        assert headers["X-Lauburu-Node-ID"] == "GL_INET_ROUTER_GW"
        assert "sha256=" in headers["X-Lauburu-Signature"]
        assert headers["X-Lauburu-Consensus-Proof"] == "f" * 64

    def test_successful_transmission_and_outbox_cleanup(self, tmp_path, sample_payload):
        """Verifies successful publication cleans up staged outbox file."""
        outbox = tmp_path / "business_queue"
        calls = []

        def mock_transport(req, timeout):
            calls.append(req.full_url)
            return 200, {"status": "PUBLISHED", "listing_id": "mkt_list_12345"}, {}

        client = BusinessClient(outbox_dir=outbox, transport_hook=mock_transport)

        receipt = client.publish_asset(sample_payload, endpoint_tier="primary_lan")

        assert receipt.is_success is True
        assert receipt.status == "PUBLISHED"
        assert receipt.listing_id == "mkt_list_12345"
        assert receipt.http_code == 200
        assert len(calls) == 1

        # File should be unlinked after success
        assert len(client.list_outbox()) == 0

    def test_retry_on_server_500_and_fallback(self, tmp_path, sample_payload):
        """Verifies exponential retry on 500 server error and failover to secondary tier."""
        outbox = tmp_path / "business_queue"
        attempts = []

        def mock_transport(req, timeout):
            attempts.append(req.full_url)
            # Primary LAN fails with 500, Cloudflare Edge succeeds with 200
            if "18802" in req.full_url:
                return 500, {"error": "Internal Hub Error"}, {}
            elif "cloudflare" in req.full_url or "lauburu.mesh" in req.full_url:
                return 200, {"listing_id": "mkt_cf_999"}, {}
            return 404, {}, {}

        client = BusinessClient(
            outbox_dir=outbox,
            transport_hook=mock_transport,
        )

        receipt = client.publish_asset(
            sample_payload,
            endpoint_tier="primary_lan",
            max_retries=2,
            base_backoff_s=0.01,  # Fast backoff for tests
            enable_failover=True,
        )

        assert receipt.is_success is True
        assert receipt.listing_id == "mkt_cf_999"
        assert len(attempts) > 1  # Retried on primary then succeeded on cloudflare

    def test_connection_failure_retains_outbox(self, tmp_path, sample_payload):
        """Verifies that completely failed transmissions retain the payload in the outbox."""
        outbox = tmp_path / "business_queue"

        def mock_transport(req, timeout):
            raise ConnectionError("Connection refused to all ports")

        client = BusinessClient(
            outbox_dir=outbox,
            transport_hook=mock_transport,
        )

        receipt = client.publish_asset(
            sample_payload,
            max_retries=2,
            base_backoff_s=0.01,
            enable_failover=False,
        )

        assert receipt.is_success is False
        assert receipt.status == "RETRY_QUEUED"
        assert receipt.http_code == 503

        # Payload remains in outbox for subsequent retry
        pending = client.list_outbox()
        assert len(pending) == 1

    def test_dispatch_pending_outbox(self, tmp_path, sample_payload):
        """Verifies batch dispatch of pending outbox items."""
        outbox = tmp_path / "business_queue"
        packager = AssetPackager(outbox_dir=outbox)
        packager.save_to_outbox(sample_payload)

        assert len(list(outbox.glob("*.json"))) == 1

        def mock_transport(req, timeout):
            return 200, {"listing_id": "mkt_batch_01"}, {}

        client = BusinessClient(outbox_dir=outbox, transport_hook=mock_transport)
        receipts = client.dispatch_pending_outbox()

        assert len(receipts) == 1
        assert receipts[0].is_success is True
        assert len(client.list_outbox()) == 0
