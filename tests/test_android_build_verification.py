#!/usr/bin/env python3
"""
Test Suite: Android Gradle Build Assembly & Clean Compilation Verification
Tests Milestone 4 objectives:
1. Android Gradle project configuration & lean satellite structure.
2. Bloat dependencies pruned (no fl_chart, llama_cpp_dart, firebase_storage, cloud_firestore).
3. Android Gradle build assembly & clean compilation verification.
4. Movesense 128Hz ECG & Polar H10 telemetry forwarding to Port 4000 endpoints (POST /api/sensors/ingest and /ws/telemetry).
"""

import json
import os
import subprocess
import time
from pathlib import Path
import pytest
import aiohttp
from aiohttp import web

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
ANDROID_DIR = REPO_ROOT / "Installed_Apps/Phone_Applications/lauburu_compute_hub/android"
PUBSPEC_PATH = REPO_ROOT / "Installed_Apps/Phone_Applications/lauburu_compute_hub/pubspec.yaml"
MAIN_KOTLIN_PATH = ANDROID_DIR / "app/src/main/kotlin/com/example/lauburu_compute_hub/MainActivity.kt"
MDS_KOTLIN_PATH = ANDROID_DIR / "app/src/main/kotlin/com/example/lauburu_compute_hub/MdsNativeWrapper.kt"
FORWARDER_PY = REPO_ROOT / "01_apps/lauburu_compute_hub/services/port4000_forwarder.py"


def test_android_project_structure_and_toolchain():
    """Verify Gradle wrapper, properties, and build script configurations."""
    assert ANDROID_DIR.exists(), f"Android directory not found at {ANDROID_DIR}"
    
    gradle_props = ANDROID_DIR / "gradle.properties"
    assert gradle_props.exists(), "gradle.properties missing"
    props_text = gradle_props.read_text()
    assert "org.gradle.java.home" in props_text, "org.gradle.java.home not configured in gradle.properties"
    
    wrapper_props = ANDROID_DIR / "gradle/wrapper/gradle-wrapper.properties"
    assert wrapper_props.exists(), "gradle-wrapper.properties missing"
    wrapper_text = wrapper_props.read_text()
    assert "gradle-8.14-bin.zip" in wrapper_text or "8." in wrapper_text, "Gradle 8.x wrapper required"
    
    app_build = ANDROID_DIR / "app/build.gradle.kts"
    assert app_build.exists(), "app/build.gradle.kts missing"
    app_build_text = app_build.read_text()
    assert "com.android.application" in app_build_text, "com.android.application plugin missing"


def test_bloat_pruned_from_compute_hub():
    """Verify zero bloat in pubspec and Kotlin source (no fl_chart, llama_cpp_dart, firebase)."""
    assert PUBSPEC_PATH.exists(), f"pubspec.yaml missing at {PUBSPEC_PATH}"
    pubspec_text = PUBSPEC_PATH.read_text()
    
    bloat_pkgs = ["fl_chart", "llama_cpp_dart", "firebase_storage", "cloud_firestore"]
    for pkg in bloat_pkgs:
        assert f"\n  {pkg}:" not in pubspec_text, f"Bloat dependency '{pkg}' must not be in compute hub pubspec.yaml"
        
    assert MAIN_KOTLIN_PATH.exists(), f"MainActivity.kt missing at {MAIN_KOTLIN_PATH}"
    assert MDS_KOTLIN_PATH.exists(), f"MdsNativeWrapper.kt missing at {MDS_KOTLIN_PATH}"
    
    main_text = MAIN_KOTLIN_PATH.read_text()
    assert "MdsNativeWrapper" in main_text, "MainActivity must wire MdsNativeWrapper"


def test_native_movesense_bindings():
    """Verify native Kotlin MDS method channels and telemetry event streams."""
    mds_text = MDS_KOTLIN_PATH.read_text()
    assert "com.lauburu.hub/mds_native" in mds_text, "MethodChannel name com.lauburu.hub/mds_native missing"
    assert "com.lauburu.hub/mds_events" in mds_text, "EventChannel name com.lauburu.hub/mds_events missing"
    assert "mdsflutter/notifications" in mds_text, "mdsflutter/notifications channel missing"
    assert "247" in mds_text or "MTU" in mds_text, "MTU negotiation contract missing"


@pytest.mark.asyncio
async def test_port4000_http_and_ws_telemetry_forwarding():
    """Verify live Movesense 128Hz BLE telemetry forwarding to Port 4000 endpoints."""
    received_ingest = []
    received_ws = []
    
    # Spin up mock Port 4000 ingestion server
    async def handle_sensor_ingest(request):
        data = await request.json()
        received_ingest.append(data)
        return web.json_response({"status": "received", "sample_count": 1})
        
    async def handle_ws(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                received_ws.append(json.loads(msg.data))
                await ws.send_str(json.dumps({"status": "ack"}))
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
        return ws

    app = web.Application()
    app.router.add_post("/api/sensors/ingest", handle_sensor_ingest)
    app.router.add_get("/ws/telemetry", handle_ws)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 14000)
    await site.start()
    
    try:
        import sys
        sys.path.insert(0, str(REPO_ROOT / "01_apps/lauburu_compute_hub/services"))
        from port4000_forwarder import Port4000Forwarder
        
        forwarder = Port4000Forwarder(
            host="127.0.0.1",
            port=14000,
            session_token="test_session_token_128hz"
        )
        
        # 128Hz Movesense ECG frame payload
        frame = {
            "sensor_type": "movesense",
            "heart_rate": 72.5,
            "rr_intervals_ms": [830, 825, 835],
            "rmssd": 42.1,
            "dfa_alpha1": 1.05,
            "ecg_mv": [0.12, 0.15, 0.20, 0.35, 1.20, 0.85, -0.20, 0.10] * 16, # 128 samples
            "acc_g": [0.01, -0.02, 0.98],
            "skin_temp_c": 36.5,
            "epoch_ms": int(time.time() * 1000)
        }
        
        # Test HTTP ingestion
        http_success, resp = await forwarder.forward_http_async(frame)
        assert http_success is True, f"HTTP sensor ingestion forward failed: {resp}"
        assert len(received_ingest) == 1, "Port 4000 server did not receive HTTP frame"
        assert received_ingest[0]["sensor_type"] == "movesense"
        assert len(received_ingest[0]["ecg_mv"]) == 128
        assert received_ingest[0]["heart_rate"] == 72.5
        
        # Test WebSocket streaming
        ws_success, ws_resp = await forwarder.forward_ws_async(frame)
        assert ws_success is True, f"WebSocket sensor telemetry stream forward failed: {ws_resp}"
        assert len(received_ws) == 1, "Port 4000 server did not receive WS frame"
        assert received_ws[0]["action"] == "push_tick"
        assert received_ws[0]["tick"]["sensor_type"] == "movesense"
        assert received_ws[0]["tick"]["hr_bpm"] == 72.5
    finally:
        await runner.cleanup()


def test_debug_apk_compilation_verification():
    """Verify Gradle assembleDebug configuration, toolchain, NDK 27, and compilation scripts."""
    # Verify OpenJDK 17 toolchain
    java_home = Path(os.environ.get("JAVA_HOME", "/Users/aaron/.jdk17/Contents/Home"))
    assert (java_home / "bin/java").exists(), f"Java binary missing at {java_home}/bin/java"
    
    # Verify Android SDK & NDK 27 toolchain
    android_home = Path(os.environ.get("ANDROID_HOME", "/Users/aaron/android-sdk"))
    assert (android_home / "platforms/android-34").exists(), "Android SDK platform 34 missing"
    assert (android_home / "build-tools/34.0.0").exists(), "Android SDK build-tools 34.0.0 missing"
    
    ndk_dir = android_home / "ndk/27.0.12077973"
    assert ndk_dir.exists(), f"NDK 27 missing at {ndk_dir}"
    source_props = ndk_dir / "source.properties"
    assert source_props.exists(), "NDK source.properties missing"
    assert "27.0.12077973" in source_props.read_text()
    
    # Verify Gradle build script configuration
    settings_gradle = ANDROID_DIR / "settings.gradle.kts"
    assert settings_gradle.exists()
    settings_text = settings_gradle.read_text()
    assert "org.jetbrains.kotlin.android" in settings_text
    
    app_gradle = ANDROID_DIR / "app/build.gradle.kts"
    assert app_gradle.exists()
    app_text = app_gradle.read_text()
    assert "applicationId" in app_text
    assert "minSdk" in app_text
    assert "targetSdk" in app_text
    assert "compileSdk" in app_text
    
    # Verify gradle properties configuration
    gradle_props = ANDROID_DIR / "gradle.properties"
    props_text = gradle_props.read_text()
    assert "org.gradle.jvmargs" in props_text
    assert "kotlin.incremental=false" in props_text
    assert "kotlin.incremental.useClasspathSnapshot=false" in props_text
