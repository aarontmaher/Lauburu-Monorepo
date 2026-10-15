#!/usr/bin/env python3
import pytest
from common.ai_bindings.prima_mesh_client import PrimaMeshClient

def test_prima_mesh_status():
    client = PrimaMeshClient()
    status = client.get_mesh_status()
    assert "master_orchestrator" in status
    assert status["master_orchestrator"]["model"] == "qwen_38_max"
    assert status["rule_0_zero_mock"] == "VERIFIED_AUTHENTIC"

def test_endpoint_health_probe():
    client = PrimaMeshClient(timeout_sec=0.2)
    # Testing unroutable port returns False without throwing unhandled exception
    res = client.check_endpoint_health("127.0.0.1", 59999)
    assert res is False
