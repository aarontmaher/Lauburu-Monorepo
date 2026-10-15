import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src to python path so we can import the app
sys.path.insert(0, str(Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src")))
from sovereign_remote_desktop_server import app, ArmState, current_arm_state

client = TestClient(app)

def test_manifest_pwa():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data["display"] == "standalone"
    assert data["short_name"] == "ScreenLens"

def test_dashboard_load():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sovereign Remote Desktop" in response.text

def test_dashboard_has_virtual_keyboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "Virtual KB" in response.text
    assert "virtual-keyboard-drawer" in response.text
    assert "SCREEN LENS IN KEYBOARD HUD" in response.text
    assert "Spotlight ⌘␣" in response.text
    assert "App Switch ⌘⇥" in response.text
    assert "Toolkit:" in response.text
    assert "Notifications 🔔" in response.text
    assert "Swap Alt/Cmd ⇄" in response.text
    assert "Magic KB 🔄" in response.text
    assert "sendVirtualKey" in response.text
    assert "sendKdeShareText" in response.text
    assert "dispatchLensToKM" in response.text
    assert "configureHardwareKeyboard" in response.text
    assert "resetAllModifiers" in response.text
    assert "onVisualTypingInput" in response.text
    assert "cycleKeyboardTarget" in response.text
    assert "toggleJumpMode" in response.text


def test_lens_to_km_endpoint():
    # Disarmed check -> MUST return 423 LOCKED
    client.post("/api/arm", json={"armed": False})
    disarmed_resp = client.post("/api/hid/lens_to_km", json={
        "action": "notifications",
        "target_device": "pixel_10_pro_xl"
    })
    assert disarmed_resp.status_code == 423

    # Armed check -> MUST return 200
    client.post("/api/arm", json={"armed": True, "duration_sec": 60})
    try:
        response = client.post("/api/hid/lens_to_km", json={
            "action": "notifications",
            "target_device": "pixel_10_pro_xl"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "error"]
        assert data["action"] == "notifications"
        assert data["zero_mock"] == "VERIFIED_LENS_TO_KM_DISPATCH"
    finally:
        client.post("/api/arm", json={"armed": False})

def test_hardware_keyboard_endpoints():
    # Test GET status
    status_resp = client.get("/api/hid/hardware_keyboard/status")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert "alt_cmd_swapped" in st_data
    assert "magic_keyboard_bt" in st_data
    assert st_data["zero_mock"] == "VERIFIED_HARDWARE_SYSCALLS"

    # Test POST configure
    cfg_resp = client.post("/api/hid/hardware_keyboard/configure", json={"action": "swap_alt_cmd"})
    assert cfg_resp.status_code == 200
    cfg_data = cfg_resp.json()
    assert cfg_data["status"] == "ok"
    assert cfg_data["action"] == "swap_alt_cmd"

def test_kdeconnect_status_endpoint():
    response = client.get("/api/hid/kdeconnect/status")
    assert response.status_code == 200
    data = response.json()
    assert "daemon_running" in data
    assert "paired_devices_count" in data
    assert "zero_mock" in data

def test_kdeconnect_devices_endpoint():
    response = client.get("/api/hid/kdeconnect/devices")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "devices" in data
    assert isinstance(data["devices"], list)

def test_km_keyboard_status_endpoint():
    response = client.get("/api/hid/km_keyboard/status")
    assert response.status_code == 200
    data = response.json()
    assert data["bridge_status"] == "ACTIVE"
    assert "total_events_ingested" in data
    assert data["zero_mock"] == "VERIFIED_AUTHENTIC_KM_KEYBOARD"

def test_km_keyboard_event_ingestion():
    test_event = {
        "source": "test_suite",
        "key": "tab",
        "event_type": "key_press",
        "target_node": "l1_mac_mini",
        "modifiers": ["ctrl"]
    }
    response = client.post("/api/hid/km_keyboard/event", json=test_event)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["event"]["key"] == "tab"
    assert data["event"]["source"] == "test_suite"

    # Verify event appears in status history
    status_resp = client.get("/api/hid/km_keyboard/status")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["total_events_ingested"] >= 1

def test_keyboard_layout_endpoint():
    response = client.get("/api/hid/keyboard/layout")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "quick_macros" in data
    assert "rows" in data
    assert any(m["id"] == "spotlight" for m in data["quick_macros"])
    assert any(m["id"] == "ctrl_c" for m in data["quick_macros"])

def test_arming_guard_for_kde_send_keys():
    # Ensure observe only
    client.post("/api/arm", json={"armed": False})
    
    # Attempt send_keys while disarmed -> MUST return 423 LOCKED
    response = client.post("/api/hid/kdeconnect/send_keys", json={"target": "l2_macbook_pro", "keys": "echo test"})
    assert response.status_code == 423
    assert response.json()["detail"]["error"] == "OBSERVE_ONLY_LOCKED"

def test_arming_guard_for_mousepad():
    client.post("/api/arm", json={"armed": False})
    response = client.post("/api/hid/kdeconnect/mousepad", json={"dx": 10.0, "dy": 5.0})
    assert response.status_code == 423

def test_armed_kde_mousepad_enqueue():
    # Arm system
    arm_resp = client.post("/api/arm", json={"armed": True, "duration_sec": 60})
    assert arm_resp.status_code == 200
    assert arm_resp.json()["arm_state"] == "CONTROL_ARMED"

    try:
        # Enqueue mousepad event
        response = client.post("/api/hid/kdeconnect/mousepad", json={
            "dx": 0.0,
            "dy": 0.0,
            "singleclick": True,
            "node": "l1_mac_mini"
        })
        assert response.status_code == 202
        assert response.json()["status"] == "enqueued"
    finally:
        # Cleanly disarm
        client.post("/api/arm", json={"armed": False})


def test_keyboard_lens_status_endpoint():
    response = client.get("/api/keyboard/lens/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert "active_keyboard_target" in data
    assert "supported_nodes" in data
    assert "frontmost_app" in data
    assert data["zero_mock"] == "VERIFIED_LENS_IN_KEYBOARD_ENGINE"


def test_keyboard_lens_autocomplete_endpoint():
    response = client.post("/api/keyboard/lens/autocomplete", json={"prefix": "git", "limit": 4})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["prefix"] == "git"
    assert isinstance(data["suggestions"], list)
    assert data["zero_mock"] == "VERIFIED_VISUAL_AUTOCOMPLETE"


def test_keyboard_lens_jump_index_endpoint():
    response = client.post("/api/keyboard/lens/jump/index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "targets" in data
    assert data["zero_mock"] == "VERIFIED_TYPE_TO_JUMP_INDEX"


def test_keyboard_lens_cycle_and_switch_target():
    # Test cycle target
    cycle_resp = client.post("/api/keyboard/lens/cycle_target")
    assert cycle_resp.status_code == 200
    c_data = cycle_resp.json()
    assert c_data["status"] == "ok"
    assert "active_target" in c_data
    assert c_data["zero_mock"] == "VERIFIED_KEYBOARD_TARGET_SWITCH"

    # Reset target back to l1_mac_mini
    sw_resp = client.post("/api/keyboard/lens/switch_target", json={"target": "l1_mac_mini"})
    assert sw_resp.status_code == 200
    sw_data = sw_resp.json()
    assert sw_data["status"] == "ok"
    assert sw_data["active_target"] == "l1_mac_mini"


def test_keyboard_lens_autofill_endpoint():
    response = client.post("/api/keyboard/lens/autofill")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "error"]
    if data["status"] == "ok":
        assert "copied_text" in data
        assert data["zero_mock"] == "VERIFIED_VISUAL_AUTOFILL"


def test_keyboard_lens_ai_copilot_endpoint():
    response = client.post("/api/keyboard/lens/ai_copilot", json={"prefix": "echo 'test'"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "error"]
    if data["status"] == "ok":
        assert "completion" in data
        assert data["zero_mock"] == "VERIFIED_LOCAL_LLM_COMPLETION"


def test_keyboard_lens_jump_execute_arming_guard():
    # Disarmed -> MUST return 423 LOCKED
    client.post("/api/arm", json={"armed": False})
    disarmed_resp = client.post("/api/keyboard/lens/jump/execute", json={"tag": "aa"})
    assert disarmed_resp.status_code == 423
    assert disarmed_resp.json()["detail"]["error"] == "OBSERVE_ONLY_LOCKED"

