use core_graphics::event::{CGEvent};
use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
use accessibility_sys::*;
use core_foundation::base::*;
use core_foundation::string::*;
use core_foundation::array::*;
use std::ptr;

unsafe fn get_cfstring(s: CFStringRef) -> String {
    let len = CFStringGetLength(s);
    let mut buf = vec![0u16; len as usize];
    CFStringGetCharacters(s, CFRange { location: 0, length: len }, buf.as_mut_ptr());
    String::from_utf16_lossy(&buf)
}

fn main() {
    unsafe {
        let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
        let event = CGEvent::new(source).unwrap();
        let point = event.location();

        let system_wide = AXUIElementCreateSystemWide();
        let mut element: AXUIElementRef = ptr::null_mut();
        
        let err = AXUIElementCopyElementAtPosition(
            system_wide,
            point.x as f32,
            point.y as f32,
            &mut element,
        );
        
        if err != kAXErrorSuccess {
            println!("Error at pos: {}", err);
            return;
        }
        
        let mut names: CFArrayRef = ptr::null();
        if AXUIElementCopyAttributeNames(element, &mut names) == kAXErrorSuccess {
            let count = CFArrayGetCount(names);
            for i in 0..count {
                let name = CFArrayGetValueAtIndex(names, i) as CFStringRef;
                println!("Attribute: {}", get_cfstring(name));
            }
        }
    }
}
