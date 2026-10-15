#!/usr/bin/env python3
"""
06_scripts_and_tooling/keyboard/emergency_key_release.py
========================================================
Emergency utility to clear any stuck modifier keys or mouse buttons
in macOS WindowServer via CoreGraphics.
"""

import sys
import ctypes

def release_all_keys():
    if sys.platform != "darwin":
        print("emergency_key_release is only applicable on macOS Darwin.")
        return 0

    try:
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    except Exception as e:
        print(f"Failed to load CoreGraphics/CoreFoundation: {e}")
        return 1

    class CGPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    cf.CFRelease.argtypes = [ctypes.c_void_p]
    cf.CFRelease.restype = None

    cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]

    cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    cg.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32]

    cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    cg.CGEventCreate.restype = ctypes.c_void_p
    cg.CGEventCreate.argtypes = [ctypes.c_void_p]
    cg.CGEventGetLocation.restype = CGPoint
    cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]

    modifier_keycodes = [54, 55, 56, 57, 58, 59, 60, 61, 62, 63]

    print("[Emergency Key Release] Posting KeyUp for all modifier keys...")
    for kc in modifier_keycodes:
        ev = cg.CGEventCreateKeyboardEvent(None, kc, False)
        if ev:
            cg.CGEventPost(0, ev)
            cf.CFRelease(ev)

    ev_mouse = cg.CGEventCreate(None)
    if ev_mouse:
        loc = cg.CGEventGetLocation(ev_mouse)
        cf.CFRelease(ev_mouse)
        ev_left_up = cg.CGEventCreateMouseEvent(None, 2, loc, 0)
        if ev_left_up:
            cg.CGEventPost(0, ev_left_up)
            cf.CFRelease(ev_left_up)
        ev_right_up = cg.CGEventCreateMouseEvent(None, 4, loc, 1)
        if ev_right_up:
            cg.CGEventPost(0, ev_right_up)
            cf.CFRelease(ev_right_up)

    print("Successfully cleared all modifier and mouse button states.")
    return 0

if __name__ == "__main__":
    sys.exit(release_all_keys())
