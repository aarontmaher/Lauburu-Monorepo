use accessibility_sys::*;
use core_foundation::base::*;
use core_foundation::string::*;
use core_foundation::dictionary::*;
use std::ptr;

fn main() {
    unsafe {
        let system_wide = AXUIElementCreateSystemWide();
        println!("system_wide: {:?}", system_wide);
    }
}
