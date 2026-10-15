use core_graphics::event::{CGEvent};
use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
use accessibility_sys::*;
use core_foundation::base::*;
use core_foundation::string::*;
use core_foundation::dictionary::*;
use std::ptr;

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
        
        println!("Element: {:?}", element);
        
        let mut value: CFTypeRef = ptr::null();
        
        let title_attr = CFStringCreateWithCString(kCFAllocatorDefault, b"AXTitle\0".as_ptr() as *const i8, kCFStringEncodingUTF8);
        if AXUIElementCopyAttributeValue(element, title_attr, &mut value) == kAXErrorSuccess {
            println!("AXTitle found");
        } else {
            println!("AXTitle not found");
        }
    }
}
