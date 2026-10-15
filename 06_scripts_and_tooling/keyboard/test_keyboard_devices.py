#!/usr/bin/env python3
import sys
import time
import ctypes

iokit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')

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
kProductKey = cf.CFStringCreateWithCString(None, b"Product", 0x08000100)

key_events = []

def get_dev_name(dev):
    if not dev: return "Unknown"
    prop = iokit.IOHIDDeviceGetProperty(dev, kProductKey)
    if not prop: return "NoProduct"
    buf = ctypes.create_string_buffer(128)
    if cf.CFStringGetCString(prop, buf, 128, 0x08000100):
        return buf.value.decode('utf-8', errors='ignore')
    return "Unknown"

IOHIDValueCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p)

def on_value(context, result, sender, value):
    elem = iokit.IOHIDValueGetElement(value)
    page = iokit.IOHIDElementGetUsagePage(elem)
    usage = iokit.IOHIDElementGetUsage(elem)
    int_val = iokit.IOHIDValueGetIntegerValue(value)
    dev = iokit.IOHIDElementGetDevice(elem)
    dname = get_dev_name(dev)
    
    if page == 7:  # Standard Keyboard Page
        evt = f"[{dname}] Key: Usage 0x{usage:02x} ({usage}), State: {'DOWN' if int_val == 1 else 'UP' if int_val == 0 else int_val}"
        print(f"🔥 {evt}")
        key_events.append(evt)

cb = IOHIDValueCallback(on_value)
iokit.IOHIDManagerRegisterInputValueCallback.argtypes = [ctypes.c_void_p, IOHIDValueCallback, ctypes.c_void_p]

manager = iokit.IOHIDManagerCreate(None, 0)
iokit.IOHIDManagerSetDeviceMatching(manager, None)
iokit.IOHIDManagerRegisterInputValueCallback(manager, cb, None)

iokit.IOHIDManagerScheduleWithRunLoop.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
current_loop = cf.CFRunLoopGetCurrent()
iokit.IOHIDManagerScheduleWithRunLoop(manager, current_loop, kCFRunLoopDefaultMode)
iokit.IOHIDManagerOpen(manager, 0)

print("Filtering strictly for KEYBOARD events (Usage Page 7). Listening for 5s...")
start = time.time()
while time.time() - start < 5.0:
    cf.CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.2, False)

print(f"Keyboard events captured: {len(key_events)}")
