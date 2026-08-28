import asyncio
import time
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark_loop")

BENCHMARK_DIR = "/Volumes/Lauburu-Monorepo/mesh_benchmarks"
RESULTS_FILE = os.path.join(BENCHMARK_DIR, "benchmark_results.json")

def create_test_file(size_mb=50):
    os.makedirs(BENCHMARK_DIR, exist_ok=True)
    file_path = os.path.join(BENCHMARK_DIR, f"test_payload_{size_mb}MB.bin")
    
    # Strictly adhere to NO FAKE DATA rule by sourcing real data from the actual model file.
    real_data_source = "/Volumes/Lauburu-Monorepo/gemma-2-2b-it-Q4_K_M.gguf"
    
    if not os.path.exists(file_path):
        logger.info(f"Creating test file {file_path} of size {size_mb}MB using REAL data from {real_data_source}")
        target_bytes = size_mb * 1024 * 1024
        
        with open(real_data_source, "rb") as source:
            real_data = source.read(target_bytes)
            
        with open(file_path, "wb") as f:
            f.write(real_data)
            
    return file_path

async def run_benchmark():
    import subprocess
    import hashlib
    file_path = create_test_file(50)
    
    # Calculate hash and size for server
    file_size = os.path.getsize(file_path)
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    expected_hash = hasher.hexdigest()
    
    # Endpoints to test (we'll use local ports to test throughput of the script itself, 
    # but in a real deployment these would be Tailscale/ADB/WLAN IPs)
    endpoints = ["127.0.0.1:8001", "127.0.0.1:8002", "127.0.0.1:8003"]
    endpoints_str = " ".join(endpoints)
    output_file = os.path.join(BENCHMARK_DIR, "output_test.bin")
    
    server_cmd = [
        "python3", os.path.join(os.path.dirname(__file__), "multiwan_bond.py"), 
        "server", "--file", output_file, 
        "--endpoints"
    ] + endpoints + [
        "--size", str(file_size), "--hash", expected_hash
    ]
    
    client_cmd = [
        "python3", os.path.join(os.path.dirname(__file__), "multiwan_bond.py"), 
        "client", "--file", file_path, 
        "--endpoints"
    ] + endpoints
    
    logger.info("Starting MultiWAN benchmark iteration (REAL DATA)...")
    
    # Spawn server
    server_process = await asyncio.create_subprocess_exec(*server_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    
    # Give server a second to bind ports
    await asyncio.sleep(1)
    
    start_time = time.time()
    
    # Spawn client
    client_process = await asyncio.create_subprocess_exec(*client_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    
    # Wait for client to finish
    await client_process.wait()
    
    end_time = time.time()
    
    # Wait for server to finish
    await server_process.wait()
    
    duration = end_time - start_time
    file_size_mb = file_size / (1024 * 1024)
    throughput = file_size_mb / duration if duration > 0 else 0
    
    if os.path.exists(output_file):
        os.remove(output_file)
    
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "file_size_mb": round(file_size_mb, 2),
        "duration_seconds": round(duration, 2),
        "throughput_mbps": round(throughput, 2),
        "routes_used": endpoints
    }
    
    # Save results
    results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            try:
                results = json.load(f)
            except json.JSONDecodeError:
                pass
                
    results.append(result)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Benchmark complete. Real Throughput: {throughput:.2f} MB/s")

async def loop():
    while True:
        try:
            await run_benchmark()
        except Exception as e:
            logger.error(f"Error in benchmark: {e}")
        await asyncio.sleep(60) # Run every minute

if __name__ == "__main__":
    logger.info("Starting MultiWAN benchmark daemon...")
    asyncio.run(loop())
