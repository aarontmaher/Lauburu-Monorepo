use crate::model::{AppEntry, AppLiveStatus};
use std::collections::HashMap;
use std::net::{TcpStream, ToSocketAddrs};
use std::path::Path;
use std::process::Command;
use std::time::{Duration, Instant};

pub fn probe_app_status(entry: &AppEntry, repo_root: &Path) -> AppLiveStatus {
    let mut status = AppLiveStatus::default();

    // 1. Check Port Listening & Latency
    if let Some(port) = entry.port {
        let addr_str = format!("127.0.0.1:{}", port);
        let start = Instant::now();
        if let Ok(mut addrs) = addr_str.to_socket_addrs() {
            if let Some(addr) = addrs.next() {
                if let Ok(_stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(50)) {
                    let elapsed = start.elapsed().as_secs_f64() * 1000.0;
                    status.port_online = true;
                    status.rtt_ms = Some((elapsed * 10.0).round() / 10.0);
                }
            }
        }
    }

    // 2. Check Process by Port or Process Name
    let mut found_pid = None;
    if let Some(port) = entry.port {
        // Fast lsof port query
        if let Ok(output) = Command::new("lsof")
            .args(["-i", &format!(":{}", port), "-t"])
            .output()
        {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                if let Some(first_line) = stdout.lines().next() {
                    if let Ok(pid) = first_line.trim().parse::<u32>() {
                        found_pid = Some(pid);
                    }
                }
            }
        }
    }

    // Fallback: check PID file in .logs
    if found_pid.is_none() {
        let pid_file = repo_root.join("01_apps/.logs").join(format!("{}.pid", entry.id));
        if pid_file.exists() {
            if let Ok(content) = std::fs::read_to_string(&pid_file) {
                if let Ok(pid) = content.trim().parse::<u32>() {
                    // Verify if PID is genuinely active
                    let check = Command::new("kill").args(["-0", &pid.to_string()]).output();
                    if let Ok(c) = check {
                        if c.status.success() {
                            found_pid = Some(pid);
                        }
                    }
                }
            }
        }
    }

    if let Some(pid) = found_pid {
        status.is_running = true;
        status.pid = Some(pid);

        // Fetch genuine CPU% and RSS from ps
        if let Ok(ps_out) = Command::new("ps")
            .args(["-p", &pid.to_string(), "-o", "%cpu,rss"])
            .output()
        {
            if ps_out.status.success() {
                let s = String::from_utf8_lossy(&ps_out.stdout);
                if let Some(data_line) = s.lines().nth(1) {
                    let parts: Vec<&str> = data_line.split_whitespace().collect();
                    if parts.len() >= 2 {
                        if let Ok(cpu) = parts[0].parse::<f32>() {
                            status.cpu_pct = Some(cpu);
                        }
                        if let Ok(rss_kb) = parts[1].parse::<f32>() {
                            status.rss_mb = Some((rss_kb / 1024.0 * 10.0).round() / 10.0);
                        }
                    }
                }
            }
        }
    }

    // 3. Format Status Label
    if status.is_running && status.port_online {
        let rtt = status.rtt_ms.unwrap_or(0.0);
        let rss = status.rss_mb.unwrap_or(0.0);
        status.status_label = format!("🟢 ACTIVE (PID {}, {:.1}MB, {:.1}ms)", status.pid.unwrap_or(0), rss, rtt);
    } else if status.port_online {
        let rtt = status.rtt_ms.unwrap_or(0.0);
        status.status_label = format!("🟢 LISTENING (:{}, {:.1}ms)", entry.port.unwrap_or(0), rtt);
    } else if status.is_running {
        status.status_label = format!("🟡 RUNNING (PID {})", status.pid.unwrap_or(0));
    } else {
        status.status_label = "⚪ STOPPED".to_string();
    }

    status
}

pub fn probe_all_apps(apps: &[AppEntry], repo_root: &Path) -> HashMap<&'static str, AppLiveStatus> {
    let mut map = HashMap::new();
    for app in apps {
        let status = probe_app_status(app, repo_root);
        map.insert(app.id, status);
    }
    map
}

pub fn read_app_readme_snippet(entry: &AppEntry, repo_root: &Path, max_lines: usize) -> Vec<String> {
    let app_dir = repo_root.join(entry.path);
    let readme_path = app_dir.join("README.md");
    if readme_path.exists() {
        if let Ok(content) = std::fs::read_to_string(&readme_path) {
            return content
                .lines()
                .take(max_lines)
                .map(|s| s.to_string())
                .collect();
        }
    }
    vec![
        format!("# {}", entry.name),
        "".to_string(),
        entry.description.to_string(),
        "".to_string(),
        format!("**Tech Stack:** {}", entry.tech_stack.join(", ")),
        format!("**Monorepo Path:** {}", entry.path),
    ]
}
