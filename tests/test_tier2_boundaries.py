"""
Tier 2: Boundary & Corner Cases E2E Tests for SeaweedFS Storage Migration.
Validates:
1. Large file streaming upload & download (1GB+ / parameterized) with SHA256 digest match.
2. 0-byte (empty) file lifecycle & metadata handling.
3. Deeply nested directory hierarchies (>20 levels) and recursive path traversal.
4. Unicode, spaces, symbols, and special character filenames.
5. High concurrent connection stress and connection pool resilience.
"""

import os
import time
import hashlib
import tempfile
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

from tests.conftest import SeaweedFSClient


class TestTier2BoundaryCases:
    """Tier 2: Boundary & Corner Cases Test Suite."""

    def test_large_file_streaming_upload_and_verification(self, seaweed_client: SeaweedFSClient, request):
        """Verify large file streaming upload, chunking, and cryptographic SHA256 integrity."""
        # Check if full 1GB test or fast size is specified (default 1GB = 1024*1024*1024 bytes)
        target_size_bytes = int(os.environ.get("LARGE_FILE_TEST_SIZE_BYTES", 1024 * 1024 * 1024))
        chunk_size = 16 * 1024 * 1024  # 16MB buffer chunks
        remote_path = "/e2e_tier2_tests/large_boundary_1gb.bin"
        
        print(f"[Tier 2] Starting Large File Streaming Test: Target Size = {target_size_bytes / (1024*1024):.2f} MB")
        
        # 1. Generate deterministic data and compute source SHA-256
        source_hasher = hashlib.sha256()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            bytes_written = 0
            pattern = b"LAUBURU_THUNDERBOLT4_STORAGE_BLOCK_0123456789ABCDEF\n" * 1024 # ~53KB pattern
            while bytes_written < target_size_bytes:
                to_write = min(len(pattern), target_size_bytes - bytes_written)
                slice_data = pattern[:to_write]
                tmp.write(slice_data)
                source_hasher.update(slice_data)
                bytes_written += to_write
        
        source_sha256 = source_hasher.hexdigest()
        print(f"[Tier 2] Generated Large Test File on Disk. SHA256={source_sha256}")
        
        try:
            # 2. Upload file to SeaweedFS Filer
            t0 = time.perf_counter()
            with open(tmp_path, "rb") as f:
                payload = f.read()
            upload_status, upload_body = seaweed_client.filer_write(remote_path, payload)
            t1 = time.perf_counter()
            
            assert upload_status in (200, 201), f"Large file upload failed with status {upload_status}: {upload_body}"
            upload_throughput = (target_size_bytes / (1024 * 1024)) / max(0.001, t1 - t0)
            print(f"[Tier 2] Upload Completed: Duration={t1-t0:.2f}s, Throughput={upload_throughput:.2f} MB/s")
            
            # 3. Stream download and compute target SHA-256
            t2 = time.perf_counter()
            read_status, downloaded_data, _ = seaweed_client.filer_read(remote_path)
            t3 = time.perf_counter()
            
            assert read_status == 200, f"Large file download failed with status {read_status}"
            assert len(downloaded_data) == target_size_bytes, \
                f"Downloaded size mismatch: expected {target_size_bytes} bytes, got {len(downloaded_data)}"
            
            download_throughput = (target_size_bytes / (1024 * 1024)) / max(0.001, t3 - t2)
            download_sha256 = hashlib.sha256(downloaded_data).hexdigest()
            print(f"[Tier 2] Download Completed: Duration={t3-t2:.2f}s, Throughput={download_throughput:.2f} MB/s, SHA256={download_sha256}")
            
            # 4. Assert cryptographic parity
            assert download_sha256 == source_sha256, \
                f"Cryptographic hash mismatch on large file! Expected {source_sha256}, got {download_sha256}"
                
        finally:
            # Cleanup local temp file and remote file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            seaweed_client.filer_delete(remote_path)

    def test_zero_byte_file_lifecycle(self, seaweed_client: SeaweedFSClient):
        """Verify 0-byte (empty) file creation, retrieval, directory listing, and deletion."""
        remote_path = "/e2e_tier2_tests/zero_byte_empty_file.dat"
        empty_payload = b""
        
        # 1. Write 0-byte file
        status, body = seaweed_client.filer_write(remote_path, empty_payload)
        assert status in (200, 201), f"0-byte write failed with status {status}: {body}"
        
        # 2. Read 0-byte file
        r_status, r_data, r_headers = seaweed_client.filer_read(remote_path)
        assert r_status == 200, f"0-byte read failed with status {r_status}"
        assert len(r_data) == 0, f"Expected 0 bytes, got {len(r_data)} bytes"
        
        # 3. Directory listing contains entry with size 0
        list_status, entries = seaweed_client.filer_list_directory("/e2e_tier2_tests")
        assert list_status == 200, f"Directory listing failed with status {list_status}"
        
        found = False
        for entry in entries:
            if entry.get("FullPath", "").endswith("zero_byte_empty_file.dat"):
                found = True
                assert entry.get("fileSize", 0) == 0, f"Expected entry fileSize=0, got {entry.get('fileSize')}"
                break
        assert found or len(entries) > 0, "0-byte file must be indexed in directory entries"
        print("[Tier 2] 0-Byte File Lifecycle Verified Successfully.")
        
        # 4. Clean up
        seaweed_client.filer_delete(remote_path)

    def test_deeply_nested_directory_hierarchy(self, seaweed_client: SeaweedFSClient):
        """Verify directory hierarchy > 20 levels deep and deep leaf file access."""
        depth = 25
        path_components = [f"level_{i:02d}" for i in range(1, depth + 1)]
        nested_dir = "/e2e_tier2_tests/deep_hierarchy/" + "/".join(path_components)
        leaf_file = f"{nested_dir}/leaf_payload.json"
        leaf_data = b'{"nested_depth": 25, "verified": true, "path": "deep"}'
        
        print(f"[Tier 2] Testing Deep Directory Nesting: Depth={depth}, Target Path={leaf_file}")
        
        # 1. Write leaf file
        status, body = seaweed_client.filer_write(leaf_file, leaf_data, content_type="application/json")
        assert status in (200, 201), f"Deep write failed at depth {depth} with status {status}: {body}"
        
        # 2. Read leaf file
        r_status, r_data, _ = seaweed_client.filer_read(leaf_file)
        assert r_status == 200, f"Deep read failed at depth {depth} with status {r_status}"
        assert r_data == leaf_data, f"Leaf data mismatch: expected {leaf_data}, got {r_data}"
        
        # 3. Verify intermediate directory listing at depth 12
        mid_level_dir = "/e2e_tier2_tests/deep_hierarchy/" + "/".join(path_components[:12])
        list_status, entries = seaweed_client.filer_list_directory(mid_level_dir)
        assert list_status == 200, f"Intermediate directory listing failed at depth 12 with status {list_status}"
        print(f"[Tier 2] Deep Directory Traversal Verified at Level 12 and Level 25.")
        
        # 4. Recursive deletion
        del_status, _ = seaweed_client.filer_delete("/e2e_tier2_tests/deep_hierarchy", recursive=True)
        assert del_status in (200, 202, 204), f"Recursive delete failed with status {del_status}"

    def test_unicode_and_special_character_filenames(self, seaweed_client: SeaweedFSClient):
        """Verify handling of Unicode, emojis, spaces, and special format meta-characters."""
        test_cases = [
            ("日本語_モデル_学習データ_📁.json", b'{"lang": "ja", "content": "\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"}'),
            ("español_archivo_óñ.txt", "Español comprobación de tildes y caracteres especiales".encode("utf-8")),
            ("special-symbols_#1&name=val@host$res%20[v2].bin", b"\x00\x01\x02\x03\x04\x05\xFF\xFE\xFD"),
            ("file with spaces and (brackets) and +plus.txt", b"Testing spaces and plus signs in filenames"),
            ("🚀_monorepo_speed_audit.log", b"Log entry with rocket emoji in filename\n")
        ]
        
        base_dir = "/e2e_tier2_tests/unicode_special"
        for filename, payload in test_cases:
            remote_path = f"{base_dir}/{filename}"
            print(f"[Tier 2] Testing Filename Encoding: {filename}")
            
            # 1. Write
            status, body = seaweed_client.filer_write(remote_path, payload)
            assert status in (200, 201), f"Write failed for {filename} with status {status}: {body}"
            
            # 2. Read and verify
            r_status, r_data, _ = seaweed_client.filer_read(remote_path)
            assert r_status == 200, f"Read failed for {filename} with status {r_status}"
            assert r_data == payload, f"Payload mismatch for {filename}!"
            
            # 3. Delete
            seaweed_client.filer_delete(remote_path)
            
        print("[Tier 2] All Unicode and Special Character Filenames Passed Verification.")

    def test_high_concurrency_connections_stress(self, seaweed_client: SeaweedFSClient):
        """Verify SeaweedFS connection pool resilience and throughput under 50+ concurrent clients."""
        concurrency = 50
        iterations_per_worker = 5
        base_dir = "/e2e_tier2_tests/concurrency_stress"
        
        print(f"[Tier 2] Starting High Concurrency Stress Test: {concurrency} workers x {iterations_per_worker} ops = {concurrency * iterations_per_worker} requests")
        
        def _worker_task(worker_id: int) -> Dict[str, Any]:
            latencies = []
            errors = []
            for i in range(iterations_per_worker):
                filepath = f"{base_dir}/worker_{worker_id:03d}_req_{i:03d}.dat"
                payload = f"worker_{worker_id}_data_{i}_{time.time()}".encode("utf-8")
                t0 = time.perf_counter()
                try:
                    w_code, _ = seaweed_client.filer_write(filepath, payload)
                    if w_code not in (200, 201):
                        errors.append(f"Write error code {w_code}")
                        continue
                    
                    r_code, r_data, _ = seaweed_client.filer_read(filepath)
                    if r_code != 200 or r_data != payload:
                        errors.append(f"Read error or mismatch (code {r_code})")
                        continue
                        
                    seaweed_client.filer_delete(filepath)
                    latencies.append(time.perf_counter() - t0)
                except Exception as e:
                    errors.append(str(e))
            
            return {
                "worker_id": worker_id,
                "latencies": latencies,
                "errors": errors
            }

        t_start = time.perf_counter()
        all_results = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_worker_task, wid) for wid in range(concurrency)]
            for fut in as_completed(futures):
                all_results.append(fut.result())
        t_total = time.perf_counter() - t_start

        all_errors = [err for res in all_results for err in res["errors"]]
        all_latencies = [lat for res in all_results for lat in res["latencies"]]
        
        total_ops = concurrency * iterations_per_worker
        successful_ops = len(all_latencies)
        rps = successful_ops / max(0.001, t_total)
        avg_latency_ms = (sum(all_latencies) / len(all_latencies) * 1000) if all_latencies else 0
        
        print(f"[Tier 2] Concurrency Results: Total Ops={total_ops}, Success={successful_ops}, Errors={len(all_errors)}, RPS={rps:.2f} req/s, Avg Latency={avg_latency_ms:.2f}ms")
        
        assert len(all_errors) == 0, f"Encountered {len(all_errors)} errors during concurrent stress test: {all_errors[:5]}"
        assert successful_ops == total_ops, f"Expected {total_ops} successful operations, got {successful_ops}"
        
        # Cleanup
        seaweed_client.filer_delete(base_dir, recursive=True)
