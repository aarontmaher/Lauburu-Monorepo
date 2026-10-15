"""
test_virtual_screen_management.py — Comprehensive Zero-Mock E2E Verification Suite
===================================================================================
Validates the VirtualScreenManager implementation against live macOS WindowServer,
BetterDisplay CLI, CoreGraphics (Quartz), and system_profiler.

Test Coverage:
  1. BetterDisplay binary discovery & version check
  2. JSON stream parsing from BetterDisplay get -identifiers
  3. Single-shot virtual screen provisioning with immediate WindowServer attachment
  4. CoreGraphics and system_profiler registration verification (Vendor ID 2198 / 0x896)
  5. Dynamic resolution re-configuration (1080p <-> 1440p)
  6. Sub-15ms in-memory frame buffer capture via Quartz.CGDisplayCreateImage (asserts len > 5000)
  7. Discard safety invariant (raises ValueError if tag_id is empty/None)
  8. Clean teardown and verification of WindowServer display removal
  9. Context manager lifecycle (managed_virtual_screen)
  10. Asynchronous methods verification (async_create, async_set_resolution, async_discard)

Rules Compliance:
  - Rule 0 & Rule 1: Zero simulated metrics, fake arrays, or mock objects. Live system tests only.
  - Rule 3: Host RAM sanctuary headroom preservation. Zero osascript WindowServer polling.
"""

import asyncio
import io
import os
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
from PIL import Image

# Ensure screen_lens is in python path
_screen_lens_dir = Path(__file__).resolve().parent.parent
if str(_screen_lens_dir) not in sys.path:
    sys.path.insert(0, str(_screen_lens_dir))

from virtual_screen_manager import (
    VirtualScreenManager,
    DisplayVerificationResult,
    DisplayCreationError,
    QUARTZ_AVAILABLE,
    PIL_AVAILABLE,
)

if QUARTZ_AVAILABLE:
    import Quartz


TEST_SCREEN_PREFIX = "Lauburu_M1_Test"


@pytest.fixture(scope="session")
def manager() -> VirtualScreenManager:
    """Fixture providing a configured VirtualScreenManager."""
    mgr = VirtualScreenManager(auto_cleanup=True)
    if not mgr.is_available():
        pytest.skip(f"BetterDisplay binary unavailable at: {mgr.cli_path}")
    return mgr


@pytest.fixture(autouse=True)
def cleanup_leftover_screens(manager: VirtualScreenManager) -> Generator[None, None, None]:
    """Ensure no test screens linger before or after each test."""
    manager.cleanup_all_virtual_screens(prefix=TEST_SCREEN_PREFIX)
    yield
    manager.cleanup_all_virtual_screens(prefix=TEST_SCREEN_PREFIX)
    time.sleep(0.3)


# ============================================================================
# Test Cases
# ============================================================================

def test_01_binary_discovery_and_availability(manager: VirtualScreenManager):
    """Verify BetterDisplay binary is discovered, executable, and responds to CLI commands."""
    assert manager.is_available() is True
    assert Path(manager.cli_path).is_file()
    assert os.access(manager.cli_path, os.X_OK)

    res = manager._run_cli(["help"])
    assert res.returncode == 0
    assert "BetterDisplay Version" in res.stdout
    assert "create" in res.stdout
    assert "discard" in res.stdout


def test_02_display_enumeration_and_json_parsing(manager: VirtualScreenManager):
    """Verify get -identifiers parses non-standard JSON stream into structured records."""
    identifiers = manager.get_display_identifiers()
    assert isinstance(identifiers, list)
    assert len(identifiers) >= 1, "At least one device/group must be registered"

    all_displays = manager.list_all_displays()
    assert isinstance(all_displays, list)
    assert len(all_displays) >= 1, "Must detect at least the physical display"

    # Find the primary active display
    main_displays = [d for d in all_displays if d.get("is_main")]
    assert len(main_displays) == 1, "Exactly one main display must be active"
    main_disp = main_displays[0]
    assert main_disp["display_id"] > 0
    assert main_disp["is_active"] is True
    assert main_disp["width"] > 0
    assert main_disp["height"] > 0


def test_03_discard_safety_invariant(manager: VirtualScreenManager):
    """
    CRITICAL SAFETY INVARIANT:
    Verify discard_virtual_screen refuses to execute without a valid tag_id
    to prevent accidental mass-deletion of all virtual screens.
    """
    with pytest.raises(ValueError, match="Cannot discard virtual screen without a valid"):
        manager.discard_virtual_screen(None)  # type: ignore

    with pytest.raises(ValueError, match="Cannot discard virtual screen without a valid"):
        manager.discard_virtual_screen("")

    with pytest.raises(ValueError, match="Cannot discard virtual screen without a valid"):
        manager.discard_virtual_screen("   ")

    with pytest.raises(ValueError, match="Cannot discard virtual screen without a valid"):
        manager.discard_virtual_screen("0")


def test_04_create_virtual_screen_and_coregraphics_registration(manager: VirtualScreenManager):
    """Test full single-shot creation, immediate WindowServer attachment, and CoreGraphics registration."""
    screen_name = f"{TEST_SCREEN_PREFIX}_Reg"

    t0 = time.perf_counter()
    info = manager.create_virtual_screen(
        name=screen_name,
        width=1920,
        height=1080,
        aspect_w=16,
        aspect_h=9,
        connected=True,
        hidpi=True,
    )
    creation_time = (time.perf_counter() - t0) * 1000

    print(f"\n[Empirical Telemetry] Virtual screen created in {creation_time:.2f} ms: {info}")

    assert info["name"] == screen_name
    assert info["connected"] is True
    assert info["is_virtual"] is True
    assert info["vendor_id"] == manager.BETTERDISPLAY_VENDOR_ID
    assert int(info["display_id"]) > 0
    assert len(str(info["tag_id"])) > 0

    disp_id = int(info["display_id"])

    # Verify macOS WindowServer registration
    verif = manager.verify_macos_registration(display_name=screen_name, display_id=disp_id)
    assert bool(verif) is True, "DisplayVerificationResult must evaluate to True"
    assert verif.is_registered is True
    assert verif.is_active is True
    assert verif.is_online is True
    assert verif.is_virtual is True
    assert verif.vendor_id == manager.BETTERDISPLAY_VENDOR_ID
    assert verif.width == 1920
    assert verif.height == 1080

    # Cross-reference system_profiler SPDisplaysDataType
    assert verif.get("in_system_profiler") is True, "Virtual display must be registered in system_profiler"


def test_05_dynamic_resolution_switching(manager: VirtualScreenManager):
    """Test dynamic resolution switching between 1080p, 1440p, and back."""
    screen_name = f"{TEST_SCREEN_PREFIX}_Res"

    info = manager.create_virtual_screen(
        name=screen_name,
        width=1920,
        height=1080,
        connected=True,
    )
    tag_id = info["tag_id"]
    disp_id = int(info["display_id"])

    assert Quartz.CGDisplayPixelsWide(disp_id) == 1920
    assert Quartz.CGDisplayPixelsHigh(disp_id) == 1080

    # Switch to 2560x1440
    t0 = time.perf_counter()
    ok = manager.set_resolution(tag_id=tag_id, width=2560, height=1440)
    assert ok is True
    time.sleep(0.3)
    res_time = (time.perf_counter() - t0) * 1000

    new_w = Quartz.CGDisplayPixelsWide(disp_id)
    new_h = Quartz.CGDisplayPixelsHigh(disp_id)
    print(f"\n[Empirical Telemetry] Resolution switched to {new_w}x{new_h} in {res_time:.2f} ms")
    assert new_w == 2560
    assert new_h == 1440

    # Switch back to 1920x1080
    ok = manager.set_resolution(tag_id=tag_id, width=1920, height=1080)
    assert ok is True
    time.sleep(0.3)
    assert Quartz.CGDisplayPixelsWide(disp_id) == 1920
    assert Quartz.CGDisplayPixelsHigh(disp_id) == 1080


def test_06_in_memory_frame_capture_quartz(manager: VirtualScreenManager):
    """
    Test in-memory frame capture via Quartz.CGDisplayCreateImage and ImageIO.
    Verifies Rule 0 empirical proof: JPEG byte length > 5000 and valid image dimensions.
    """
    screen_name = f"{TEST_SCREEN_PREFIX}_Cap"

    info = manager.create_virtual_screen(
        name=screen_name,
        width=1920,
        height=1080,
        connected=True,
    )
    disp_id = int(info["display_id"])

    t0 = time.perf_counter()
    jpeg_bytes = manager.capture_display_frame(disp_id, quality=85)
    capture_time = (time.perf_counter() - t0) * 1000

    print(f"\n[Empirical Telemetry] Frame captured in {capture_time:.2f} ms: {len(jpeg_bytes)} bytes")

    assert isinstance(jpeg_bytes, bytes)
    assert len(jpeg_bytes) > 5000, f"Frame size {len(jpeg_bytes)} bytes must exceed 5000 bytes (Rule 0)"
    assert jpeg_bytes[:2] == b"\xff\xd8", "Must start with JPEG SOI marker (0xFFD8)"
    assert jpeg_bytes[-2:] == b"\xff\xd9", "Must end with JPEG EOI marker (0xFFD9)"

    # Verify PIL can parse the JPEG buffer
    img = Image.open(io.BytesIO(jpeg_bytes))
    assert img.format == "JPEG"
    assert img.width == 1920
    assert img.height == 1080

    # Verify not empty or blank
    extrema = img.convert("L").getextrema()
    assert extrema[1] > 0, "Captured frame must contain non-zero pixel intensity"


def test_07_clean_teardown_and_deregistration(manager: VirtualScreenManager):
    """Test clean teardown and verification that display is deregistered from Quartz WindowServer."""
    screen_name = f"{TEST_SCREEN_PREFIX}_Teardown"

    info = manager.create_virtual_screen(
        name=screen_name,
        width=1920,
        height=1080,
        connected=True,
    )
    tag_id = info["tag_id"]
    disp_id = int(info["display_id"])

    # Verify display was registered
    err, active_disps, _ = Quartz.CGGetActiveDisplayList(32, None, None)
    assert disp_id in active_disps

    # Discard virtual screen
    t0 = time.perf_counter()
    discard_ok = manager.discard_virtual_screen(tag_id)
    assert discard_ok is True

    # Poll Quartz until display is removed
    deregistered = False
    for _ in range(50):
        err, cur_disps, _ = Quartz.CGGetActiveDisplayList(32, None, None)
        if disp_id not in cur_disps:
            deregistered = True
            break
        time.sleep(0.05)

    teardown_time = (time.perf_counter() - t0) * 1000
    print(f"\n[Empirical Telemetry] Display deregistered from WindowServer in {teardown_time:.2f} ms")
    assert deregistered is True, f"Display {disp_id} failed to deregister from WindowServer"

    # Verify it is no longer in list_virtual_screens()
    active_screens = manager.list_virtual_screens()
    matching = [s for s in active_screens if s.get("tag_id") == tag_id]
    assert len(matching) == 0


def test_08_managed_context_manager(manager: VirtualScreenManager):
    """Test managed_virtual_screen context manager creates and discards display automatically."""
    screen_name = f"{TEST_SCREEN_PREFIX}_Ctx"
    captured_disp_id = None

    with manager.managed_virtual_screen(name=screen_name, width=1280, height=720) as screen:
        assert screen["name"] == screen_name
        captured_disp_id = int(screen["displayID"] if "displayID" in screen else screen["display_id"])
        assert captured_disp_id > 0

        # Verify active in Quartz inside context
        err, disps, _ = Quartz.CGGetActiveDisplayList(32, None, None)
        assert captured_disp_id in disps

    # Outside context: verify discarded
    time.sleep(0.5)
    err, disps, _ = Quartz.CGGetActiveDisplayList(32, None, None)
    assert captured_disp_id not in disps


@pytest.mark.asyncio
async def test_09_async_virtual_screen_lifecycle(manager: VirtualScreenManager):
    """Test asynchronous create, resolution modification, and discard operations."""
    screen_name = f"{TEST_SCREEN_PREFIX}_Async"

    # Async create
    info = await manager.async_create_virtual_screen(
        name=screen_name,
        width=1920,
        height=1080,
        connected=True,
    )
    tag_id = info["tag_id"]
    disp_id = int(info["display_id"])

    assert info["name"] == screen_name
    assert disp_id > 0

    # Async list
    screens = await manager.async_list_virtual_screens()
    matching = [s for s in screens if s["tag_id"] == tag_id]
    assert len(matching) == 1

    # Async resolution switch
    ok = await manager.async_set_resolution(tag_id=tag_id, width=1280, height=720)
    assert ok is True
    await asyncio.sleep(0.3)
    assert Quartz.CGDisplayPixelsWide(disp_id) == 1280

    # Async discard
    discard_ok = await manager.async_discard_virtual_screen(tag_id)
    assert discard_ok is True

    # Verify WindowServer removal
    await asyncio.sleep(0.5)
    err, cur_disps, _ = Quartz.CGGetActiveDisplayList(32, None, None)
    assert disp_id not in cur_disps
