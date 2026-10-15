#!/usr/bin/env python3
import Quartz
import ApplicationServices
import sys

def get_ax_app():
    workspace = Quartz.NSWorkspace.sharedWorkspace()
    app = workspace.frontmostApplication()
    if app:
        return ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
    return None

def traverse_ax(node, depth=0, max_depth=10, elements_out=None):
    if elements_out is None:
        elements_out = []
    if depth > max_depth:
        return elements_out

    # Get role
    err, role = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXRole", None)
    role_str = role if err == 0 else "unknown"
    
    # Get title
    err, title = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXTitle", None)
    title_str = title if err == 0 and isinstance(title, str) else ""

    # Get description
    err, desc = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXDescription", None)
    desc_str = desc if err == 0 and isinstance(desc, str) else ""

    # Get position
    err, pos_val = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXPosition", None)
    x, y = 0, 0
    if err == 0:
        success, pos = ApplicationServices.AXValueGetValue(pos_val, ApplicationServices.kAXValueCGPointType, None)
        if success:
            x, y = pos.x, pos.y

    # Get size
    err, size_val = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXSize", None)
    w, h = 0, 0
    if err == 0:
        success, size = ApplicationServices.AXValueGetValue(size_val, ApplicationServices.kAXValueCGSizeType, None)
        if success:
            w, h = size.width, size.height

    val = title_str if title_str else desc_str
    if val or role_str in ['AXWindow', 'AXButton', 'AXGroup']:
        elements_out.append({
            "role": role_str,
            "title": val,
            "x": int(x), "y": int(y), "w": int(w), "h": int(h)
        })

    # Recurse children
    err, children = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXChildren", None)
    if err == 0 and children:
        for child in children:
            traverse_ax(child, depth + 1, max_depth, elements_out)
            
    return elements_out

def dump_macos_ui():
    app = get_ax_app()
    if not app:
        print("[!] No frontmost app found.")
        return []
        
    err, windows = ApplicationServices.AXUIElementCopyAttributeValue(app, "AXWindows", None)
    if err == 0 and windows:
        all_elements = []
        for win in windows:
            traverse_ax(win, 0, 15, all_elements)
        return all_elements
    else:
        print(f"[!] Could not get windows (err {err})")
        return []

def click_macos(x, y):
    print(f"[*] Native macOS click via CGEvent at ({x}, {y})")
    pt = Quartz.CGPoint(x, y)
    
    # Mouse down
    event_down = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, pt, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
    
    # Mouse up
    event_up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, pt, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "click":
        click_macos(int(sys.argv[2]), int(sys.argv[3]))
    else:
        elements = dump_macos_ui()
        for el in elements:
            if el['title']:
                print(f"[{el['role']}] '{el['title']}' at ({el['x']},{el['y']})")
