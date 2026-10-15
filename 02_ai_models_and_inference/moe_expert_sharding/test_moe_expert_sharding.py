import pytest
import time
import threading
import numpy as np
from http.server import HTTPServer
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).parent))

from moe_expert_worker import MoEExpertServer, ExpertHTTPHandler, LocalExpertSlice
from moe_expert_router import MoERouter


@pytest.fixture(scope="module")
def start_all_local_moe_workers(tmp_path_factory):
    # Create test manifest mapping all 16 experts to local loopback ports
    test_manifest = {
        "topology_version": "test_2026",
        "total_experts": 16,
        "top_k_active": 2,
        "hidden_dim": 4096,
        "nodes": {
            "L1": {"ip": "127.0.0.1", "port": 50070, "assigned_experts": [0, 1, 2, 3]},
            "L2": {"ip": "127.0.0.1", "port": 50071, "assigned_experts": [4, 5, 6, 7]},
            "L3": {"ip": "127.0.0.1", "port": 50072, "assigned_experts": [8, 9, 10, 11]},
            "L4": {"ip": "127.0.0.1", "port": 50073, "assigned_experts": [12, 13, 14, 15]}
        }
    }
    manifest_dir = tmp_path_factory.mktemp("manifest")
    manifest_file = manifest_dir / "test_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(test_manifest, f)

    servers = []
    
    def run_srv(node_id, port, experts):
        s_obj = MoEExpertServer(node_id=node_id, port=port, assigned_experts=experts)
        class Handler(ExpertHTTPHandler):
            server_instance = s_obj
        httpd = HTTPServer(("127.0.0.1", port), Handler)
        servers.append(httpd)
        httpd.serve_forever()

    threads = [
        threading.Thread(target=run_srv, args=("L1", 50070, [0, 1, 2, 3]), daemon=True),
        threading.Thread(target=run_srv, args=("L2", 50071, [4, 5, 6, 7]), daemon=True),
        threading.Thread(target=run_srv, args=("L3", 50072, [8, 9, 10, 11]), daemon=True),
        threading.Thread(target=run_srv, args=("L4", 50073, [12, 13, 14, 15]), daemon=True),
    ]
    for t in threads:
        t.start()
    time.sleep(0.3)
    
    yield str(manifest_file)
    
    for s in servers:
        s.shutdown()


def test_local_expert_slice_computation():
    slice_obj = LocalExpertSlice(expert_id=1, hidden_dim=4096, intermediate_dim=2048)
    x = np.ones(4096, dtype=np.float32)
    y = slice_obj.forward(x)
    assert y.shape == (4096,)
    assert not np.isnan(y).any()
    assert float(np.linalg.norm(y)) > 0.0


def test_moe_router_top_k_gating(start_all_local_moe_workers):
    manifest_path = start_all_local_moe_workers
    router = MoERouter(manifest_path=manifest_path)
    x = np.random.randn(4096).astype(np.float32)
    selected_experts, weights = router.route_token(x)
    
    assert len(selected_experts) == 2
    assert len(weights) == 2
    assert np.isclose(np.sum(weights), 1.0, atol=1e-4)


def test_moe_end_to_end_activation_dispatch(start_all_local_moe_workers):
    manifest_path = start_all_local_moe_workers
    router = MoERouter(manifest_path=manifest_path)
    x = np.random.randn(4096).astype(np.float32)
    
    # Warmup
    _ = router.forward_moe_layer(x)
    
    # Measure live latency
    res = router.forward_moe_layer(x)
    assert "selected_experts" in res
    assert "weights" in res
    assert "payload_bytes_sent" in res
    assert res["payload_bytes_sent"] == 4096 * 4  # 16 KB FP32
    assert res["total_latency_ms"] < 15.0  # Ultra-low sub-15ms local latency
    assert res["output_norm"] > 0.0
