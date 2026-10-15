use core_graphics::event::{CGEvent};
use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
fn main() {
    let source = CGEventSource::new(CGEventSourceStateID::HIDSystemState).unwrap();
    let event = CGEvent::new(source).unwrap();
    let point = event.location();
    println!("Mouse at: {:?}", point);
}
