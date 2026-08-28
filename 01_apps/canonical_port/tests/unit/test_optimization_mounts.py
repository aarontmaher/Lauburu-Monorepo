"""
Unit Tests: 4 Optimization Modules Aggregation & Mounting Contracts (Features 7, 8, 9, 10)
Verifies mounting contracts, telemetry endpoints, and subsystem interfaces for Hardware, Software, Internet, Storage.
Derived from ORIGINAL_REQUEST.md §R2 and PROJECT.md §3.
"""

import pytest
from typing import Dict, List, Any, Optional

class OptimizationModuleHost:
    """Reference mounting host for the 4 optimization modules."""
    def __init__(self, modules_spec: Dict[str, Any], api_base_url: str = "http://127.0.0.1:4000"):
        self.modules = modules_spec
        self.api_base_url = api_base_url
        self.mounted_modules: Dict[str, Dict[str, Any]] = {}

    def mount_module(self, module_key: str, props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if module_key not in self.modules:
            raise KeyError(f"Unknown optimization module: {module_key}")
        
        spec = self.modules[module_key]
        mount_record = {
            "moduleId": spec["id"],
            "name": spec["name"],
            "status": "MOUNTED",
            "apiBaseUrl": self.api_base_url,
            "subsystems": spec["subsystems"],
            "endpoints": spec["telemetryEndpoints"],
            "customProps": props or {}
        }
        self.mounted_modules[module_key] = mount_record
        return mount_record

    def get_mounted_module(self, module_key: str) -> Optional[Dict[str, Any]]:
        return self.mounted_modules.get(module_key)

    def trigger_action(self, module_key: str, action_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if module_key not in self.mounted_modules:
            return {"success": False, "error": f"Module {module_key} is not mounted"}
        return {
            "success": True,
            "moduleId": self.mounted_modules[module_key]["moduleId"],
            "action": action_name,
            "payload": payload,
            "timestamp": "2026-08-27T04:20:00Z"
        }


def test_mount_all_four_optimization_modules(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    keys = ["hardware", "software", "internet", "storage"]
    for key in keys:
        res = host.mount_module(key)
        assert res["status"] == "MOUNTED"
        assert res["moduleId"] == optimization_modules_spec[key]["id"]
        assert len(res["subsystems"]) >= 3
        assert len(res["endpoints"]) >= 3

def test_hardware_optimization_mounting_contract(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    res = host.mount_module("hardware", {"bleakHz": 128})
    assert res["moduleId"] == "optimization-hardware"
    assert "LiveDeviceSentinelHUD" in res["subsystems"]
    assert "ComputeHubWebView" in res["subsystems"]
    assert "/api/telemetry" in res["endpoints"]
    assert res["customProps"]["bleakHz"] == 128

def test_software_optimization_mounting_contract(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    res = host.mount_module("software")
    assert res["moduleId"] == "optimization-software"
    assert "MetaTrainingGameDashboardView" in res["subsystems"]
    assert "/api/pyspark/ast_index" in res["endpoints"]
    
    # Trigger sandbox evaluation action
    act = host.trigger_action("software", "evaluate_sandbox_code", {"language": "c", "asan": True})
    assert act["success"] is True
    assert act["action"] == "evaluate_sandbox_code"

def test_internet_optimization_mounting_contract(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    res = host.mount_module("internet")
    assert res["moduleId"] == "optimization-internet"
    assert "FutureNetworkSimulationHub" in res["subsystems"]
    assert "/api/mesh_all_to_all_matrix" in res["endpoints"]
    assert optimization_modules_spec["internet"]["transportersCount"] == 10

def test_storage_optimization_mounting_contract(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    res = host.mount_module("storage")
    assert res["moduleId"] == "optimization-storage"
    assert "StorageAnalysisHub" in res["subsystems"]
    assert "/api/storage/deep_analysis" in res["endpoints"]
    assert optimization_modules_spec["storage"]["minFreeHeadroomGb"] == 10.0

def test_unmounted_module_action_failure(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    act = host.trigger_action("hardware", "reboot_sentinel", {})
    assert act["success"] is False
    assert "not mounted" in act["error"]

def test_invalid_module_mount_raises(optimization_modules_spec):
    host = OptimizationModuleHost(optimization_modules_spec)
    with pytest.raises(KeyError):
        host.mount_module("invalid_module_key")
