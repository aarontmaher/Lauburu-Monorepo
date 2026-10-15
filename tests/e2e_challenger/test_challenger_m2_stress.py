"""
Adversarial Stress Test Suite for Milestone 2: Swarm Node & Tailscale Binding
Challenger: challenger_m2_1
Target: Pixel 10 Pro XL (100.73.38.87) via SSH (8022) and Tailscale Ports (31330, 50052)
"""

import json
import time
import socket
import statistics
import concurrent.futures
import subprocess
from typing import Dict, List, Tuple, Any

PIXEL_HOST = "100.73.38.87"
PIXEL_SSH_PORT = 8022
RPC_PORT = 50052
DHT_PORT = 31330
PEER_ID = "QmRbXmTEWgBytkrptKvoDHUjPKutFfQBBWzCM8fC3Db2gr"
PEER_MADDR = f"/ip4/{PIXEL_HOST}/tcp/{DHT_PORT}/p2p/{PEER_ID}"


def run_pixel_ssh(cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
    """Run command on Pixel via SSH."""
    proc = subprocess.run(
        [
            "ssh", "-p", str(PIXEL_SSH_PORT),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", f"ConnectTimeout={min(timeout, 10)}",
            PIXEL_HOST,
            cmd
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def probe_tcp(host: str, port: int, timeout: float = 5.0) -> Tuple[bool, float]:
    """Probe TCP connection and return (success, rtt_ms)."""
    t0 = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            rtt = (time.perf_counter() - t0) * 1000.0
            return (res == 0, rtt)
    except Exception:
        return (False, -1.0)


def stress_test_rpc_monitor(stop_event, interval_sec: float = 0.5) -> Dict[str, Any]:
    """Continuously probe RPC server port 50052 during stress testing until stop_event is set."""
    rtts = []
    failures = 0
    total_probes = 0
    while not stop_event.is_set():
        total_probes += 1
        ok, rtt = probe_tcp(PIXEL_HOST, RPC_PORT, timeout=5.0)
        if ok:
            rtts.append(rtt)
        else:
            failures += 1
        time.sleep(interval_sec)
    
    return {
        "total_probes": total_probes,
        "successful_probes": len(rtts),
        "failed_probes": failures,
        "success_rate": (len(rtts) / total_probes * 100.0) if total_probes > 0 else 0.0,
        "min_rtt_ms": min(rtts) if rtts else -1,
        "mean_rtt_ms": statistics.mean(rtts) if rtts else -1,
        "max_rtt_ms": max(rtts) if rtts else -1,
        "stddev_rtt_ms": statistics.stdev(rtts) if len(rtts) > 1 else 0.0,
    }




def run_pixel_python(script_code: str, timeout: int = 90) -> Tuple[int, str, str]:
    """Execute Python code on Pixel via SSH using base64 stdin to avoid quote escaping issues."""
    import base64
    b64_script = base64.b64encode(script_code.encode("utf-8")).decode("ascii")
    cmd = f"echo {b64_script} | base64 -d | python3"
    return run_pixel_ssh(cmd, timeout=timeout)


def execute_dht_20_op_churn_on_pixel() -> Dict[str, Any]:
    """
    Execute 20 concurrent store/get operations on Pixel DHT node and collect empirical telemetry.
    """
    python_code = """
import time
import json
import concurrent.futures
import hivemind
import petals_peer

peer_maddr = petals_peer.PEER_MADDR
results = {
    "peer_maddr": peer_maddr,
    "operations": [],
    "total_ops": 20,
    "store_success_count": 0,
    "get_success_count": 0,
    "consistency_pass_count": 0,
    "errors": []
}

# Connect DHT client to the local node
try:
    dht = hivemind.DHT(initial_peers=[peer_maddr], start=True, client_mode=True)
except Exception as e:
    results["errors"].append(f"DHT init failed: {str(e)}")
    print(json.dumps(results))
    exit(0)

# Generate 20 test vectors
test_vectors = []
for i in range(20):
    key = f"churn_key_{i}_{int(time.time()*1000)}"
    if i % 4 == 0:
        val = f"simple_value_{i}"
    elif i % 4 == 1:
        val = json.dumps({"op_index": i, "tensor_shape": [128, 128], "status": "active", "timestamp": time.time()})
    elif i % 4 == 2:
        val = "B64PAYLOAD_" + ("XYZ1234567890ABCDEF" * (i + 1))
    else:
        val = f"utf8_payload_{i}_ok_tensor_alpha_beta"
    test_vectors.append((i, key, val))

# Execute concurrent store operations
def do_store(item):
    idx, k, v = item
    t0 = time.perf_counter()
    try:
        ok = dht.store(k, v, expiration_time=time.time() + 60)
        dt = (time.perf_counter() - t0) * 1000.0
        return (idx, k, v, ok, dt, None)
    except Exception as e:
        return (idx, k, v, False, (time.perf_counter() - t0) * 1000.0, str(e))

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    store_res = list(ex.map(do_store, test_vectors))

# Execute concurrent get operations
def do_get(store_item):
    idx, k, expected_val, store_ok, store_dt, store_err = store_item
    if not store_ok:
        return {
            "index": idx,
            "key": k,
            "expected_val": expected_val,
            "store_ok": False,
            "store_time_ms": store_dt,
            "store_error": store_err,
            "get_ok": False,
            "consistent": False
        }
    t0 = time.perf_counter()
    try:
        retrieved = dht.get(k, latest=True)
        get_dt = (time.perf_counter() - t0) * 1000.0
        if retrieved is None:
            return {
                "index": idx,
                "key": k,
                "expected_val": expected_val,
                "store_ok": True,
                "store_time_ms": store_dt,
                "get_ok": False,
                "get_time_ms": get_dt,
                "consistent": False,
                "error": "Retrieved value is None"
            }
        val_matches = (retrieved.value == expected_val)
        return {
            "index": idx,
            "key": k,
            "expected_val": expected_val,
            "retrieved_val": retrieved.value,
            "store_ok": True,
            "store_time_ms": store_dt,
            "get_ok": True,
            "get_time_ms": get_dt,
            "consistent": val_matches,
            "expiration_valid": (retrieved.expiration_time > time.time())
        }
    except Exception as e:
        return {
            "index": idx,
            "key": k,
            "expected_val": expected_val,
            "store_ok": True,
            "store_time_ms": store_dt,
            "get_ok": False,
            "get_time_ms": (time.perf_counter() - t0) * 1000.0,
            "consistent": False,
            "error": str(e)
        }

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    get_res = list(ex.map(do_get, store_res))

dht.shutdown()

results["operations"] = get_res
results["store_success_count"] = sum(1 for r in get_res if r.get("store_ok", False))
results["get_success_count"] = sum(1 for r in get_res if r.get("get_ok", False))
results["consistency_pass_count"] = sum(1 for r in get_res if r.get("consistent", False))

print(json.dumps(results))
"""
    code, out, err = run_pixel_python(python_code, timeout=90)
    if code != 0:
        return {"error": f"SSH execution failed: {err}", "stdout": out}
    try:
        lines = [l for l in out.strip().split('\n') if l.startswith('{')]
        json_line = lines[-1]
        return json.loads(json_line)
    except Exception as e:
        return {"error": f"JSON parsing failed: {str(e)}", "raw_output": out}


def execute_routing_traversal_test_on_pixel() -> Dict[str, Any]:
    """
    Execute Kademlia routing table traversal under load.
    """
    python_code = """
import time
import json
import random
import hashlib
import hivemind
import petals_peer

peer_maddr = petals_peer.PEER_MADDR
results = {
    "visible_maddrs": [],
    "routing_lookups": [],
    "total_lookups": 10,
    "successful_lookups": 0,
    "avg_lookup_ms": 0.0,
    "errors": []
}

try:
    dht = hivemind.DHT(initial_peers=[peer_maddr], start=True, client_mode=True)
    maddrs = [str(m) for m in dht.get_visible_maddrs()]
    results["visible_maddrs"] = maddrs
except Exception as e:
    results["errors"].append(f"Init error: {str(e)}")
    print(json.dumps(results))
    exit(0)

# Perform 10 lookups for various key spaces
lookup_times = []
for i in range(10):
    rand_key = hashlib.sha256(f"random_routing_key_{i}_{time.time()}_{random.random()}".encode()).hexdigest()
    t0 = time.perf_counter()
    try:
        res = dht.get(rand_key, latest=True)
        dt = (time.perf_counter() - t0) * 1000.0
        lookup_times.append(dt)
        results["routing_lookups"].append({
            "key": rand_key,
            "lookup_ms": dt,
            "found": res is not None,
            "status": "clean_traversal"
        })
        results["successful_lookups"] += 1
    except Exception as e:
        results["routing_lookups"].append({
            "key": rand_key,
            "error": str(e),
            "status": "error"
        })

dht.shutdown()
if lookup_times:
    results["avg_lookup_ms"] = sum(lookup_times) / len(lookup_times)

print(json.dumps(results))
"""
    code, out, err = run_pixel_python(python_code, timeout=60)
    if code != 0:
        return {"error": f"SSH execution failed: {err}", "stdout": out}
    try:
        lines = [l for l in out.strip().split('\n') if l.startswith('{')]
        return json.loads(lines[-1])
    except Exception as e:
        return {"error": f"JSON parsing failed: {str(e)}", "raw_output": out}



import threading

def test_adversarial_m2_suite():
    """Run the complete stress test suite."""
    print("=== STARTING ADVERSARIAL STRESS TEST SUITE ===")
    
    # Check RPC PID before
    code, rpc_pid_before, _ = run_pixel_ssh("pgrep -f 'rpc-server' | head -n 1")
    assert code == 0 and len(rpc_pid_before) > 0, f"RPC server not running before test: {rpc_pid_before}"
    print(f"[1/5] RPC Server active on PID: {rpc_pid_before}")
    
    # 2. Concurrently run RPC monitor and DHT 20-op churn
    print("[2/5] Launching concurrent 20-op DHT KV churn and RPC server ping monitor...")
    stop_event = threading.Event()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_rpc = executor.submit(stress_test_rpc_monitor, stop_event, interval_sec=0.2)
        try:
            dht_results = execute_dht_20_op_churn_on_pixel()
        finally:
            stop_event.set()
        rpc_metrics = f_rpc.result()

    
    print("DHT Churn Results:", json.dumps(dht_results, indent=2))
    print("RPC Server Metrics during Churn:", json.dumps(rpc_metrics, indent=2))
    
    assert "error" not in dht_results, f"DHT churn encountered error: {dht_results.get('error')}"
    assert dht_results.get("store_success_count") == 20, f"Expected 20 stores, got {dht_results.get('store_success_count')}"
    assert dht_results.get("get_success_count") == 20, f"Expected 20 gets, got {dht_results.get('get_success_count')}"
    assert dht_results.get("consistency_pass_count") == 20, f"Expected 20 consistent values, got {dht_results.get('consistency_pass_count')}"
    
    assert rpc_metrics["failed_probes"] == 0, f"RPC probes failed during DHT churn: {rpc_metrics['failed_probes']}"
    assert rpc_metrics["success_rate"] == 100.0, f"RPC success rate dropped below 100%: {rpc_metrics['success_rate']}%"
    print(f"[PASS] 20/20 DHT KV operations 100% consistent! RPC server 100% available (mean RTT: {rpc_metrics['mean_rtt_ms']:.2f}ms)")
    
    # 3. Routing Table Traversal under load
    print("[3/5] Launching Kademlia routing table traversal under load...")
    routing_results = execute_routing_traversal_test_on_pixel()
    print("Routing Results:", json.dumps(routing_results, indent=2))
    assert "error" not in routing_results, f"Routing traversal error: {routing_results.get('error')}"
    assert routing_results.get("successful_lookups") == 10, f"Routing lookups failed: {routing_results}"
    print(f"[PASS] 10/10 routing table traversals completed cleanly (avg RTT: {routing_results.get('avg_lookup_ms'):.2f}ms)")
    
    # 4. Check RPC PID after
    code, rpc_pid_after, _ = run_pixel_ssh("pgrep -f 'rpc-server' | head -n 1")
    assert code == 0 and rpc_pid_before == rpc_pid_after, f"RPC server crashed or restarted! Before: {rpc_pid_before}, After: {rpc_pid_after}"
    print(f"[4/5] RPC Server PID strictly preserved: {rpc_pid_after}")
    
    # 5. Process memory and resource audit
    code, mem_info, _ = run_pixel_ssh("ps -o pid,user,rss,vsz,comm -C ggml-rpc-server,python3,p2pd")
    print(f"[5/5] Resource footprint:\n{mem_info}")
    
    print("=== ALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    test_adversarial_m2_suite()
