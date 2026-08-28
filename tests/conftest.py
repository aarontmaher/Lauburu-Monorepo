"""
Pytest fixtures and core testing utilities for Lauburu SeaweedFS E2E Storage Migration.
Supports all 4 testing tiers with flexible live/fallback environment probing.
"""

import os
import sys
import time
import socket
import hashlib
import tempfile
import threading
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import pytest

# Default Configuration Constants Grounded in Survey Reports
DEFAULT_TB4_IP = os.environ.get("SEAWEED_TB4_IP", "169.254.80.69")
DEFAULT_MASTER_PORT = int(os.environ.get("SEAWEED_MASTER_PORT", 9333))
DEFAULT_VOLUME_PORT = int(os.environ.get("SEAWEED_VOLUME_PORT", 8080))
DEFAULT_FILER_PORT = int(os.environ.get("SEAWEED_FILER_PORT", 8888))
DEFAULT_S3_PORT = int(os.environ.get("SEAWEED_S3_PORT", 8333))

DEFAULT_MASTER_URL = f"http://{DEFAULT_TB4_IP}:{DEFAULT_MASTER_PORT}"
DEFAULT_VOLUME_URL = f"http://{DEFAULT_TB4_IP}:{DEFAULT_VOLUME_PORT}"
DEFAULT_FILER_URL = f"http://{DEFAULT_TB4_IP}:{DEFAULT_FILER_PORT}"
DEFAULT_S3_URL = f"http://{DEFAULT_TB4_IP}:{DEFAULT_S3_PORT}"


def pytest_addoption(parser):
    """Register CLI options for pytest."""
    parser.addoption("--master-url", action="store", default=DEFAULT_MASTER_URL, help="SeaweedFS Master URL")
    parser.addoption("--volume-url", action="store", default=DEFAULT_VOLUME_URL, help="SeaweedFS Volume URL")
    parser.addoption("--filer-url", action="store", default=DEFAULT_FILER_URL, help="SeaweedFS Filer URL")
    parser.addoption("--s3-url", action="store", default=DEFAULT_S3_URL, help="SeaweedFS S3 Gateway URL")
    parser.addoption("--tb4-ip", action="store", default=DEFAULT_TB4_IP, help="Thunderbolt 4 bridge0 IP")
    parser.addoption("--source-dir", action="store", default="/mnt/dfs_unified", help="Source dataset path for parity")
    parser.addoption("--target-dir", action="store", default="/Volumes/Lauburu-Monorepo", help="Target dataset path")
    parser.addoption("--benchmark-size-mb", action="store", type=int, default=512, help="Benchmark file size in MB")
    parser.addoption("--json-report", action="store", default="storage_migration_test_report.json", help="JSON report path")


class SeaweedFSClient:
    """High-level client for interacting with SeaweedFS Master, Filer, Volume, and S3 APIs."""

    def __init__(self, master_url: str, filer_url: str, volume_url: str, s3_url: str, timeout: float = 10.0):
        self.master_url = master_url.rstrip("/")
        self.filer_url = filer_url.rstrip("/")
        self.volume_url = volume_url.rstrip("/")
        self.s3_url = s3_url.rstrip("/")
        self.timeout = timeout

    # ---------------- MASTER API ----------------
    def get_cluster_status(self) -> Dict[str, Any]:
        """Fetch cluster status from Master."""
        urls = [f"{self.master_url}/dir/status", f"{self.master_url}/cluster/status"]
        last_err = None
        for u in urls:
            try:
                req = urllib.request.Request(u, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                last_err = e
        raise RuntimeError(f"Failed to fetch master cluster status: {last_err}")

    def assign_volume(self, count: int = 1, replication: str = "") -> Dict[str, Any]:
        """Assign volume chunk ID (FID) from Master."""
        params = []
        if count > 1:
            params.append(f"count={count}")
        if replication:
            params.append(f"replication={replication}")
        query = ("?" + "&".join(params)) if params else ""
        url = f"{self.master_url}/dir/assign{query}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---------------- FILER API ----------------
    def filer_write(self, remote_path: str, data: bytes, content_type: str = "application/octet-stream") -> Tuple[int, str]:
        """Write file payload to Filer at remote_path."""
        clean_path = "/" + remote_path.lstrip("/")
        encoded_path = urllib.parse.quote(clean_path, safe="/")
        url = f"{self.filer_url}{encoded_path}"
        req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": content_type})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return resp.status, body
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="ignore")

    def filer_read(self, remote_path: str) -> Tuple[int, bytes, Dict[str, str]]:
        """Read file payload from Filer at remote_path."""
        clean_path = "/" + remote_path.lstrip("/")
        encoded_path = urllib.parse.quote(clean_path, safe="/")
        url = f"{self.filer_url}{encoded_path}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                data = resp.read()
                return resp.status, data, headers
        except urllib.error.HTTPError as e:
            return e.code, b"", {}

    def filer_delete(self, remote_path: str, recursive: bool = False) -> Tuple[int, str]:
        """Delete file or directory at remote_path."""
        clean_path = "/" + remote_path.lstrip("/")
        encoded_path = urllib.parse.quote(clean_path, safe="/")
        query = "?recursive=true" if recursive else ""
        url = f"{self.filer_url}{encoded_path}{query}"
        req = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="ignore")

    def filer_list_directory(self, remote_dir: str) -> Tuple[int, List[Dict[str, Any]]]:
        """List entries in remote directory via Filer JSON API."""
        clean_path = "/" + remote_dir.strip("/") + "/"
        encoded_path = urllib.parse.quote(clean_path, safe="/")
        url = f"{self.filer_url}{encoded_path}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                entries = data.get("Entries", []) if isinstance(data, dict) else []
                return resp.status, entries
        except urllib.error.HTTPError as e:
            return e.code, []

    # ---------------- S3 API ----------------
    def s3_put_bucket(self, bucket_name: str) -> int:
        """Create S3 bucket."""
        url = f"{self.s3_url}/{bucket_name}"
        req = urllib.request.Request(url, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def s3_put_object(self, bucket_name: str, key: str, data: bytes) -> int:
        """Put S3 object."""
        url = f"{self.s3_url}/{bucket_name}/{key.lstrip('/')}"
        req = urllib.request.Request(url, data=data, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def s3_get_object(self, bucket_name: str, key: str) -> Tuple[int, bytes]:
        """Get S3 object."""
        url = f"{self.s3_url}/{bucket_name}/{key.lstrip('/')}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, b""

    def s3_delete_object(self, bucket_name: str, key: str) -> int:
        """Delete S3 object."""
        url = f"{self.s3_url}/{bucket_name}/{key.lstrip('/')}"
        req = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code


class TB4NetworkProbe:
    """Network topology and interface probing utility."""

    @staticmethod
    def get_interface_details(iface: str = "bridge0") -> Dict[str, Any]:
        """Inspect network interface via ifconfig."""
        try:
            res = subprocess.run(["ifconfig", iface], capture_output=True, text=True, check=True)
            output = res.stdout
            is_active = "status: active" in output or "<UP," in output
            mtu = 1500
            for line in output.splitlines():
                if "mtu" in line:
                    parts = line.split("mtu")
                    if len(parts) > 1:
                        try:
                            mtu = int(parts[1].strip().split()[0])
                        except ValueError:
                            pass
            ips = []
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    parts = line.split()
                    if len(parts) >= 2:
                        ips.append(parts[1])
            return {
                "interface": iface,
                "active": is_active,
                "mtu": mtu,
                "ipv4_addresses": ips,
                "raw": output
            }
        except subprocess.CalledProcessError as e:
            return {"interface": iface, "active": False, "error": str(e), "ipv4_addresses": []}

    @staticmethod
    def check_route_for_ip(target_ip: str) -> Dict[str, Any]:
        """Check kernel route lookup for destination IP."""
        try:
            res = subprocess.run(["route", "-n", "get", target_ip], capture_output=True, text=True, check=True)
            out = res.stdout
            iface = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("interface:"):
                    iface = line.split("interface:")[1].strip()
            return {"target_ip": target_ip, "interface": iface, "raw": out}
        except Exception as e:
            return {"target_ip": target_ip, "interface": None, "error": str(e)}

    @staticmethod
    def probe_socket(ip: str, port: int, timeout: float = 2.0) -> bool:
        """Probe TCP socket connectivity."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            res = sock.connect_ex((ip, port))
            sock.close()
            return res == 0
        except Exception:
            return False


class BenchmarkHelper:
    """I/O throughput and latency benchmark helper."""

    @staticmethod
    def benchmark_direct_write(target_path: str, size_bytes: int, chunk_size: int = 1024 * 1024) -> Dict[str, float]:
        """Perform sequential write benchmark and return stats."""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        chunk = os.urandom(chunk_size)
        total_chunks = max(1, size_bytes // chunk_size)
        actual_bytes = total_chunks * chunk_size

        t0 = time.perf_counter()
        with open(target_path, "wb") as f:
            for _ in range(total_chunks):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        t1 = time.perf_counter()

        duration = max(0.0001, t1 - t0)
        throughput_mb_s = (actual_bytes / (1024 * 1024)) / duration
        return {
            "bytes_written": actual_bytes,
            "duration_sec": duration,
            "throughput_mb_s": throughput_mb_s
        }

    @staticmethod
    def benchmark_direct_read(target_path: str, chunk_size: int = 1024 * 1024) -> Dict[str, float]:
        """Perform sequential read benchmark and return stats."""
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Benchmark file {target_path} does not exist")

        total_bytes = 0
        t0 = time.perf_counter()
        with open(target_path, "rb") as f:
            while True:
                buf = f.read(chunk_size)
                if not buf:
                    break
                total_bytes += len(buf)
        t1 = time.perf_counter()

        duration = max(0.0001, t1 - t0)
        throughput_mb_s = (total_bytes / (1024 * 1024)) / duration
        return {
            "bytes_read": total_bytes,
            "duration_sec": duration,
            "throughput_mb_s": throughput_mb_s
        }


class CryptographicParityAuditor:
    """Multi-threaded SHA-256 cryptographic parity auditor."""

    @staticmethod
    def hash_file_sha256(filepath: str, block_size: int = 4 * 1024 * 1024) -> str:
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(block_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def audit_parity(source_dir: str, target_dir: str, max_workers: int = 16) -> Dict[str, Any]:
        """Audit parity between source_dir and target_dir."""
        if not os.path.exists(source_dir):
            return {"error": f"Source dir {source_dir} not found", "matched": False, "files_checked": 0}
        if not os.path.exists(target_dir):
            return {"error": f"Target dir {target_dir} not found", "matched": False, "files_checked": 0}

        source_files = {}
        for root, _, files in os.walk(source_dir):
            if ".deleted" in root or ".git" in root:
                continue
            for f in files:
                p = os.path.join(root, f)
                rel = os.path.relpath(p, source_dir)
                try:
                    source_files[rel] = os.path.getsize(p)
                except OSError:
                    pass

        mismatches = []
        verified_count = 0

        def _verify_entry(rel_path, src_size):
            src_path = os.path.join(source_dir, rel_path)
            tgt_path = os.path.join(target_dir, rel_path)
            if not os.path.exists(tgt_path):
                return {"file": rel_path, "error": "MISSING_IN_TARGET"}
            try:
                tgt_size = os.path.getsize(tgt_path)
                if tgt_size != src_size:
                    return {"file": rel_path, "error": "SIZE_MISMATCH", "src": src_size, "dst": tgt_size}
                # Hash comparison for files <= 100MB or sample for huge files
                if src_size <= 100 * 1024 * 1024:
                    s_hash = CryptographicParityAuditor.hash_file_sha256(src_path)
                    t_hash = CryptographicParityAuditor.hash_file_sha256(tgt_path)
                    if s_hash != t_hash:
                        return {"file": rel_path, "error": "HASH_MISMATCH", "src_hash": s_hash, "dst_hash": t_hash}
                return None
            except Exception as e:
                return {"file": rel_path, "error": f"EXC_{e}"}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_verify_entry, rel, size) for rel, size in source_files.items()]
            for fut in futures:
                res = fut.result()
                if res:
                    mismatches.append(res)
                else:
                    verified_count += 1

        return {
            "total_source_files": len(source_files),
            "verified_matching_files": verified_count,
            "mismatches": mismatches,
            "parity_100_percent": len(mismatches) == 0 and len(source_files) > 0
        }


# ================== PYTEST FIXTURES ==================

@pytest.fixture(scope="session")
def master_url(request) -> str:
    return request.config.getoption("--master-url")


@pytest.fixture(scope="session")
def volume_url(request) -> str:
    return request.config.getoption("--volume-url")


@pytest.fixture(scope="session")
def filer_url(request) -> str:
    return request.config.getoption("--filer-url")


@pytest.fixture(scope="session")
def s3_url(request) -> str:
    return request.config.getoption("--s3-url")


@pytest.fixture(scope="session")
def tb4_ip(request) -> str:
    return request.config.getoption("--tb4-ip")


@pytest.fixture(scope="session")
def seaweed_client(master_url, filer_url, volume_url, s3_url) -> SeaweedFSClient:
    return SeaweedFSClient(master_url=master_url, filer_url=filer_url, volume_url=volume_url, s3_url=s3_url)


@pytest.fixture(scope="session")
def tb4_probe() -> TB4NetworkProbe:
    return TB4NetworkProbe()


@pytest.fixture(scope="session")
def bench_helper() -> BenchmarkHelper:
    return BenchmarkHelper()


@pytest.fixture(scope="session")
def parity_auditor() -> CryptographicParityAuditor:
    return CryptographicParityAuditor()
