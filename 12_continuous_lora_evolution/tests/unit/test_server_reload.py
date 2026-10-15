"""
Unit Tests for Inference Server Hot-Reload Sentinel (Feature F15).
Tests zero-downtime routing, health probing, failover handshakes across ports
8081, 8082, 8083, and flap-resistant health verification.
"""

import unittest
from typing import Any, Dict

from src.orchestration.server_reload_sentinel import (
    PORT_LLAMA_RPC,
    PORT_PRIMA_PRP,
    PORT_PROXY_ROUTER,
    DEFAULT_CLUSTER_PORTS,
    ServerHealthStatus,
    ServerReloadSentinel,
    check_cluster_health,
    probe_server_health,
    reload_inference_cluster,
)


class TestServerReloadSentinel(unittest.TestCase):
    """Test suite for inference cluster server reload and health probing."""

    def test_cluster_port_mappings(self):
        """Verifies cluster port mappings (8081, 8082, 8083)."""
        self.assertEqual(PORT_LLAMA_RPC, 8081)
        self.assertEqual(PORT_PRIMA_PRP, 8082)
        self.assertEqual(PORT_PROXY_ROUTER, 8083)
        self.assertEqual(DEFAULT_CLUSTER_PORTS["llama_rpc"], 8081)
        self.assertEqual(DEFAULT_CLUSTER_PORTS["prima_prp"], 8082)
        self.assertEqual(DEFAULT_CLUSTER_PORTS["proxy_router"], 8083)

    def test_health_status_dataclass(self):
        """ServerHealthStatus stores and serializes health check information."""
        status = ServerHealthStatus(
            port=8082,
            host="127.0.0.1",
            status="HEALTHY",
            code=200,
            response_time_ms=1.45,
            details={"model": "qwen38_dare_ties"},
        )
        d = status.to_dict()
        self.assertEqual(d["port"], 8082)
        self.assertEqual(d["status"], "HEALTHY")
        self.assertEqual(d["code"], 200)

    def test_validate_port_boundaries(self):
        """validate_port correctly checks port ranges (1 to 65535)."""
        sentinel = ServerReloadSentinel()
        self.assertTrue(sentinel.validate_port(8082))
        self.assertTrue(sentinel.validate_port(1))
        self.assertTrue(sentinel.validate_port(65535))
        self.assertFalse(sentinel.validate_port(0))
        self.assertFalse(sentinel.validate_port(-1))
        self.assertFalse(sentinel.validate_port(70000))
        self.assertFalse(sentinel.validate_port("8082"))  # type: ignore

    def test_probe_health_connection_refused(self):
        """probe_health cleanly reports CONNECTION_REFUSED without unhandled exceptions."""
        sentinel = ServerReloadSentinel(health_timeout_sec=0.2)
        # Port 59999 is unlikely to be listening
        res = sentinel.probe_health(port=59999)
        self.assertIn(res["status"], ("CONNECTION_REFUSED", "TIMEOUT", "ERROR"))
        self.assertEqual(res["code"], 0)

    def test_failover_and_restoration_route_latching(self):
        """Sentinel handles failover to fallback (8081) and restoration to primary (8082)."""
        sentinel = ServerReloadSentinel(primary_port=8082, fallback_port=8081)
        self.assertEqual(sentinel.active_route, 8082)
        self.assertFalse(sentinel.is_failover_active)

        # Trigger failover
        sentinel.failover_to_fallback()
        self.assertEqual(sentinel.active_route, 8081)
        self.assertTrue(sentinel.is_failover_active)

        # Restore primary
        sentinel.restore_primary_route()
        self.assertEqual(sentinel.active_route, 8082)
        self.assertFalse(sentinel.is_failover_active)

    def test_wait_for_service_health_with_flapping(self):
        """wait_for_service_health requires N consecutive 200 OKs before passing."""
        # Simulated responses: 500, 200, 500, 200, 200, 200
        responses = [
            {"port": 8082, "status": "UNHEALTHY", "code": 500},
            {"port": 8082, "status": "HEALTHY", "code": 200},
            {"port": 8082, "status": "UNHEALTHY", "code": 500},
            {"port": 8082, "status": "HEALTHY", "code": 200},
            {"port": 8082, "status": "HEALTHY", "code": 200},
            {"port": 8082, "status": "HEALTHY", "code": 200},
        ]
        resp_idx = 0

        def mock_probe(port: int) -> Dict[str, Any]:
            nonlocal resp_idx
            if resp_idx < len(responses):
                res = responses[resp_idx]
                resp_idx += 1
                return res
            return {"port": port, "status": "HEALTHY", "code": 200}

        sentinel = ServerReloadSentinel(
            required_consecutive_probes=3,
            probe_interval_sec=0.01,
            max_reload_wait_sec=2.0,
        )

        is_healthy, consecutive_passed, logs = sentinel.wait_for_service_health(
            port=8082,
            required_consecutive=3,
            probe_fn=mock_probe,
        )
        self.assertTrue(is_healthy)
        self.assertEqual(consecutive_passed, 3)
        self.assertEqual(len(logs), 6)

    def test_reload_inference_cluster_input_validation(self):
        """reload_inference_cluster enforces non-empty .gguf path."""
        sentinel = ServerReloadSentinel()
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("")
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("model.bin")
        with self.assertRaises(ValueError):
            sentinel.reload_inference_cluster("model.gguf", target_port=99999)

    def test_reload_inference_cluster_end_to_end_simulated(self):
        """reload_inference_cluster completes zero-downtime failover and restoration."""
        probe_count = 0

        def mock_probe(port: int) -> Dict[str, Any]:
            nonlocal probe_count
            probe_count += 1
            if probe_count < 2:
                return {"port": port, "status": "UNHEALTHY", "code": 503}
            return {"port": port, "status": "HEALTHY", "code": 200}

        sentinel = ServerReloadSentinel(
            required_consecutive_probes=2,
            probe_interval_sec=0.01,
            max_reload_wait_sec=1.0,
        )

        res = sentinel.reload_inference_cluster(
            new_gguf_path="/vault/model-Q4_K_M.gguf",
            target_port=8082,
            probe_fn=mock_probe,
        )

        self.assertEqual(res["status"], "RELOADED")
        self.assertEqual(res["port"], 8082)
        self.assertEqual(res["active_route"], 8082)
        self.assertTrue(res["failover_executed"])
        self.assertEqual(res["health_probes_passed"], 2)


if __name__ == "__main__":
    unittest.main()
