#!/usr/bin/env python3
"""
06_scripts_and_tooling/keyboard/test_raw_hid_listener.py
=======================================================
Direct IOHIDManager raw input event listener.
Listens to all physical HID keyboard reports for 10 seconds.
"""

import sys
import time
import ctypes

iokit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')

# Types
iokit.IOHIDManagerCreate.restype = ctypes.c_void_p
iokit.IOHIDManagerCreate.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

iokit.IOHIDManagerSetDeviceMatching.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
iokit.IOHIDManagerOpen.restype = ctypes.c_int32
iokit.IOHIDManagerOpen.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

iokit.IOHIDValueGetElement.restype = ctypes.c_void_p
iokit.IOHIDValueGetElement.argtypes = [ctypes.c_void_p]

iokit.IOHIDElementGetUsagePage.restype = ctypes.c_uint32
iokit.IOHIDElementGetUsagePage.argtypes = [ctypes.c_void_p]

iokit.IOHIDElementGetUsage.restype = ctypes.c_uint32
iokit.IOHIDElementGetUsage.argtypes = [ctypes.c_void_p]

iokit.IOHIDValueGetIntegerValue.restype = ctypes.c_int64
iokit.IOHIDValueGetIntegerValue.argtypes = [ctypes.c_void_p]

iokit.IOHIDElementGetDevice.restype = ctypes.c_void_p
iokit.IOHIDElementGetDevice.argtypes = [ctypes.c_void_p]

iokit.IOHIDDeviceGetProperty.restype = ctypes.c_void_p
iokit.IOHIDDeviceGetProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

cf.CFStringCreateWithCString.restype = ctypes.c_void_p
cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]

cf.CFStringGetCString.restype = ctypes.c_bool
cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]

cf.CFRunLoopGetCurrent.restype = ctypes.c_void_p
cf.CFRunLoopRunInMode.restype = ctypes.c_int32
cf.CFRunLoopRunInMode.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_bool]

kCFRunLoopDefaultMode = cf.CFStringCreateWithCString(None, b"kCFRunLoopDefaultMode", 0x08000100)

received_events = []

IOHIDValueCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p)

def on_value(context, result, sender, value):
    elem = iokit.IOHIDValueGetElement(value)
    page = iokit.IOHIDElementGetUsagePage(elem)
    usage = iokit.IOHIDElementGetUsage(elem)
    int_val = iokit.IOHIDValueGetIntegerValue(value)
    
    # We care about keyboard events (page 7) or consumer controls (page 12)
    if page == 7 or page == 12:
        evt = f"Page: 0x{page:02x}, Usage: 0x{usage:02x} ({usage}), State: {'DOWN' if int_val == 1 else 'UP' if int_val == 0 else int_val}"
        print(f"[*] RAW HID EVENT DETECTED: {evt}")
        received_events.append(evt)

cb = IOHIDValueCallback(on_value)
iokit.IOHIDManagerRegisterInputValueCallback.argtypes = [ctypes.c_void_p, IOHIDValueCallback, ctypes.c_void_p]

manager = iokit.IOHIDManagerCreate(None, 0)
iokit.IOHIDManagerSetDeviceMatching(manager, None) # Match all HID devices
iokit.IOHIDManagerRegisterInputValueCallback(manager, cb, None)

iokit.IOHIDManagerScheduleWithRunLoop.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
current_loop = cf.CFRunLoopGetCurrent()
iokit.IOHIDManagerScheduleWithRunLoop(manager, current_loop, kCFRunLoopDefaultMode)

res = iokit.IOHIDManagerOpen(manager, 0)
print(f"IOHIDManager Open result: {res} (0 = SUCCESS)")
print("================================================================")
print("Listening for 8 seconds for ANY hardware keyboard activity...")
print("================================================================")

start = time.time()
while time.time() - start < 8.0:
    cf.CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.5, False)

print("================================================================")
print(f"Total RAW HID Keyboard Events captured: {len(received_events)}")
if len(received_events) == 0:
    print("⚠️ ZERO hardware HID events were detected during the window.")
else:
    print(f"✅ Received {len(received_events)} events successfully.")
