"""
Tier 3: Cross-Feature Combinations E2E Tests for SeaweedFS Storage Migration.
Validates:
1. Concurrent Filer Read/Write operations during active Automount Sentinel healthcheck probes.
2. Thunderbolt 4 (bridge0) Route Isolation and prevention of Wi-Fi / Tailscale traffic leakage.
"""

import os
import time
import socket
import threading
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import pytest

from tests.conftest import SeaweedFSClient, TB4NetworkProbe


class TestTier3Combinations:
    """Tier 3: Cross-Feature Combinations Test Suite."""

    def test_concurrent_filer_rw_during_sentinel_probes(self, seaweed_client: SeaweedFSClient):
        """
        Verify that heavy concurrent Filer R/W workloads do not cause latency spikes
        that falsely trigger the automount sentinel's 2.0s healthcheck timeout or failover.
        """
        stop_event = threading.Event()
        io_errors = []
        io_count = [0]
        base_dir = "/e2e_tier3_tests/sentinel_rw_stress"
        
        print("[Tier 3] Spawning Background I/O Stress Threads...")
        
        def _heavy_io_worker(worker_id: int):
            seq = 0
            while not stop_event.is_set():
                filepath = f"{base_dir}/stream_{worker_id}_{seq}.dat"
                payload = os.urandom(256 * 1024) # 256KB chunks
                try:
                    w_code, _ = seaweed_client.filer_write(filepath, payload)
                    if w_code in (200, 201):
                        r_code, r_data, _ = seaweed_client.filer_read(filepath)
                        if r_code == 200 and len(r_data) == len(payload):
                            seaweed_client.filer_delete(filepath)
                            io_count[0] += 1
                        else:
                            io_errors.append(f"Worker {worker_id} read fail code {r_code}")
                    else:
                        io_errors.append(f"Worker {worker_id} write fail code {w_code}")
                except Exception as e:
                    io_errors.append(f"Worker {worker_id} exception: {e}")
                seq += 1
                time.sleep(0.01)

        # Spawn 8 background IO workers
        workers = [threading.Thread(target=_heavy_io_worker, args=(i,), daemon=True) for i in range(8)]
        for w in workers:
            w.start()

        # Execute 10 Sentinel Health Check Probes in foreground with strict 2.0s deadline
        sentinel_probe_latencies = []
        sentinel_probe_failures = []
        
        print("[Tier 3] Executing Foreground Sentinel Health Check Probes...")
        for probe_idx in range(10):
            t0 = time.perf_counter()
            healthy = False
            
            # Replicate Sentinel's Health Check Logic:
            # 1. TCP socket probe
            sock_ok = False
            try:
                host = seaweed_client.filer_url.split("://")[-1].split(":")[0]
                port = int(seaweed_client.filer_url.split(":")[-1])
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                sock_ok = (s.connect_ex((host, port)) == 0)
                s.close()
            except Exception:
                sock_ok = False
            
            # 2. Directory Listing / probe file check
            if sock_ok:
                list_code, entries = seaweed_client.filer_list_directory("/")
                if list_code == 200:
                    healthy = True
                    
            dt = time.perf_counter() - t0
            sentinel_probe_latencies.append(dt)
            
            if not healthy or dt > 2.0:
                sentinel_probe_failures.append({"probe": probe_idx, "latency_sec": dt, "healthy": healthy})
            
            time.sleep(0.2)

        # Stop background IO workers
        stop_event.set()
        for w in workers:
            w.join(timeout=2.0)
            
        print(f"[Tier 3] Sentinel Probe Summary: Total Probes=10, Completed I/O Ops={io_count[0]}, Background I/O Errors={len(io_errors)}")
        print(f"[Tier 3] Probe Latencies: Min={min(sentinel_probe_latencies)*1000:.2f}ms, Max={max(sentinel_probe_latencies)*1000:.2f}ms, Avg={sum(sentinel_probe_latencies)/len(sentinel_probe_latencies)*1000:.2f}ms")
        
        # Assertions
        assert len(sentinel_probe_failures) == 0, f"Sentinel healthcheck failed during I/O: {sentinel_probe_failures}"
        assert all(lat < 2.0 for lat in sentinel_probe_latencies), "Sentinel probe latency exceeded 2.0s threshold!"
        assert len(io_errors) == 0, f"I/O errors occurred during sentinel probe test: {io_errors[:5]}"
        
        # Cleanup
        seaweed_client.filer_delete(base_dir, recursive=True)

    def test_tb4_route_isolation_and_no_leakage(self, tb4_probe: TB4NetworkProbe, seaweed_client: SeaweedFSClient, tb4_ip: str):
        """
        Verify that routing to Thunderbolt 4 endpoints strictly utilizes bridge0
        and that SeaweedFS Master advertises ONLY TB4 bridge IPs, avoiding Wi-Fi/Tailscale leakage.
        """
        # 1. Verify kernel route table for Thunderbolt 4 peer endpoints
        peer_ips_to_test = ["169.254.87.238", "169.254.122.166", tb4_ip]
        verified_routes = []
        
        for ip in peer_ips_to_test:
            route_info = tb4_probe.check_route_for_ip(ip)
            iface = route_info.get("interface")
            if iface:
                print(f"[Tier 3] Kernel Route for {ip}: Interface = {iface}")
                assert iface not in ("utun4", "utun3", "utun0", "en1"), \
                    f"Route {ip} leaked onto Tailscale ({iface}) or Wi-Fi! Route info: {route_info}"
                assert iface in ("bridge0", "lo0") or iface.startswith("en"), \
                    f"Expected route interface bridge0, lo0, or Thunderbolt enX, got {iface}"
                verified_routes.append(iface)
                
        assert len(verified_routes) > 0, f"No valid routes resolved for TB4 peers: {peer_ips_to_test}"
        
        # 2. Verify SeaweedFS Master volume assign URL endpoints
        assign = seaweed_client.assign_volume(count=1)
        target_url = assign.get("url") or assign.get("publicUrl", "")
        print(f"[Tier 3] SeaweedFS Master Advertised Endpoint: {target_url}")
        
        # Assert volume server address does NOT contain Tailscale (100.x.x.x) or Wi-Fi (192.168.8.x)
        assert not target_url.startswith("100."), f"Volume Server endpoint leaked onto Tailscale IP: {target_url}"
        assert not target_url.startswith("192.168."), f"Volume Server endpoint leaked onto Wi-Fi / LAN IP: {target_url}"
        assert target_url.startswith("169.254.") or target_url.startswith("10.0.") or target_url.startswith("127.0.0.1") or target_url.startswith("localhost"), \
            f"Volume Server endpoint must be on Thunderbolt 4 subnet (169.254.x.x / 10.0.40.x) or local, got: {target_url}"
        
        print("[Tier 3] Thunderbolt 4 Route Isolation and Zero-Leakage Verified.")
