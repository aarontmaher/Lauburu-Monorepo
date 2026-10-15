# Sovereign Lens Bootstrapper & Telemetry Core

Ultra-lightweight, zero-dependency C++17 bootstrapper daemon and kernel telemetry engine governing the Sovereign Lens runtime across the Lauburu ecosystem.

## Architectural Overview

`lens_bootstrapper` runs on system boot as an ultra-lightweight supervisor daemon (`< 10 MB` RAM ceiling; empirically measured **~1.64 MB RSS** on Apple Silicon M4 Pro). It executes continuous zero-fork kernel telemetry, manages the local Python/MLX/TFLite supervisor child process with process group isolation and exponential backoff, and provides a line-delimited ASCII/JSON Unix Domain Socket control plane.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   LENS BOOTSTRAPPER ARCHITECTURE                      │
├────────────────────────────────────────────────────────────────────────┤
│  lens_bootstrapper (Daemon PID, RSS: ~1.64 MB)                         │
│    ├── SystemTelemetry Engine:                                         │
│    │     • macOS: Mach host_statistics64(), notify.h, getifaddrs()      │
│    │     • Linux: /proc/meminfo, /sys/class/thermal, /proc/net/dev     │
│    ├── ProcessSupervisor:                                              │
│    │     • fork() + setpgid() process group isolation                  │
│    │     • Non-blocking waitpid() crash detection                      │
│    │     • Exponential backoff crash recovery (1s..30s)                │
│    │     • Non-blocking TCP connect liveness probe                     │
│    │     • Graceful SIGTERM -> 5s timeout -> SIGKILL reaping           │
│    ├── UnixSocketServer:                                               │
│    │     • Endpoint: ~/.lauburu/lens_bootstrapper.sock (0600)          │
│    │     • Non-blocking poll() multiplexing (STATUS, TELEMETRY, etc.)  │
│    └── Thermal Signal Dispatcher:                                      │
│          • Writes /tmp/thermal_offload_signal.json on level >= 2       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ spawns child process group
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Child Supervisor (e.g., local_lens_supervisor.py / MLX Engine)        │
└────────────────────────────────────────────────────────────────────────┘
```

## Features (Milestone 1, F1 - F6)

- **F1: CMake Build Configuration**: Clean CMake setup building static telemetry library (`lens_telemetry`), standalone daemon (`lens_bootstrapper`), companion CLI (`lens_bootstrapper_ctl`), and unit tests using `-O2 -fno-rtti -fno-exceptions` (zero third-party dependencies).
- **F2: C++ Bootstrapper Daemon Core**: Event loop handling `SIGTERM`, `SIGINT`, `SIGHUP` (supervisor reload), CLI arguments (`--foreground`, `--daemon`, `--config`, `--test-run`), and baseline idle RAM < 2 MB.
- **F3: Zero-Fork Kernel Telemetry Engine**: Direct Mach kernel `host_statistics64` VM accounting, `<notify.h>` thermal state (`com.apple.system.thermalpressurelevel`), `<ifaddrs.h>` network throughput on macOS; `/proc` and `/sys` parsers on Linux.
- **F4: Supervisor Process Manager**: POSIX `fork()`/`execvp()` with `setpgid()`, non-blocking `waitpid()`, exponential backoff ($1\text{s} \to 2\text{s} \to 4\text{s} \dots \max 30\text{s}$), non-blocking TCP liveness probe, and clean `SIGTERM \to \text{5s} \to \text{SIGKILL}` reaping.
- **F5: Zero-Overhead Unix Domain Socket IPC**: Non-blocking `poll()` socket server at `~/.lauburu/lens_bootstrapper.sock` with companion CLI `lens_bootstrapper_ctl` supporting `STATUS`, `TELEMETRY`, `RESTART_SUPERVISOR`, `STOP`, and `PING`.
- **F6: Production Service Manifests**: macOS LaunchAgent (`config/com.lauburu.lens-bootstrapper.plist`) and Linux systemd unit (`config/lens-bootstrapper.service`).

---

## Directory Layout

```
00_core_infrastructure/lens_bootstrapper/
├── CMakeLists.txt                         # Root CMake build configuration
├── README.md                              # Technical documentation
├── config/
│   ├── lens_bootstrapper.json             # Runtime configuration
│   ├── com.lauburu.lens-bootstrapper.plist# macOS LaunchAgent manifest
│   └── lens-bootstrapper.service          # Linux systemd service unit
├── include/
│   ├── bootstrapper_daemon.hpp            # Daemon coordinator & signal handling
│   ├── telemetry/
│   │   ├── system_telemetry.hpp           # Cross-platform telemetry interface
│   │   ├── darwin_telemetry.hpp           # Mach kernel & notify.h provider
│   │   └── linux_telemetry.hpp            # /proc & /sys provider
│   ├── supervisor/
│   │   └── process_supervisor.hpp         # Process lifecycle & health prober
│   ├── ipc/
│   │   └── unix_socket_server.hpp         # Unix domain socket server
│   └── utils/
│       ├── logger.hpp                     # Low-overhead timestamped logger
│       └── json_writer.hpp                # Minimal JSON serializer & parser
├── src/
│   ├── main.cpp                           # Daemon entrypoint
│   ├── bootstrapper_daemon.cpp            # Main event loop & telemetry timer
│   ├── telemetry/
│   │   ├── system_telemetry.cpp           # Telemetry provider factory & rate math
│   │   ├── darwin_telemetry.cpp           # Mach VM & BSD network counters
│   │   └── linux_telemetry.cpp            # Linux sysfs/procfs counters
│   ├── supervisor/
│   │   └── process_supervisor.cpp         # Child spawn, waitpid, TCP ping, reaping
│   ├── ipc/
│   │   └── unix_socket_server.cpp         # Poll-based socket server
│   ├── ctl/
│   │   └── lens_bootstrapper_ctl.cpp      # Companion CLI client
│   └── utils/
│       ├── logger.cpp                     # POSIX I/O logger
│       └── json_writer.cpp                # Zero-allocation JSON string writer
└── tests/
    ├── test_bootstrapper_telemetry.cpp    # Real Mach/Linux telemetry test
    ├── test_bootstrapper_supervisor.cpp   # Child lifecycle & signal test
    └── test_bootstrapper_ipc.cpp          # IPC command/response test
```

---

## Building and Testing

### Prerequisites
- Clang (Apple Clang 15+ / Clang 12+) or GCC 10+
- CMake 3.16+
- POSIX-compliant operating system (macOS or Linux)

### Compilation
```bash
cd 00_core_infrastructure/lens_bootstrapper
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j4
```

### Running Unit Tests
```bash
ctest --output-on-failure
```
All unit tests pass with exit code 0:
- `test_bootstrapper_telemetry`: Verifies real physical Mach/procfs memory numbers, valid thermal states ($0 \le \text{pressure} \le 3$), and active interface byte counters.
- `test_bootstrapper_supervisor`: Verifies child fork, exit detection, exponential backoff, and graceful process group termination.
- `test_bootstrapper_ipc`: Verifies socket creation, non-blocking client connections, line protocol, and clean unlinking.

---

## CLI Usage

### Running the Daemon

```bash
# Foreground execution (standard under launchd / systemd)
./build/lens_bootstrapper --foreground

# Background daemon mode (POSIX double-fork)
./build/lens_bootstrapper --daemon

# Test run mode (runs for 3 seconds, exercises telemetry, and exits 0)
./build/lens_bootstrapper --test-run

# Custom config file or supervisor command
./build/lens_bootstrapper --config config/lens_bootstrapper.json --supervisor-cmd "python3 worker.py"
```

### Using the Companion CLI (`lens_bootstrapper_ctl`)

```bash
# Query daemon and supervisor status
./build/lens_bootstrapper_ctl status
# Output: {"status": "RUNNING", "pid": 35196, "supervisor_pid": 35201, "supervisor_status": "ALIVE", "uptime_sec": 42}

# Query real-time kernel telemetry
./build/lens_bootstrapper_ctl telemetry
# Output: {"timestamp": 1791671979, "ram_total_bytes": 25769803776, "ram_free_bytes": 860536832, "ram_avail_bytes": 4696686592, "ram_used_bytes": 21496070144, "vm_pressure": 2, "thermal_pressure": 0, "net_rx_bps": 125090, "net_tx_bps": 2635636, "net_rx_bytes": 4300743680, "net_tx_bytes": 7702360064}

# Gracefully restart the child supervisor
./build/lens_bootstrapper_ctl restart_supervisor
# Output: {"result": "RESTARTING", "old_pid": 35201}

# Test IPC socket connectivity
./build/lens_bootstrapper_ctl ping
# Output: {"result": "PONG"}

# Stop the daemon and child process
./build/lens_bootstrapper_ctl stop
# Output: {"result": "STOPPING"}
```

---

## Empirical Memory Verification

Audited on Apple M4 Pro (macOS 15.6 Darwin 25.6.0 arm64):
```
$ ps -o pid,rss,vsz,comm -p 35196
  PID    RSS      VSZ COMM
35196   1680 435307024 /Volumes/Lauburu-Monorepo/00_core_infrastructure/lens_bootstrapper/build/lens_bootstrapper
```
- **Resident Set Size (RSS)**: **1680 KB (1.64 MB)**
- **Baseline RAM Limit**: `< 10 MB`
- **Safety Margin**: **83.6% headroom below the 10 MB limit**

---

## Service Installation

### macOS LaunchAgent
```bash
cp config/com.lauburu.lens-bootstrapper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lauburu.lens-bootstrapper.plist
```

### Linux systemd Unit
```bash
sudo cp config/lens-bootstrapper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lens-bootstrapper.service
```
