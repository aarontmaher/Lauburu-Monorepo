use rdev::{listen, Event, EventType};
use rusqlite::{params, Connection};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use std::fs;
use std::path::Path;
use std::ptr;
use std::env;
use std::net::TcpStream;
use std::io::Write;
use std::thread;

use core_graphics::event::CGEvent;
use core_graphics::event_source::{CGEventSource, CGEventSourceStateID};
use accessibility_sys::*;
use core_foundation::base::*;
use core_foundation::string::*;

unsafe fn get_cfstring(s: CFStringRef) -> String {
    let len = CFStringGetLength(s);
    let mut buf = vec![0u16; len as usize];
    CFStringGetCharacters(s, CFRange { location: 0, length: len }, buf.as_mut_ptr());
    String::from_utf16_lossy(&buf)
}

unsafe fn get_attr_string(element: AXUIElementRef, attr_name: &str) -> Option<String> {
    let c_str = match std::ffi::CString::new(attr_name) {
        Ok(c) => c,
        Err(_) => return None,
    };
    let attr_cfstr = CFStringCreateWithCString(
        kCFAllocatorDefault,
        c_str.as_ptr(),
        kCFStringEncodingUTF8,
    );
    if attr_cfstr.is_null() {
        return None;
    }
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
    if attr_cfstr.is_null() {
        return None;
    }
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

fn extract_accessibility_info() -> (Option<String>, Option<String>) {
    unsafe {
        let source_res = CGEventSource::new(CGEventSourceStateID::HIDSystemState);
        let source = match source_res {
            Ok(s) => s,
            Err(_) => return (None, None),
        };
        let event_res = CGEvent::new(source);
        let event = match event_res {
            Ok(e) => e,
            Err(_) => return (None, None),
        };
        let point = event.location();

        let system_wide = AXUIElementCreateSystemWide();
        if system_wide.is_null() {
            return (None, None);
        }
        let mut element: AXUIElementRef = ptr::null_mut();
        
        if AXUIElementCopyElementAtPosition(system_wide, point.x as f32, point.y as f32, &mut element) == kAXErrorSuccess {
            let window_title = get_window_title(element);
            
            let mut element_text = None;
            for attr in &["AXValue", "AXTitle", "AXDescription", "AXHelp"] {
                if let Some(val) = get_attr_string(element, attr) {
                    element_text = Some(val);
                    break;
                }
            }
            
            CFRelease(system_wide as _);
            if !element.is_null() {
                CFRelease(element as _);
            }
            return (window_title, element_text);
        }
        CFRelease(system_wide as _);
    }
    (None, None)
}

fn post_event_to_hub(hub_addr: &str, device_id: &str, event_type: &str, timestamp: i64,
                     window_title: &Option<String>, element_text: &Option<String>) {
    let hub = hub_addr.to_string();
    let dev = device_id.to_string();
    let et = event_type.to_string();
    let wt = window_title.clone();
    let el = element_text.clone();

    thread::spawn(move || {
        let wt_json = wt.map(|w| format!("\"{}\"", w.replace('\\', "\\\\").replace('"', "\\\""))).unwrap_or_else(|| "null".to_string());
        let el_json = el.map(|e| format!("\"{}\"", e.replace('\\', "\\\\").replace('"', "\\\""))).unwrap_or_else(|| "null".to_string());
        let payload = format!(
            "{{\"device_id\":\"{}\",\"event_type\":\"{}\",\"timestamp\":{},\"window_title\":{},\"element_text\":{}}}",
            dev, et, timestamp, wt_json, el_json
        );

        if let Ok(mut stream) = TcpStream::connect(&hub) {
            let req = format!(
                "POST /api/timeline/event HTTP/1.1\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                hub, payload.len(), payload
            );
            let _ = stream.write_all(req.as_bytes());
        }
    });
}

fn setup_db(db_path: &Path) -> rusqlite::Result<Connection> {
    if let Some(parent) = db_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let conn = Connection::open(db_path)?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL DEFAULT 'L1_Mac_Node',
            event_type TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            window_title TEXT,
            element_text TEXT,
            audio_transcript TEXT,
            metadata TEXT
        )",
        [],
    )?;
    Ok(conn)
}

struct AppConfig {
    device_id: String,
    hub_addr: Option<String>,
    db_conn: Option<Arc<Mutex<Connection>>>,
}

fn callback(event: Event, config: Arc<AppConfig>) {
    let mut event_type_str = None;
    let mut is_click = false;
    match event.event_type {
        EventType::KeyPress(_) => event_type_str = Some("KeyPress"),
        EventType::KeyRelease(_) => event_type_str = Some("KeyRelease"),
        EventType::ButtonPress(_) => {
            event_type_str = Some("ButtonPress");
            is_click = true;
        },
        EventType::ButtonRelease(_) => event_type_str = Some("ButtonRelease"),
        EventType::Wheel { .. } => event_type_str = Some("Wheel"),
        EventType::MouseMove { .. } => {},
    }

    if let Some(et_str) = event_type_str {
        let (mut window_title, mut element_text) = (None, None);
        if is_click {
            let info = extract_accessibility_info();
            window_title = info.0;
            element_text = info.1;
        }
        
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as i64;
        
        // Log to local DB if configured
        if let Some(ref db_arc) = config.db_conn {
            if let Ok(conn) = db_arc.lock() {
                let _ = conn.execute(
                    "INSERT INTO timeline (device_id, event_type, timestamp, window_title, element_text) VALUES (?1, ?2, ?3, ?4, ?5)",
                    params![config.device_id, et_str, now, window_title, element_text],
                );
            }
        }

        // Post to remote hub if configured
        if let Some(ref hub) = config.hub_addr {
            post_event_to_hub(hub, &config.device_id, et_str, now, &window_title, &element_text);
        }

        println!("[{}] {} at {} (Title: {:?}, Text: {:?})", config.device_id, et_str, now, window_title, element_text);
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut device_id = "L1_Mac_Node".to_string();
    let mut hub_addr = None;
    let mut db_path_opt = Some("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/screen_lens_timeline.db".to_string());

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--device-id" => {
                if i + 1 < args.len() {
                    device_id = args[i + 1].clone();
                    i += 1;
                }
            },
            "--hub-addr" => {
                if i + 1 < args.len() {
                    hub_addr = Some(args[i + 1].clone());
                    i += 1;
                }
            },
            "--db-path" => {
                if i + 1 < args.len() {
                    db_path_opt = Some(args[i + 1].clone());
                    i += 1;
                }
            },
            "--no-local-db" => {
                db_path_opt = None;
            },
            _ => {}
        }
        i += 1;
    }

    let mut db_conn = None;
    if let Some(ref db_path_str) = db_path_opt {
        let db_path = Path::new(db_path_str);
        if let Ok(c) = setup_db(db_path) {
            println!("Local DB configured at {}", db_path_str);
            db_conn = Some(Arc::new(Mutex::new(c)));
        } else {
            println!("Could not open local DB at {}, falling back to hub only.", db_path_str);
        }
    }

    let config = Arc::new(AppConfig {
        device_id: device_id.clone(),
        hub_addr: hub_addr.clone(),
        db_conn,
    });

    println!("Starting capture daemon for device '{}' (hub: {:?})...", device_id, hub_addr);
    
    let config_clone = Arc::clone(&config);
    if let Err(error) = listen(move |event| callback(event, Arc::clone(&config_clone))) {
        eprintln!("Error listening for events: {:?}", error);
    }
}
