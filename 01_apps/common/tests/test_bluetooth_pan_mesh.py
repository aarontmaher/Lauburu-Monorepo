#!/usr/bin/env python3
import pytest
from common.network.bluetooth_pan_mesh import BluetoothPanMeshManager

def test_bt_pan_manager_init():
    mgr = BluetoothPanMeshManager()
    assert mgr.os_type in ["darwin", "linux"]

def test_optimal_transport_evaluation():
    mgr = BluetoothPanMeshManager()
    telemetry = mgr.evaluate_optimal_transport()
    assert "optimal_transport" in telemetry
    assert "details" in telemetry
    assert isinstance(telemetry["details"], list)
    for record in telemetry["details"]:
        assert "transport" in record
        assert "reachable" in record
