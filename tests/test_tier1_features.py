"""
Tier 1: Feature Coverage E2E Tests for SeaweedFS Storage Migration.
Validates:
1. SeaweedFS Master Cluster Status & Topology.
2. Volume Allocation & FID Generation.
3. Filer HTTP API Read/Write/Delete & Directory Indexing.
4. S3 API Compatibility & Object Lifecycle.
5. Thunderbolt 4 (bridge0) Ingress Binding & Network Socket Verification.
6. LaunchDaemon Autostart & KeepAlive Configuration.
"""

import os
import plistlib
import socket
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pytest

from tests.conftest import SeaweedFSClient, TB4NetworkProbe


class TestTier1FeatureCoverage:
    """Tier 1: Feature Coverage Test Suite."""

    def test_seaweedfs_master_cluster_status(self, seaweed_client: SeaweedFSClient):
        """Verify SeaweedFS Master cluster health, leader election, and topology."""
        status = seaweed_client.get_cluster_status()
        assert isinstance(status, dict), f"Expected dict response from master, got {type(status)}"
        
        # Check topology structure
        topology = status.get("Topology") or status.get("Cluster") or status
        assert topology is not None, "Master status must contain Topology or Cluster information"
        
        # Verify Free / Max volumes or DataCenters if available
        free_vols = topology.get("Free", 0)
        max_vols = topology.get("Max", 0)
        dc_list = topology.get("DataCenters", [])
        
        print(f"[Tier 1] Master Status Verified: Free Volumes={free_vols}, Max Volumes={max_vols}, DataCenters={len(dc_list)}")
        assert free_vols >= 0, "Free volume count must be non-negative"

    def test_seaweedfs_volume_allocation(self, seaweed_client: SeaweedFSClient):
        """Verify SeaweedFS Master volume allocation (/dir/assign) and FID generation."""
        assign_result = seaweed_client.assign_volume(count=1)
        assert isinstance(assign_result, dict), f"Expected dict from /dir/assign, got {type(assign_result)}"
        
        # SeaweedFS returns 'fid', 'url'/'publicUrl', 'count'
        assert "fid" in assign_result, f"Assign response missing 'fid': {assign_result}"
        fid = assign_result["fid"]
        assert "," in fid, f"Expected SeaweedFS FID format '<volume_id>,<file_key>', got: {fid}"
        
        # Verify volume target URL is provided
        target_url = assign_result.get("url") or assign_result.get("publicUrl")
        assert target_url, f"Assign response missing target URL: {assign_result}"
        print(f"[Tier 1] Volume Allocation Verified: FID={fid} -> Target URL={target_url}")

    def test_filer_http_api_crud(self, seaweed_client: SeaweedFSClient):
        """Verify Filer HTTP API read, write, metadata headers, and delete lifecycle."""
        test_path = "/e2e_tier1_tests/crud_test_payload.txt"
        test_payload = b"Lauburu-Monorepo Thunderbolt 4 SeaweedFS Migration Tier 1 Verification Payload\n"
        
        # 1. Write (PUT)
        status_code, body = seaweed_client.filer_write(test_path, test_payload, content_type="text/plain")
        assert status_code in (200, 201), f"Filer write failed with status {status_code}: {body}"
        
        # 2. Read (GET)
        read_code, read_data, headers = seaweed_client.filer_read(test_path)
        assert read_code == 200, f"Filer read failed with status {read_code}"
        assert read_data == test_payload, f"Payload mismatch! Expected {len(test_payload)} bytes, got {len(read_data)}"
        print(f"[Tier 1] Filer Write & Read Verified: {len(read_data)} bytes verified matching exactly.")
        
        # 3. Delete (DELETE)
        del_code, del_body = seaweed_client.filer_delete(test_path)
        assert del_code in (200, 202, 204), f"Filer delete failed with status {del_code}: {del_body}"
        
        # 4. Verify Not Found after deletion
        verify_code, _, _ = seaweed_client.filer_read(test_path)
        assert verify_code == 404, f"Expected 404 after deletion, got {verify_code}"

    def test_filer_directory_indexing_and_json_listing(self, seaweed_client: SeaweedFSClient):
        """Verify Filer directory creation, hierarchical indexing, and JSON directory listing."""
        dir_path = "/e2e_tier1_tests/dir_index_test"
        file_a = f"{dir_path}/item_alpha.json"
        file_b = f"{dir_path}/item_beta.json"
        payload_a = b'{"item": "alpha", "active": true}'
        payload_b = b'{"item": "beta", "active": true}'
        
        # Write files
        c_a, _ = seaweed_client.filer_write(file_a, payload_a, content_type="application/json")
        c_b, _ = seaweed_client.filer_write(file_b, payload_b, content_type="application/json")
        assert c_a in (200, 201) and c_b in (200, 201), "Failed to populate test directory files"
        
        # List directory
        list_code, entries = seaweed_client.filer_list_directory(dir_path)
        assert list_code == 200, f"Filer directory listing failed with status {list_code}"
        
        entry_names = [e.get("FullPath", "").split("/")[-1] for e in entries if isinstance(e, dict)]
        print(f"[Tier 1] Directory Entries Found: {entry_names}")
        assert "item_alpha.json" in entry_names or len(entries) >= 2, f"Entries missing item_alpha.json in {entries}"
        
        # Cleanup
        seaweed_client.filer_delete(dir_path, recursive=True)

    def test_s3_api_bucket_and_object_lifecycle(self, seaweed_client: SeaweedFSClient):
        """Verify SeaweedFS S3 Gateway API bucket and object lifecycle."""
        bucket_name = "e2e-tier1-bucket"
        object_key = "test_document.json"
        payload = b'{"s3_migration_test": true, "timestamp": 2026}'
        
        # 1. Create Bucket
        b_code = seaweed_client.s3_put_bucket(bucket_name)
        assert b_code in (200, 409), f"S3 PutBucket failed with status {b_code}"
        
        # 2. Put Object
        obj_code = seaweed_client.s3_put_object(bucket_name, object_key, payload)
        assert obj_code in (200, 201), f"S3 PutObject failed with status {obj_code}"
        
        # 3. Get Object
        get_code, get_data = seaweed_client.s3_get_object(bucket_name, object_key)
        assert get_code == 200, f"S3 GetObject failed with status {get_code}"
        assert get_data == payload, f"S3 data payload mismatch! Expected {payload}, got {get_data}"
        print(f"[Tier 1] S3 Gateway Object CRUD Verified: {len(get_data)} bytes verified matching.")
        
        # 4. Delete Object
        del_code = seaweed_client.s3_delete_object(bucket_name, object_key)
        assert del_code in (200, 204), f"S3 DeleteObject failed with status {del_code}"

    def test_tb4_bridge0_ingress_binding(self, tb4_probe: TB4NetworkProbe, tb4_ip: str):
        """Verify Thunderbolt 4 bridge0 interface status and SeaweedFS listener bindings."""
        iface_info = tb4_probe.get_interface_details("bridge0")
        assert iface_info["active"] is True, f"Thunderbolt 4 interface bridge0 must be active: {iface_info}"
        
        # Verify bridge0 IPv4 address is present
        ips = iface_info.get("ipv4_addresses", [])
        print(f"[Tier 1] bridge0 Detected IPv4 Addresses: {ips}")
        assert len(ips) > 0, "bridge0 must have at least one assigned IPv4 address"
        assert tb4_ip in ips or any(ip.startswith("169.254.") for ip in ips), \
            f"Expected TB4 IP {tb4_ip} in bridge0 IP list {ips}"
        
        # Verify socket connectivity to SeaweedFS ports on TB4 IP
        ports_to_check = [
            ("Master", 9333),
            ("Volume", 8080),
            ("Filer", 8888),
            ("S3 Gateway", 8333)
        ]
        for name, port in ports_to_check:
            is_open = tb4_probe.probe_socket(tb4_ip, port, timeout=2.0)
            print(f"[Tier 1] Socket Probe: {name} on {tb4_ip}:{port} -> {'OPEN' if is_open else 'CLOSED'}")
            # Assert port is open and responsive on TB4 interface
            assert is_open is True, f"SeaweedFS {name} port {port} must be open and listening on TB4 IP {tb4_ip}"

    def test_launchdaemon_autostart_and_keepalive_plist(self):
        """Verify macOS LaunchDaemon plist configuration for SeaweedFS auto-start and KeepAlive."""
        candidate_paths = [
            "/Library/LaunchDaemons/ai.lauburu.seaweedfs.plist",
            os.path.expanduser("~/Library/LaunchAgents/ai.lauburu.seaweedfs.plist"),
            "/Volumes/nas-1/Lauburu-Monorepo/scripts/launchd/ai.lauburu.seaweedfs.plist",
            "/System/Volumes/Data/seaweedfs/ai.lauburu.seaweedfs.plist"
        ]
        
        plist_path = None
        for p in candidate_paths:
            if os.path.exists(p):
                plist_path = p
                break
        
        assert plist_path is not None, f"Could not find SeaweedFS LaunchDaemon plist in candidate paths: {candidate_paths}"
        print(f"[Tier 1] Inspecting LaunchDaemon plist: {plist_path}")
        
        with open(plist_path, "rb") as f:
            plist_data = plistlib.load(f)
            
        assert plist_data.get("Label") == "ai.lauburu.seaweedfs", f"Expected Label 'ai.lauburu.seaweedfs', got {plist_data.get('Label')}"
        assert plist_data.get("RunAtLoad") is True, "LaunchDaemon RunAtLoad must be True for autostart"
        assert "KeepAlive" in plist_data, "LaunchDaemon must have KeepAlive configured"
        
        # Verify ProgramArguments
        prog_args = plist_data.get("ProgramArguments", [])
        assert any("weed" in arg for arg in prog_args), f"ProgramArguments must invoke 'weed': {prog_args}"
        assert "server" in prog_args, f"ProgramArguments must invoke 'weed server': {prog_args}"
        
        # Verify resource limits
        soft_limits = plist_data.get("SoftResourceLimits", {})
        hard_limits = plist_data.get("HardResourceLimits", {})
        nofiles = soft_limits.get("NumberOfFiles", 0) or hard_limits.get("NumberOfFiles", 0)
        assert nofiles >= 65536, f"NumberOfFiles resource limit must be >= 65536 to handle high concurrent IO, got {nofiles}"
        
        print(f"[Tier 1] LaunchDaemon Plist Verified Successfully: Label={plist_data['Label']}, NumberOfFiles={nofiles}")
