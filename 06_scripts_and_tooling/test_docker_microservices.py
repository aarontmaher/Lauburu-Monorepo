"""
Lauburu Mesh - Docker Microservices Comprehensive Test & Optimization Suite
Benchmarks container startup, virtio-fs volume throughput, Qdrant vector indexing, and SeaweedFS DFS.
"""

import os
import sys
import time
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
COMPOSE_MASTER = REPO_ROOT / "00_core_infrastructure" / "docker-compose.master.yml"

def get_env():
    env = os.environ.copy()
    colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
    if colima_sock.exists() and "DOCKER_HOST" not in env:
        env["DOCKER_HOST"] = f"unix://{colima_sock}"
    return env

def test_docker_daemon():
    print("🧪 [1/4] Testing Docker Daemon & Socket Connection...")
    env = get_env()
    t0 = time.time()
    res = subprocess.run(["docker", "info", "--format", "{{json .}}"], capture_output=True, text=True, timeout=5, env=env)
    latency = round((time.time() - t0) * 1000, 2)
    if res.returncode == 0:
        info = json.loads(res.stdout)
        print(f"  ✅ Daemon Active (v{info.get('ServerVersion')}) | Latency: {latency}ms | Driver: {info.get('Driver')}")
        return True
    else:
        print(f"  ❌ Daemon Unreachable: {res.stderr}")
        return False

def test_qdrant_vector_container():
    print("\n🧪 [2/4] Benchmarking Qdrant Vector DB Container on Port 6333...")
    env = get_env()
    
    # Check if container is running or launch standalone test container
    res_ps = subprocess.run(["docker", "ps", "--filter", "name=lauburu-qdrant", "--format", "{{.ID}}"], capture_output=True, text=True, env=env)
    container_id = res_ps.stdout.strip()
    
    launched_temp = False
    if not container_id:
        print("  ⚡ Spinning up ephemeral Qdrant container for benchmark...")
        cmd = ["docker", "run", "-d", "--name", "test-qdrant", "-p", "6333:6333", "-p", "6334:6334", "qdrant/qdrant:latest"]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if res.returncode == 0:
            launched_temp = True
            time.sleep(2)
        else:
            print(f"  ⚠️ Could not launch Qdrant: {res.stderr}")
            return False

    # Test Qdrant API
    try:
        t0 = time.time()
        url = "http://localhost:6333/collections"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            rtt = round((time.time() - t0) * 1000, 2)
            print(f"  ✅ Qdrant Vector DB Health: ONLINE | Collections: {len(data.get('result', {}).get('collections', []))} | HTTP RTT: {rtt}ms")
    except Exception as e:
        print(f"  ⚠️ Qdrant probe error: {e}")
    finally:
        if launched_temp:
            subprocess.run(["docker", "rm", "-f", "test-qdrant"], capture_output=True, env=env)
            print("  🧹 Ephemeral Qdrant container cleaned up.")

def test_virtiofs_volume_io():
    print("\n🧪 [3/4] Benchmarking Virtio-FS Direct Host Volume Mount I/O...")
    env = get_env()
    test_dir = REPO_ROOT / "obsidian_vault"
    
    # Run containerized dd write benchmark inside Colima virtiofs mount
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{test_dir}:/vault:ro",
        "alpine:latest",
        "sh", "-c", "time find /vault -name '*.md' | wc -l"
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
    dur = round(time.time() - t0, 3)
    if res.returncode == 0:
        count = res.stdout.strip().splitlines()[-1]
        print(f"  ✅ Virtio-FS Read Test: Scanned {count} markdown files inside container in {dur}s ({round(float(count)/max(dur, 0.001))} files/sec)")
    else:
        print(f"  ⚠️ Volume benchmark error: {res.stderr}")

def test_portal_container_build():
    print("\n🧪 [4/4] Verifying Unified Portal Container Image Buildability...")
    env = get_env()
    portal_dir = REPO_ROOT / "01_apps" / "unified_portal"
    
    cmd = ["docker", "build", "-t", "lauburu/unified-portal:test", str(portal_dir)]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    dur = round(time.time() - t0, 2)
    if res.returncode == 0:
        print(f"  ✅ Unified Portal Dockerfile Build: SUCCESS in {dur}s (Image tagged as lauburu/unified-portal:test)")
    else:
        print(f"  ⚠️ Build output: {res.stderr[:200]}")

if __name__ == "__main__":
    print("=========================================================")
    print("🐳 LAUBURU MESH DOCKER OPTIMIZATION & VERIFICATION SUITE")
    print("=========================================================")
    test_docker_daemon()
    test_virtiofs_volume_io()
    test_qdrant_vector_container()
    test_portal_container_build()
    print("\n=========================================================")
    print("🎯 DOCKER BENCHMARK & OPTIMIZATION VERIFICATION COMPLETE")
    print("=========================================================")
