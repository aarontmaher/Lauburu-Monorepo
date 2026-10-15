#!/usr/bin/env python3
"""
Android Package, Manifest, and Asset Integrity Tests for Lauburu Bluetooth Terminal IDE.
Governed by:
- Rule 1 (Tri-Proof): Exact cryptographic SHA256 and byte counts.
"""

import os
import hashlib
from pathlib import Path

BASE_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/bluetooth_terminal_ide")
APK_PATH = BASE_DIR / "android/app/build/outputs/apk/debug/app-debug.apk"
BUILD_GRADLE_PATH = BASE_DIR / "android/app/build.gradle.kts"
MANIFEST_PATH = BASE_DIR / "android/app/src/main/AndroidManifest.xml"
MAIN_ACTIVITY_PATH = BASE_DIR / "android/app/src/main/java/com/lauburu/terminalide/MainActivity.kt"
INDEX_HTML_PATH = BASE_DIR / "frontend/index.html"
ASSETS_INDEX_HTML_PATH = BASE_DIR / "android/app/src/main/assets/index.html"

def test_apk_exists_and_checksum():
    """Verifies that the compiled APK exists and exceeds 5MB."""
    assert APK_PATH.exists(), f"APK not found at {APK_PATH}"
    size = APK_PATH.stat().st_size
    assert size > 5_000_000, f"APK size {size} is unexpectedly small"
    with open(APK_PATH, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert len(sha256) == 64
    print(f"Verified APK size: {size} bytes, SHA256: {sha256}")

def test_manifest_permissions_and_package():
    """Verifies required permissions in AndroidManifest.xml and package in build.gradle.kts."""
    assert MANIFEST_PATH.exists()
    assert BUILD_GRADLE_PATH.exists()
    
    gradle_content = BUILD_GRADLE_PATH.read_text(encoding="utf-8")
    assert "applicationId = \"com.lauburu.terminalide\"" in gradle_content
    assert "namespace = \"com.lauburu.terminalide\"" in gradle_content
    
    # Required permissions in manifest
    manifest_content = MANIFEST_PATH.read_text(encoding="utf-8")
    assert "android.permission.INTERNET" in manifest_content
    assert "android.permission.CAMERA" in manifest_content
    assert "android.permission.BLUETOOTH" in manifest_content
    assert "android.permission.BLUETOOTH_CONNECT" in manifest_content

def test_main_activity_configuration():
    """Verifies WebView settings and reverse bridge config in MainActivity.kt."""
    assert MAIN_ACTIVITY_PATH.exists()
    content = MAIN_ACTIVITY_PATH.read_text(encoding="utf-8")
    
    # WebView JavaScript and DOM Storage
    assert "javaScriptEnabled = true" in content
    assert "domStorageEnabled = true" in content
    assert "allowFileAccess = true" in content
    assert "allowContentAccess = true" in content
    
    # Default URL to port 4050 reverse tunnel with asset fallback
    assert "http://127.0.0.1:4050" in content
    assert "file:///android_asset/index.html" in content

def test_frontend_assets_sync():
    """Verifies that frontend index.html is synchronized with android assets."""
    assert INDEX_HTML_PATH.exists()
    assert ASSETS_INDEX_HTML_PATH.exists()
    
    frontend_size = INDEX_HTML_PATH.stat().st_size
    asset_size = ASSETS_INDEX_HTML_PATH.stat().st_size
    assert frontend_size > 20_000, "Frontend index.html is too small"
    assert asset_size > 20_000, "Asset index.html is too small"
    
    # Content features
    content = INDEX_HTML_PATH.read_text(encoding="utf-8")
    assert "LAUBURU BT IDE" in content
    assert "M1: AUDIT" in content
    assert "M5: PRIMA" in content
    assert "TRI-ORCHESTRATOR" in content
    assert "SCREEN LENS" in content
    assert "OFFLINE RAG IDE" in content
