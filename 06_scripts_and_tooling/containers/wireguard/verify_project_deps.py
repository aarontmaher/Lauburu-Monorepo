#!/usr/bin/env python3
"""
verify_project_deps.py
Empirical Tri-Proof Verification of Project Dependencies inside Podman Container.
Governed by Rule 1: Zero-Mock & Truth Verification Rule.
"""

import sys
import hashlib
import platform

print("=" * 60)
print("🔬 LAUBURU PROJECT CONTAINER DEPENDENCY VERIFICATION")
print(f"Python Version: {platform.python_version()} ({platform.machine()})")
print(f"System Kernel:  {platform.system()} {platform.release()}")
print("=" * 60)

modules_to_test = [
    ("fastapi", "FastAPI Core Web Framework"),
    ("uvicorn", "ASGI Server"),
    ("pydantic", "Schema Validation"),
    ("psutil", "Hardware & Process Telemetry"),
    ("httpx", "Async HTTP Client"),
    ("aiohttp", "Async HTTP Server/Client"),
    ("websockets", "Realtime WebSockets Bridge"),
    ("numpy", "Numerical DSP Array Operations"),
    ("scipy", "Signal Processing & Biometrics"),
    ("bleak", "Bluetooth Low Energy Mesh Protocol"),
    ("cryptography", "Zero-Knowledge Encryption"),
    ("yaml", "PyYAML Configuration Parser"),
    ("pyarrow", "Parquet Columnar Data Lake"),
    ("pandas", "Dataframe Telemetry Processor"),
    ("pytest", "Empirical Test Runner"),
    ("rich", "TUI Formatting & Console Engine"),
]

passed = 0
failed = 0

for mod_name, desc in modules_to_test:
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "unknown")
        print(f"  [✓] {mod_name:<14} v{ver:<10} - {desc}")
        passed += 1
    except Exception as e:
        print(f"  [✗] {mod_name:<14} FAILED: {e}")
        failed += 1

print("-" * 60)

import shutil
system_tools = [
    ("wg", "WireGuard Tools"),
    ("podman", "Podman Container Engine"),
    ("cloudflared", "Cloudflare Tunnel Daemon"),
    ("go", "Go Toolchain (GoLand IDE Support)"),
]

for tool, desc in system_tools:
    path = shutil.which(tool)
    if path:
        print(f"  [✓] CLI tool {tool:<10} found at {path} - {desc}")
        passed += 1
    else:
        print(f"  [!] CLI tool {tool:<10} NOT found in PATH - {desc}")

print("-" * 60)

# Functional verification: NumPy DSP & Cryptography
try:
    import numpy as np
    t = np.linspace(0, 1, 512)
    sig = np.sin(2 * np.pi * 50 * t)
    assert len(sig) == 512
    print(f"  [✓] DSP Math Check: Generated 512-sample synthetic test wave (Mean: {np.mean(sig):.6f})")

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    key = b"\x00" * 32
    iv = b"\x00" * 16
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(b"a" * 16) + encryptor.finalize()
    print(f"  [✓] Crypto Check: AES-256-CBC cipher operational (CT SHA256: {hashlib.sha256(ct).hexdigest()[:16]}...)")
except Exception as e:
    print(f"  [✗] Functional Check FAILED: {e}")
    failed += 1

print("=" * 60)
if failed == 0:
    print(f"🎉 TRI-PROOF SUCCESS: All {passed} project dependencies verified in Podman!")
    sys.exit(0)
else:
    print(f"⚠️ VERIFICATION FAILED: {failed} errors detected.")
    sys.exit(1)
