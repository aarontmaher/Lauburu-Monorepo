#!/usr/bin/env python3
"""
Adversarial Stress Harness: MCP Models Distributed Routing & Failover (R4)
Tests simulated backend dropouts, cascading failures, timeout injections,
explicit routing isolation, and health matrix resilience.
"""

import sys
import os
import asyncio
import traceback
from typing import Any, List, Dict, Optional

# Ensure antigravity_mcp_models is on sys.path
sys.path.insert(0, "/Users/aaron/teamwork_projects/antigravity_mcp_models/src")

from antigravity_mcp_models.clients.base import (
    BaseBackendClient,
    ModelResponse,
    BackendHealthStatus,
    BackendError,
    BackendUnavailableError,
    BackendTimeoutError,
    BackendPayloadError,
)
from antigravity_mcp_models.config import ServerConfig, BackendConfig
from antigravity_mcp_models.tools.routing_tools import (
    query_model,
    check_model_backends,
    list_available_models,
)

class MockFailingBackendClient(BaseBackendClient):
    """Configurable mock client that can simulate various dropout and failure modes."""
    
    def __init__(self, backend_name: str, behavior: str = "healthy", latency_ms: float = 5.0):
        super().__init__(backend_name=backend_name, config=BackendConfig(enabled=True, base_url=f"http://localhost:8080/{backend_name}"))
        self.behavior = behavior  # "healthy", "conn_refused", "timeout", "503", "500", "corrupt_json"
        self.latency_ms = latency_ms
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs: Any) -> ModelResponse:
        self.call_count += 1
        if self.behavior == "healthy":
            return ModelResponse(
                text=f"[{self.backend_name}] Response to: {prompt[:30]}",
                model="test-model",
                backend=self.backend_name,
                latency_ms=self.latency_ms,
            )
        elif self.behavior == "conn_refused":
            raise BackendUnavailableError(
                message=f"[{self.backend_name}] Connection refused at {self.config.base_url}",
                backend=self.backend_name,
                status_code=503,
                retryable=True,
            )
        elif self.behavior == "timeout":
            raise BackendTimeoutError(
                message=f"[{self.backend_name}] Read timed out after 30.0s",
                backend=self.backend_name,
                timeout_type="read",
            )
        elif self.behavior == "503":
            raise BackendUnavailableError(
                message=f"[{self.backend_name}] 503 Service Unavailable: GPU out of memory",
                backend=self.backend_name,
                status_code=503,
                retryable=True,
            )
        elif self.behavior == "500":
            raise BackendError(
                message=f"[{self.backend_name}] 500 Internal Server Error: CUDA assertion failure",
                backend=self.backend_name,
                status_code=500,
                retryable=False,
            )
        elif self.behavior == "corrupt_json":
            raise BackendPayloadError(
                message=f"[{self.backend_name}] Malformed JSON response body: unexpected end of stream",
                backend=self.backend_name,
                status_code=400,
            )
        raise ValueError(f"Unknown behavior: {self.behavior}")

    async def chat(self, messages: List[Dict[str, Any]], **kwargs: Any) -> ModelResponse:
        last_msg = messages[-1]["content"] if messages else ""
        return await self.generate(prompt=last_msg, **kwargs)

    async def check_health(self) -> BackendHealthStatus:
        if self.behavior == "healthy":
            return BackendHealthStatus(
                backend=self.backend_name,
                healthy=True,
                status="operational",
                latency_ms=self.latency_ms,
                endpoint=str(self.config.base_url),
                active_model="test-model-v1",
                available_models=["test-model-v1", "test-model-v2"],
            )
        else:
            return BackendHealthStatus(
                backend=self.backend_name,
                healthy=False,
                status="offline",
                latency_ms=0.0,
                endpoint=str(self.config.base_url),
                active_model="None",
                available_models=[],
                error=f"Simulated failure: {self.behavior}",
            )

    async def list_models(self) -> List[str]:
        if self.behavior == "healthy":
            return ["model-alpha", "model-beta"]
        raise BackendUnavailableError(
            message=f"[{self.backend_name}] Cannot list models: backend offline",
            backend=self.backend_name,
            status_code=503,
        )


async def run_adversarial_mcp_tests():
    print("=================================================================")
    print("  ADVERSARIAL STRESS TEST: MCP MODELS ROUTING & FAILOVER (R4)   ")
    print("=================================================================")
    results = {}

    # Test 1: Primary llama.cpp drops out -> Failover to Exo
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="conn_refused"),
            "exo": MockFailingBackendClient("exo", behavior="healthy"),
            "petals": MockFailingBackendClient("petals", behavior="healthy"),
        }
        res = await query_model(prompt="Test prompt 1", backend="auto", client_map=client_map)
        assert "[exo]" in res, f"Expected [exo] response, got: {res}"
        assert client_map["llamacpp"].call_count == 1, "Primary should have been attempted once"
        assert client_map["exo"].call_count == 1, "Secondary should have been invoked on failover"
        assert client_map["petals"].call_count == 0, "Tertiary should not have been called"
        print(" [PASS] Test 1: Primary (llama.cpp) dropout -> Clean failover to secondary (Exo)")
        results["test_1_primary_dropout"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 1: {e}")
        traceback.print_exc()
        results["test_1_primary_dropout"] = f"FAIL: {e}"

    # Test 2: Primary and Secondary drop out -> Failover to Tertiary (Petals)
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="503"),
            "exo": MockFailingBackendClient("exo", behavior="timeout"),
            "petals": MockFailingBackendClient("petals", behavior="healthy"),
        }
        res = await query_model(prompt="Test prompt 2", backend="auto", client_map=client_map)
        assert "[petals]" in res, f"Expected [petals] response, got: {res}"
        assert client_map["llamacpp"].call_count == 1
        assert client_map["exo"].call_count == 1
        assert client_map["petals"].call_count == 1
        print(" [PASS] Test 2: Cascading dropouts (llama.cpp + Exo) -> Clean failover to tertiary (Petals)")
        results["test_2_cascading_dropouts"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 2: {e}")
        traceback.print_exc()
        results["test_2_cascading_dropouts"] = f"FAIL: {e}"

    # Test 3: Total blackout - All backends drop out
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="conn_refused"),
            "exo": MockFailingBackendClient("exo", behavior="500"),
            "petals": MockFailingBackendClient("petals", behavior="corrupt_json"),
        }
        failed_as_expected = False
        try:
            await query_model(prompt="Test prompt 3", backend="auto", client_map=client_map)
        except BackendUnavailableError as exc:
            failed_as_expected = True
            assert exc.status_code == 503, f"Expected 503 status code, got {exc.status_code}"
            assert exc.retryable is True, "Should be marked retryable"
            err_msg = str(exc)
            assert "llamacpp" in err_msg and "exo" in err_msg and "petals" in err_msg, \
                f"Error message must contain details from all failing backends, got: {err_msg}"
        assert failed_as_expected, "Query should have raised BackendUnavailableError when all backends fail"
        print(" [PASS] Test 3: Total backend blackout -> BackendUnavailableError(503, retryable=True) with complete audit trail")
        results["test_3_total_blackout"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 3: {e}")
        traceback.print_exc()
        results["test_3_total_blackout"] = f"FAIL: {e}"

    # Test 4: Explicit non-auto routing isolation
    # If user requests explicit backend 'llamacpp' and it fails, it must NOT silently route to Exo
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="500"),
            "exo": MockFailingBackendClient("exo", behavior="healthy"),
            "petals": MockFailingBackendClient("petals", behavior="healthy"),
        }
        failed_explicit = False
        try:
            await query_model(prompt="Explicit test", backend="llamacpp", client_map=client_map)
        except BackendError as exc:
            failed_explicit = True
            assert "CUDA assertion failure" in str(exc)
        assert failed_explicit, "Explicit routing to failing backend must fail immediately without falling over"
        assert client_map["exo"].call_count == 0, "Exo must not be invoked on explicit llamacpp call"
        print(" [PASS] Test 4: Explicit backend routing isolation (no unintended cross-talk on failure)")
        results["test_4_explicit_routing_isolation"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 4: {e}")
        traceback.print_exc()
        results["test_4_explicit_routing_isolation"] = f"FAIL: {e}"

    # Test 5: Chat mode multi-backend failover with structured messages
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="timeout"),
            "exo": MockFailingBackendClient("exo", behavior="healthy"),
            "petals": MockFailingBackendClient("petals", behavior="healthy"),
        }
        messages = [
            {"role": "system", "content": "You are a helpful mesh assistant."},
            {"role": "user", "content": "Analyze network topology."}
        ]
        res = await query_model(messages=messages, backend="auto", client_map=client_map)
        assert "[exo]" in res
        print(" [PASS] Test 5: Chat conversation mode auto-routing failover verified")
        results["test_5_chat_mode_failover"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 5: {e}")
        traceback.print_exc()
        results["test_5_chat_mode_failover"] = f"FAIL: {e}"

    # Test 6: Health matrix check with degraded/offline backends
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="healthy", latency_ms=12.4),
            "exo": MockFailingBackendClient("exo", behavior="conn_refused"),
            "petals": MockFailingBackendClient("petals", behavior="503"),
        }
        matrix = await check_model_backends(client_map=client_map)
        assert "llama.cpp" in matrix and "Operational" in matrix
        assert "Exo" in matrix and "Degraded/Offline" in matrix
        assert "Petals" in matrix and "Degraded/Offline" in matrix
        print(" [PASS] Test 6: check_model_backends() correctly captures mixed operational/degraded states")
        results["test_6_health_matrix_degraded"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 6: {e}")
        traceback.print_exc()
        results["test_6_health_matrix_degraded"] = f"FAIL: {e}"

    # Test 7: Model catalog discovery with partial offline backends
    try:
        client_map = {
            "llamacpp": MockFailingBackendClient("llamacpp", behavior="healthy"),
            "exo": MockFailingBackendClient("exo", behavior="conn_refused"),
            "petals": MockFailingBackendClient("petals", behavior="healthy"),
        }
        catalog = await list_available_models(client_map=client_map)
        assert "Total Available Models" in catalog and "4" in catalog
        assert "No models currently discovered or backend offline" in catalog
        print(" [PASS] Test 7: list_available_models() resiliently aggregates models despite partial backend offline")
        results["test_7_model_catalog_resilience"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 7: {e}")
        traceback.print_exc()
        results["test_7_model_catalog_resilience"] = f"FAIL: {e}"

    # Test 8: High concurrency stress test with oscillating backend availability
    try:
        class FlappingClient(BaseBackendClient):
            def __init__(self, name):
                super().__init__(backend_name=name, config=BackendConfig(enabled=True, base_url=f"http://localhost:8080/{name}"))
                self.calls = 0
            async def generate(self, prompt: str, **kwargs):
                self.calls += 1
                if self.calls % 2 == 1:
                    raise BackendUnavailableError(f"Flapping offline call {self.calls}", backend=self.backend_name, status_code=503)
                return ModelResponse(text=f"[{self.backend_name}] OK", model="m", backend=self.backend_name, latency_ms=1.0)
            async def chat(self, messages, **kwargs):
                return await self.generate("chat", **kwargs)
            async def check_health(self):
                return BackendHealthStatus(backend=self.backend_name, healthy=True, status="ok", latency_ms=1.0, endpoint="url", active_model="m", available_models=["m"])
            async def list_models(self):
                return ["m"]

        c_map = {
            "llamacpp": FlappingClient("llamacpp"),
            "exo": FlappingClient("exo"),
            "petals": MockFailingBackendClient("petals", behavior="healthy")
        }

        tasks = [query_model(prompt=f"Stress prompt {i}", backend="auto", client_map=c_map) for i in range(50)]
        stress_results = await asyncio.gather(*tasks)
        assert len(stress_results) == 50
        for sr in stress_results:
            assert any(b in sr for b in ["[llamacpp]", "[exo]", "[petals]"])
        print(" [PASS] Test 8: 50 concurrent requests with flapping dropouts completed with 100% success")
        results["test_8_concurrency_flapping_stress"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Test 8: {e}")
        traceback.print_exc()
        results["test_8_concurrency_flapping_stress"] = f"FAIL: {e}"

    print("=================================================================")
    all_passed = all(v == "PASS" for v in results.values())
    print(f"R4 MCP ROUTING ADVERSARIAL RESULT: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=================================================================")
    return all_passed, results

if __name__ == "__main__":
    ok, res = asyncio.run(run_adversarial_mcp_tests())
    if not ok:
        sys.exit(1)
