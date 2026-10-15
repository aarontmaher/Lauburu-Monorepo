use core_graphics::event::{CGEvent};
use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
use accessibility_sys::*;
use core_foundation::base::*;
use core_foundation::string::*;
use std::ptr;

unsafe fn get_cfstring(s: CFStringRef) -> String {
    let len = CFStringGetLength(s);
    let mut buf = vec![0u16; len as usize];
    CFStringGetCharacters(s, CFRange { location: 0, length: len }, buf.as_mut_ptr());
    String::from_utf16_lossy(&buf)
}

unsafe fn get_attr_string(element: AXUIElementRef, attr_name: &str) -> Option<String> {
    let attr_cfstr = CFStringCreateWithCString(
        kCFAllocatorDefault,
        std::ffi::CString::new(attr_name).unwrap().as_ptr(),
        kCFStringEncodingUTF8,
    );
    let mut value: CFTypeRef = ptr::null();
    let err = AXUIElementCopyAttributeValue(element, attr_cfstr, &mut value);
    CFRelease(attr_cfstr as _);
    
    if err == kAXErrorSuccess && !value.is_null() {
        let type_id = CFGetTypeID(value);
        if type_id == CFStringGetTypeID() {
            let s = get_cfstring(value as CFStringRef);
            CFRelease(value);
            return Some(s);
        }
        CFRelease(value);
    }
    None
}

unsafe fn get_window_title(element: AXUIElementRef) -> Option<String> {
    let attr_cfstr = CFStringCreateWithCString(
        kCFAllocatorDefault,
        b"AXWindow\0".as_ptr() as *const i8,
        kCFStringEncodingUTF8,
    );
    let mut window_val: CFTypeRef = ptr::null();
    let err = AXUIElementCopyAttributeValue(element, attr_cfstr, &mut window_val);
    CFRelease(attr_cfstr as _);
    
    if err == kAXErrorSuccess && !window_val.is_null() {
        let title = get_attr_string(window_val as AXUIElementRef, "AXTitle");
        CFRelease(window_val);
        return title;
    }
    None
}

fn main() {
    unsafe {
        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
        let event = CGEvent::new(source).unwrap();
        let point = event.location();

        let system_wide = AXUIElementCreateSystemWide();
        let mut element: AXUIElementRef = ptr::null_mut();
        
        if AXUIElementCopyElementAtPosition(system_wide, point.x as f32, point.y as f32, &mut element) == kAXErrorSuccess {
            println!("Window Title: {:?}", get_window_title(element));
            for attr in &["AXValue", "AXTitle", "AXDescription", "AXHelp"] {
                if let Some(val) = get_attr_string(element, attr) {
                    println!("{}: {}", attr, val);
                }
            }
        }
    }
}
