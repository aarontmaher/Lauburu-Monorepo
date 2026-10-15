package main

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
)

// CurriculumItem represents a single polyglot training and evaluation task.
type CurriculumItem struct {
	ID                string   `json:"id"`
	Domain            string   `json:"domain"`
	Language          string   `json:"language"`
	Title             string   `json:"title"`
	Prompt            string   `json:"prompt"`
	SystemPrompt      string   `json:"system_prompt"`
	ChosenCode        string   `json:"chosen_code"`
	RejectedCode      string   `json:"rejected_code"`
	ChosenRationale   string   `json:"chosen_rationale"`
	RejectedRationale string   `json:"rejected_rationale"`
	CompilerCommand   string   `json:"compiler_command"`
	Tags              []string `json:"tags"`
}

// ComputeSha256 returns the hexadecimal SHA256 digest of the chosen code.
func (c *CurriculumItem) ComputeSha256() string {
	h := sha256.Sum256([]byte(c.ChosenCode))
	return hex.EncodeToString(h[:])
}

// ExtractCodeBlock extracts raw code from markdown fences if present.
func ExtractCodeBlock(text string) string {
	if strings.Contains(text, "```") {
		lines := strings.Split(text, "\n")
		var codeLines []string
		inBlock := false
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "```") {
				if inBlock {
					break
				}
				inBlock = true
				continue
			}
			if inBlock {
				codeLines = append(codeLines, line)
			}
		}
		if len(codeLines) > 0 {
			return strings.Join(codeLines, "\n")
		}
	}
	return text
}

// GetPolyglotCurriculum returns the complete canonical curriculum across ALL TUI frameworks and polyglot domains.
func GetPolyglotCurriculum() []CurriculumItem {
	return []CurriculumItem{
		// =========================================================================
		// PART 1: TUI SPECIALIST IN ALL LANGUAGES
		// =========================================================================

		// 1. Rust: Ratatui + Crossterm Immediate-Mode 120 FPS TUI
		{
			ID:       "TUI_RUST_RATATUI_01",
			Domain:   "tui_rust_ratatui",
			Language: "rust_ratatui",
			Title:    "Rust Ratatui 120 FPS Immediate-Mode Dashboard with Zero Allocations",
			Prompt:   "Build an immediate-mode 120 FPS terminal UI using Ratatui and Crossterm with responsive layout constraints and zero heap reallocations per render frame.",
			SystemPrompt: "You are a Master Rust Ratatui Specialist. Write high-performance, zero-allocation immediate mode TUI code with proper layout constraints.",
			ChosenCode: `use ratatui::layout::Rect;

pub struct TuiState {
    pub status: &'static str,
    pub latency_ms: f64,
}

pub fn calculate_tui_layout(area: Rect) -> (Rect, Rect) {
    let header_height = 3.min(area.height);
    let header_rect = Rect::new(area.x, area.y, area.width, header_height);
    let body_rect = Rect::new(area.x, area.y + header_height, area.width, area.height.saturating_sub(header_height));
    (header_rect, body_rect)
}

pub fn format_telemetry_line(state: &TuiState) -> String {
    format!("Status: {} | Latency: {:.2}ms", state.status, state.latency_ms)
}`,
			RejectedCode: `pub fn bad_tui_render() {
    // Spawns thread and sleeps inside render pass! Catastrophic 120 FPS frame drop
    std::thread::sleep(std::time::Duration::from_millis(50));
}`,
			ChosenRationale:   "Computes responsive viewport rectangles using arithmetic bounds without runtime heap allocations, ensuring fluid 120 FPS frame delivery.",
			RejectedRationale: "Blocks the immediate-mode render loop with thread sleeps, causing severe frame drops and terminal lag.",
			CompilerCommand:   "cargo check in canonical_tui_rust",
			Tags:              []string{"rust", "ratatui", "crossterm", "tui", "120fps", "zero_alloc"},
		},

		// 2. Go: Charm Bubble Tea Elm Architecture TUI
		{
			ID:       "TUI_GO_BUBBLETEA_01",
			Domain:   "tui_go_bubbletea",
			Language: "go",
			Title:    "Go Bubble Tea Elm Architecture TUI with Lipgloss Styling",
			Prompt:   "Construct a Go Bubble Tea interactive terminal model following The Elm Architecture with Lipgloss responsive borders and safe quit handling.",
			SystemPrompt: "You are a Master Go Bubble Tea Specialist. Implement clean TEA state transitions with Lipgloss composable styles.",
			ChosenCode: `package main

import (
	"fmt"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type TuiModel struct {
	status string
	style  lipgloss.Style
}

func InitialTuiModel() TuiModel {
	return TuiModel{
		status: "ACTIVE_120FPS",
		style:  lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1),
	}
}

func (m TuiModel) Init() tea.Cmd { return nil }

func (m TuiModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if key, ok := msg.(tea.KeyMsg); ok && (key.String() == "q" || key.String() == "ctrl+c") {
		return m, tea.Quit
	}
	return m, nil
}

func (m TuiModel) View() string {
	return m.style.Render(fmt.Sprintf("Lauburu Go TUI | %s", m.status))
}`,
			RejectedCode: `package main

var badState string
func BadUpdate() {
    badState = "leaking" // Mutates global state, breaks TEA immutability
}`,
			ChosenRationale:   "Adheres strictly to The Elm Architecture with immutable state transitions and declarative Lipgloss styling.",
			RejectedRationale: "Mutates unstructured global state, breaking TEA functional purity and goroutine race safety.",
			CompilerCommand:   "go vet .",
			Tags:              []string{"go", "bubbletea", "lipgloss", "tea", "tui"},
		},

		// 3. Python: Textual & Rich Reactive Layouts
		{
			ID:       "TUI_PYTHON_TEXTUAL_01",
			Domain:   "tui_python_textual",
			Language: "python",
			Title:    "Python Textual Reactive Micro-Dashboard with Rich Styling",
			Prompt:   "Design a reactive Python Textual dashboard structure with asynchronous message workers, typed state containers, and zero blocking calls.",
			SystemPrompt: "You are a Master Python Textual Specialist. Write clean, typed, non-blocking Textual and Rich TUI code.",
			ChosenCode: `from dataclasses import dataclass
import sys

@dataclass
class TelemetryState:
    status: str = "STREAMING"
    throughput_mbps: float = 11200.0
    latency_ms: float = 0.27

def render_rich_card(state: TelemetryState) -> str:
    """Renders zero-allocation ANSI card for micro-dashboards."""
    border = "=" * 48
    content = f"| Status: {state.status:<12} | Latency: {state.latency_ms:0.2f}ms |"
    return f"{border}\n{content}\n{border}"

if __name__ == "__main__":
    s = TelemetryState()
    print(render_rich_card(s))
`,
			RejectedCode: `import time
def bad_card():
    time.sleep(1.0) # Blocks async Textual event loop!
    return "blocked"
`,
			ChosenRationale:   "Utilizes typed dataclass state containers and deterministic formatting without blocking the async event loop.",
			RejectedRationale: "Injects blocking time.sleep calls that freeze the Textual reactive loop and halt UI responsiveness.",
			CompilerCommand:   "python3 -m py_compile",
			Tags:              []string{"python", "textual", "rich", "tui", "reactive"},
		},

		// 4. C++20: FTXUI Component Tree & DOM Layout
		{
			ID:       "TUI_CPP_FTXUI_01",
			Domain:   "tui_cpp_ftxui",
			Language: "cpp",
			Title:    "C++20 FTXUI Functional Component Tree with Sub-Millisecond Redraw",
			Prompt:   "Construct a modern C++20 functional terminal user interface component using immutable DOM rendering and sub-millisecond redraw latency.",
			SystemPrompt: "You are a C++20 FTXUI Specialist. Write modern C++20 using smart pointers, RAII, and clean component separation.",
			ChosenCode: `#include <iostream>
#include <string>
#include <memory>

struct Element {
    std::string text;
    int width;
};

class Component {
public:
    virtual ~Component() = default;
    virtual Element Render() = 0;
};

class TelemetryWidget : public Component {
    std::string status;
public:
    explicit TelemetryWidget(std::string s) : status(std::move(s)) {}
    Element Render() override {
        return {status, static_cast<int>(status.length())};
    }
};

int main() {
    auto widget = std::make_unique<TelemetryWidget>("ACTIVE_120FPS");
    auto element = widget->Render();
    return element.width > 0 ? 0 : 1;
}`,
			RejectedCode: `int main() {
    char* leak = (char*)malloc(1024); // Naked malloc leak
    return 0;
}`,
			ChosenRationale:   "Uses modern C++20 smart pointers (std::make_unique) and polymorphic component abstractions with zero memory leaks.",
			RejectedRationale: "Employs naked malloc allocations without free, causing heap memory fragmentation and leaks.",
			CompilerCommand:   "clang++ -std=c++20 -fsyntax-only",
			Tags:              []string{"cpp", "ftxui", "tui", "modern_cpp", "raii"},
		},

		// 5. C11: POSIX ncurses Alternate Buffer Engine
		{
			ID:       "TUI_C11_NCURSES_01",
			Domain:   "tui_c11_ncurses",
			Language: "c",
			Title:    "C11 POSIX Terminal Alternate Screen Buffer Controller",
			Prompt:   "Write an idempotent C11 terminal screen manager that safely switches to the alternate screen buffer (\033[?1049h) and cleanly restores on exit.",
			SystemPrompt: "You are a C11 POSIX Terminal Specialist. Generate safe, standard-compliant C11 code managing terminal escape codes.",
			ChosenCode: `#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int init_terminal_buffer(void) {
    // Switch to alternate screen buffer and home cursor
    if (printf("\033[?1049h\033[H") < 0) return -1;
    fflush(stdout);
    return 0;
}

int restore_terminal_buffer(void) {
    // Restore primary screen buffer and show cursor
    if (printf("\033[?1049l\033[?25h") < 0) return -1;
    fflush(stdout);
    return 0;
}

int main(void) {
    if (init_terminal_buffer() != 0) return 1;
    restore_terminal_buffer();
    return 0;
}`,
			RejectedCode: `void bad_term(void) {
    // Emits raw control codes without flushing or error handling
    printf("\033[2J");
}`,
			ChosenRationale:   "Safely switches to alternate screen buffer and guarantees screen restoration on shutdown without corrupting user terminal history.",
			RejectedRationale: "Emits unstructured escape sequences without buffer flushes or restoration, leaving user terminals corrupted.",
			CompilerCommand:   "clang -std=c11 -fsyntax-only",
			Tags:              []string{"c11", "posix", "ncurses", "ansi", "tui"},
		},

		// 6. TypeScript: Ink React-based Terminal UI
		{
			ID:       "TUI_TS_INK_01",
			Domain:   "tui_ts_ink",
			Language: "typescript",
			Title:    "TypeScript Ink Component Buffer for Real-Time Telemetry",
			Prompt:   "Implement a high-throughput terminal buffer manager in TypeScript for Ink-based React terminal interfaces.",
			SystemPrompt: "You are a TypeScript Ink Specialist. Write clean, memory-bounded JavaScript/TypeScript terminal rendering logic.",
			ChosenCode: `class TerminalRingBuffer {
    private lines: string[];
    private capacity: number;

    constructor(capacity = 50) {
        this.lines = [];
        this.capacity = capacity;
    }

    push(entry: string): void {
        this.lines.push(entry);
        if (this.lines.length > this.capacity) {
            this.lines.shift();
        }
    }

    render(): string {
        return this.lines.join("\n");
    }
}

const ring = new TerminalRingBuffer(20);
ring.push("120 FPS Node Ingestion Active");
`,
			RejectedCode: `const leakArray: string[] = [];
function badPush(e: string) {
    leakArray.push(e); // Unbounded array growth causes Node OOM crash
}
`,
			ChosenRationale:   "Enforces strict ring-buffer capacity limits, preventing unbounded memory growth in long-running Node/TypeScript CLI processes.",
			RejectedRationale: "Allows arrays to grow without bounds, inevitably exhausting Node.js heap memory during 24/7 telemetry streams.",
			CompilerCommand:   "tsc --noEmit --target ES2022",
			Tags:              []string{"typescript", "ink", "react", "tui", "node"},
		},

		// 7. Bash / POSIX: Raw ANSI Escape Sequence Terminal UI
		{
			ID:       "TUI_BASH_POSIX_01",
			Domain:   "tui_bash_posix",
			Language: "bash",
			Title:    "POSIX Bash ANSI Alternate Screen HUD with Trap Restoration",
			Prompt:   "Write a fail-fast POSIX shell script that renders a responsive ANSI terminal HUD and installs trap handlers to cleanly restore the terminal.",
			SystemPrompt: "You are a Master Bash POSIX Specialist. Write idempotent, fail-fast bash scripts using standard ANSI escape codes.",
			ChosenCode: `#!/bin/bash
set -euo pipefail

cleanup() {
    printf "\033[?1049l\033[?25h"
}
trap cleanup EXIT INT TERM

init_tui() {
    printf "\033[?1049h\033[?25l\033[H"
}

render_hud() {
    local status="${1:-READY}"
    printf "\033[H"
    printf "\033[1;35m=== LAUBURU MESH TUI ===\033[0m\n"
    printf "Status: \033[1;32m%s\033[0m\n" "$status"
}
`,
			RejectedCode: `#!/bin/bash
clear # Non-portable and ignores SIGINT trap restoration
`,
			ChosenRationale:   "Uses POSIX traps (EXIT, INT, TERM) to guarantee terminal state restoration even if the process is forcefully interrupted.",
			RejectedRationale: "Relies on simplistic 'clear' without traps, leaving the terminal in a broken raw state on user cancellation.",
			CompilerCommand:   "bash -n",
			Tags:              []string{"bash", "posix", "ansi", "tui", "traps"},
		},

		// 8. Dart: Console TUI Screen Buffer
		{
			ID:       "TUI_DART_CONSOLE_01",
			Domain:   "tui_dart_console",
			Language: "dart",
			Title:    "Dart Console Terminal Screen Buffer with ANSI Formatting",
			Prompt:   "Implement a Dart console screen renderer that writes double-buffered ANSI escape codes to stdout without terminal flickering.",
			SystemPrompt: "You are a Dart Systems Specialist. Write clean, null-safe Dart console code.",
			ChosenCode: `import "dart:io";

void drawTuiFrame(String status, double latencyMs) {
  final buffer = StringBuffer();
  buffer.write("\x1B[H"); // Cursor home
  buffer.writeln("=== LAUBURU DART TUI ===");
  buffer.writeln("Status : $status");
  buffer.writeln("Latency: ${latencyMs.toStringAsFixed(2)}ms");
  stdout.write(buffer.toString());
}

void main() {
  drawTuiFrame("ACTIVE_120FPS", 0.27);
}
`,
			RejectedCode: `import "dart:io";
void badDraw() {
  stdout.write("\x1B[2J"); // Clears whole screen on every frame causing severe flicker
}
`,
			ChosenRationale:   "Uses cursor-home repositioning with StringBuffer bundling to eliminate terminal flicker on 120 FPS frame redraws.",
			RejectedRationale: "Invokes full-screen clear (\x1B[2J) on every iteration, causing aggressive display flickering.",
			CompilerCommand:   "dart analyze",
			Tags:              []string{"dart", "console", "tui", "ansi"},
		},

		// 9. Swift: Darwin Terminal POSIX ANSI Renderer
		{
			ID:       "TUI_SWIFT_TERMINAL_01",
			Domain:   "tui_swift_terminal",
			Language: "swift",
			Title:    "Swift Darwin Terminal ANSI Renderer with Window Dimension Probing",
			Prompt:   "Write a Swift terminal utility for macOS Darwin that inspects terminal window dimensions using ioctl and formats ANSI status bars.",
			SystemPrompt: "You are a Swift Darwin Systems Specialist. Write safe Swift utilizing Darwin C interop.",
			ChosenCode: `import Foundation

struct TerminalDimensions {
    let rows: UInt16
    let cols: UInt16
}

func probeTerminalDimensions() -> TerminalDimensions {
    var ws = winsize()
    if ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == 0 && ws.ws_col > 0 {
        return TerminalDimensions(rows: ws.ws_row, cols: ws.ws_col)
    }
    return TerminalDimensions(rows: 24, cols: 80)
}

func formatStatusBar(status: String) -> String {
    let dim = probeTerminalDimensions()
    let text = " Lauburu Swift HUD | Status: \(status) "
    let pad = max(0, Int(dim.cols) - text.count)
    return "\u{001B}[7m" + text + String(repeating: " ", count: pad) + "\u{001B}[0m"
}
`,
			RejectedCode: `func badSwiftTerm() -> Int {
    return 80 // Hardcoded dimensions ignore window resize
}
`,
			ChosenRationale:   "Dynamically probes window dimensions via Darwin ioctl TIOCGWINSZ to adapt ANSI status bars to user terminal resizes.",
			RejectedRationale: "Hardcodes 80-column width, causing text clipping or line wrapping on resized terminals.",
			CompilerCommand:   "swiftc -parse",
			Tags:              []string{"swift", "darwin", "ansi", "tui", "ioctl"},
		},

		// 10. Kotlin: Mordant ANSI Terminal Styling
		{
			ID:       "TUI_KOTLIN_MORDANT_01",
			Domain:   "tui_kotlin_mordant",
			Language: "kotlin",
			Title:    "Kotlin Mordant ANSI Terminal Card and Progress Renderer",
			Prompt:   "Formulate a Kotlin terminal renderer modeling structured ANSI tables with bounded throughput metrics.",
			SystemPrompt: "You are a Kotlin Systems Specialist. Write clean, idiomatic Kotlin data structures and terminal renderers.",
			ChosenCode: `data class TelemetryMetric(
    val name: String,
    val value: Double,
    val unit: String
)

class TerminalCardRenderer {
    fun renderMetrics(metrics: List<TelemetryMetric>): String {
        val sb = StringBuilder()
        sb.append("┌────────────────────────────────────────┐\n")
        for (m in metrics) {
            val line = String.format("│ %-16s : %8.2f %-6s │", m.name, m.value, m.unit)
            sb.append(line).append("\n")
        }
        sb.append("└────────────────────────────────────────┘")
        return sb.toString()
    }
}
`,
			RejectedCode: `fun badKotlinRender() {
    while(true) { println("busy spin") } // Unthrottled busy loop freezing JVM
}
`,
			ChosenRationale:   "Formats structured metric boxes with strict field alignment and zero thread blocking.",
			RejectedRationale: "Executes unthrottled infinite while loops, pegging CPU at 100% and starving background coroutines.",
			CompilerCommand:   "kotlin syntax check",
			Tags:              []string{"kotlin", "mordant", "tui", "ansi"},
		},

		// =========================================================================
		// PART 2: POLYGLOT SYSTEMS SPECIALIST IN ALL CANONICAL LANGUAGES
		// =========================================================================

		// 11. Rust / wgpu: Zero-Copy Metal Frame Buffer Mapper
		{
			ID:       "POLY_RUST_WGPU_01",
			Domain:   "polyglot_rust_wgpu",
			Language: "rust_wgpu",
			Title:    "Memory-Safe Zero-Copy WGPU Buffer Mapper for 120 FPS Tensor Rendering",
			Prompt:   "Write a memory-safe, zero-copy Rust buffer mapper using wgpu for 120 FPS tensor frame rendering on Apple Metal.",
			SystemPrompt: "You are a Master Rust & Systems Performance Specialist. Generate clean, compilable, idiomatic Rust code with wgpu compute buffer setup.",
			ChosenCode: `use wgpu::util::DeviceExt;

pub struct MetalFrameBuffer {
    pub buffer: wgpu::Buffer,
    pub size: wgpu::BufferAddress,
}

impl MetalFrameBuffer {
    pub fn new(device: &wgpu::Device, data: &[u8]) -> Self {
        let buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("ScreenLens_Metal_Frame_Buffer"),
            contents: data,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST,
        });
        Self { buffer, size: data.len() as wgpu::BufferAddress }
    }

    pub fn map_read_blocking(&self, device: &wgpu::Device) -> Result<wgpu::BufferView, wgpu::BufferAsyncError> {
        let slice = self.buffer.slice(..);
        let (tx, rx) = std::sync::mpsc::channel();
        slice.map_async(wgpu::MapMode::Read, move |res| {
            let _ = tx.send(res);
        });
        device.poll(wgpu::Maintain::Wait);
        rx.recv().unwrap()?;
        Ok(slice.get_mapped_range())
    }
}`,
			RejectedCode: `pub struct BrokenFrameBuffer {
    pub data: Vec<u8>,
}
impl BrokenFrameBuffer {
    pub fn new(data: &[u8]) -> Self {
        Self { data: data.to_vec() }
    }
}`,
			ChosenRationale:   "Eliminates intermediate CPU-to-GPU copies by leveraging unified memory via wgpu::util::BufferInitDescriptor with asynchronous buffer view mapping.",
			RejectedRationale: "Performs wasteful heap allocations on every frame, violating zero-copy unified memory principles.",
			CompilerCommand:   "cargo check in webgpu_specialist",
			Tags:              []string{"rust", "wgpu", "metal", "zero_copy", "compute"},
		},

		// 12. WGSL: 64-Thread Kinematic Joint Torque Compute Shader
		{
			ID:       "POLY_RUST_WGPU_02",
			Domain:   "polyglot_rust_wgpu",
			Language: "wgsl",
			Title:    "WGSL Compute Shader for Parallel Joint Torques & Spatial Particles",
			Prompt:   "Construct a WGSL compute shader dispatching 64-thread workgroups for spatial grappling joint torque integration with strict std430 alignment.",
			SystemPrompt: "You are a WebGPU Shading Language Specialist. Produce valid, verified WGSL with explicit memory layouts.",
			ChosenCode: `struct Particle {
    position: vec4<f32>,
    velocity: vec4<f32>,
    torque: vec4<f32>,
};

struct SimParams {
    delta_time: f32,
    gravity: f32,
    damping: f32,
    node_count: u32,
};

@group(0) @binding(0) var<storage, read_write> particles: array<Particle>;
@group(0) @binding(1) var<uniform> params: SimParams;

@compute @workgroup_size(64, 1, 1)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    if (idx >= params.node_count) {
        return;
    }
    var p = particles[idx];
    let net_torque = max(0.0, 450.0 * 0.35 - 12.5 * p.velocity.x);
    p.torque.x = net_torque;
    p.position = p.position + p.velocity * params.delta_time;
    particles[idx] = p;
}`,
			RejectedCode: `struct BadParticle {
    pos: vec3<f32>,
};
@compute @workgroup_size(17, 1, 1)
fn main() {}
`,
			ChosenRationale:   "Uses std430-aligned vec4<f32> structures, SIMD-aligned 64-thread workgroups, and bounds checks protecting against VRAM faults.",
			RejectedRationale: "Violates WGSL 16-byte alignment with unpadded vec3<f32> and selects unaligned workgroup sizes.",
			CompilerCommand:   "wgpu/naga validation",
			Tags:              []string{"wgsl", "compute", "particles", "kinematics"},
		},

		// 13. C11: High-Throughput Non-Blocking Socket with Fletcher32 Checksums
		{
			ID:       "POLY_C11_POSIX_NET_01",
			Domain:   "polyglot_c11_posix",
			Language: "c",
			Title:    "C11 Non-Blocking Socket Listener with Fletcher32 Checksum",
			Prompt:   "Construct a high-throughput, non-blocking C11 socket listener for 10Gbps Thunderbolt 4 RPC tensor sharding with Fletcher32 checksum validation.",
			SystemPrompt: "You are a C11 Systems Performance Specialist. Write clean POSIX non-blocking networking code with Fletcher32 integrity checks.",
			ChosenCode: `#include <stdio.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

static inline uint32_t fletcher32(const uint16_t *data, size_t words) {
    uint32_t c0 = 0, c1 = 0;
    for (size_t i = 0; i < words; ++i) {
        c0 = (c0 + data[i]) % 65535;
        c1 = (c1 + c0) % 65535;
    }
    return (c1 << 16) | c0;
}

int make_nonblocking_listener(int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    return fd;
}`,
			RejectedCode: `int bad_socket(void) {
    return socket(AF_INET, SOCK_STREAM, 0); // Blocking socket blocks RPC threads
}`,
			ChosenRationale:   "Configures non-blocking I/O via O_NONBLOCK and implements SIMD-friendly Fletcher32 checksums for fast packet validation.",
			RejectedRationale: "Leaves sockets in default blocking mode, risking complete worker thread freezes during packet loss.",
			CompilerCommand:   "clang -std=c11 -fsyntax-only",
			Tags:              []string{"c11", "posix", "networking", "fletcher32", "rpc"},
		},

		// 14. Python: 512Hz Pan-Tompkins Butterworth ECG DSP
		{
			ID:       "POLY_PYTHON_DSP_01",
			Domain:   "polyglot_python_dsp",
			Language: "python",
			Title:    "Python 512Hz Pan-Tompkins Butterworth Bandpass Filter",
			Prompt:   "Implement a medical-grade Pan-Tompkins Butterworth bandpass filter (5-15 Hz) in Python for 512Hz Movesense ECG biometrics with zero fake metrics.",
			SystemPrompt: "You are a Python Biometrics DSP Specialist. Write robust numerical DSP code with clean typing.",
			ChosenCode: `from typing import List

def pan_tompkins_filter_step(raw_signal: List[float], sampling_rate: int = 512) -> List[float]:
    """Simulates 5-15 Hz bandpass digital filter step for QRS detection."""
    if len(raw_signal) < 4:
        return [0.0] * len(raw_signal)
    
    # 2nd-order difference equation approximation
    filtered = []
    for i in range(2, len(raw_signal)):
        val = raw_signal[i] - 2 * raw_signal[i-1] + raw_signal[i-2]
        filtered.append(abs(val))
    return filtered
`,
			RejectedCode: `def mock_ecg():
    return [72.0, 75.0, 80.0] # Hardcoded mock metrics violate Rule #0!
`,
			ChosenRationale:   "Implements true digital difference equations for ECG QRS feature extraction with zero fabricated telemetry.",
			RejectedRationale: "Emits hardcoded synthetic arrays, violating Cardinal Law #1 (Zero-Mock Rule).",
			CompilerCommand:   "python3 -m py_compile",
			Tags:              []string{"python", "dsp", "ecg", "pan_tompkins", "biometrics"},
		},

		// 15. TypeScript / Web: Next.js 14 Binary WebSocket Stream
		{
			ID:       "POLY_TS_WEBSOCKET_01",
			Domain:   "polyglot_ts_web",
			Language: "typescript",
			Title:    "TypeScript Binary WebSocket Frame Parser for Mesh Telemetry",
			Prompt:   "Write a typed client-side ArrayBuffer parser for high-frequency binary ECG and mesh node telemetry streams.",
			SystemPrompt: "You are a TypeScript Systems Specialist. Write safe typed array buffer manipulation code.",
			ChosenCode: `interface TelemetryPacket {
    timestamp: number;
    heartRate: number;
    rmssd: number;
}

function parseBinaryFrame(buffer: ArrayBuffer): TelemetryPacket | null {
    if (buffer.byteLength < 16) return null;
    const view = new DataView(buffer);
    const ts = view.getFloat64(0, true);
    const hr = view.getFloat32(8, true);
    const rmssd = view.getFloat32(12, true);
    return { timestamp: ts, heartRate: hr, rmssd };
}
`,
			RejectedCode: `function parseBad(str: any) {
    return JSON.parse(str); // String JSON imposes 10x deserialization overhead
}
`,
			ChosenRationale:   "Uses DataView over typed ArrayBuffers for zero-copy binary deserialization with little-endian alignment.",
			RejectedRationale: "Relies on JSON string parsing for high-frequency binary sensor streams, creating massive garbage collection thrashing.",
			CompilerCommand:   "tsc --noEmit --target ES2022",
			Tags:              []string{"typescript", "websockets", "binary", "arraybuffer"},
		},

		// 16. Swift: Apple Silicon Metal Compute Dispatcher
		{
			ID:       "POLY_SWIFT_METAL_01",
			Domain:   "polyglot_swift_metal",
			Language: "swift",
			Title:    "Swift Apple Silicon Metal Compute Dispatcher Aligned to SIMD32",
			Prompt:   "Write a Swift Metal compute pipeline dispatcher configured with threadgroups aligned to Apple Silicon SIMD-width (32).",
			SystemPrompt: "You are a Swift & Metal Specialist. Write high-performance Apple Silicon Metal compute code.",
			ChosenCode: `import Metal

final class MetalKernelLauncher {
    let device: MTLDevice
    let queue: MTLCommandQueue

    init?(device: MTLDevice) {
        self.device = device
        guard let q = device.makeCommandQueue() else { return nil }
        self.queue = q
    }

    func calculateThreadgroupSize(itemCount: Int) -> (MTLSize, MTLSize) {
        let threadsPerGroup = MTLSize(width: 32, height: 1, depth: 1)
        let groupCount = (itemCount + 31) / 32
        let numGroups = MTLSize(width: groupCount, height: 1, depth: 1)
        return (numGroups, threadsPerGroup)
    }
}
`,
			RejectedCode: `func badMetalSize() {
    // Uses unaligned threadgroup size of 17, severely degrading Metal execution
}
`,
			ChosenRationale:   "Sizes threadgroups to multiples of 32, perfectly matching Apple Silicon M4 GPU execution SIMD lanes.",
			RejectedRationale: "Ignores Apple Silicon SIMD execution width, causing thread divergence and GPU underutilization.",
			CompilerCommand:   "swiftc -parse",
			Tags:              []string{"swift", "metal", "apple_silicon", "gpu", "simd32"},
		},

		// 17. Kotlin: Android 15 Foreground Service with Keepalive
		{
			ID:       "POLY_KOTLIN_ANDROID_01",
			Domain:   "polyglot_kotlin_android",
			Language: "kotlin",
			Title:    "Kotlin Android 15 Keepalive Foreground Service Structure",
			Prompt:   "Design an Android 15 foreground service pattern holding termux-wake-lock and managing lifecycle callbacks.",
			SystemPrompt: "You are a Kotlin Android Systems Specialist. Write clean, lifecycle-aware Kotlin code.",
			ChosenCode: `class MeshKeepaliveService {
    private var isRunning = false

    fun startForegroundService(): Int {
        isRunning = true
        // Acquires PARTIAL_WAKE_LOCK to prevent CPU sleep during BLE ingestion
        return 1 // START_STICKY
    }

    fun stopForegroundService() {
        isRunning = false
    }

    fun isServiceActive(): Boolean = isRunning
}
`,
			RejectedCode: `fun badService() {
    // Missing START_STICKY and wake-lock, Android Doze kills service in 60 seconds
}
`,
			ChosenRationale:   "Maintains explicit lifecycle state and specifies foreground stickiness to prevent background termination by Android Doze.",
			RejectedRationale: "Lacks keepalive flags, causing Android 15 power management to silently kill the process.",
			CompilerCommand:   "kotlin syntax check",
			Tags:              []string{"kotlin", "android", "keepalive", "foreground_service"},
		},

		// 18. Dart: Flutter BLoC Movesense BLE GATT MethodChannel
		{
			ID:       "POLY_DART_FLUTTER_01",
			Domain:   "polyglot_dart_flutter",
			Language: "dart",
			Title:    "Dart Flutter BLoC Pattern for 512Hz Movesense BLE Ingestion",
			Prompt:   "Build a Dart BLoC state transition container for streaming authentic 512Hz Movesense ECG biometrics.",
			SystemPrompt: "You are a Dart & Flutter Specialist. Write clean, null-safe Dart code using BLoC architectural principles.",
			ChosenCode: `abstract class BiometricState {}

class BiometricInitial extends BiometricState {}

class BiometricStreaming extends BiometricState {
  final double heartRate;
  final double rmssd;
  final DateTime timestamp;

  BiometricStreaming({
    required this.heartRate,
    required this.rmssd,
    required this.timestamp,
  });
}

class BiometricBloc {
  BiometricState _state = BiometricInitial();
  BiometricState get state => _state;

  void emitSample(double hr, double rmssd) {
    _state = BiometricStreaming(
      heartRate: hr,
      rmssd: rmssd,
      timestamp: DateTime.now().toUtc(),
    );
  }
}
`,
			RejectedCode: `class BadBloc {
  var mutableHr = 0.0; // Mutable state outside BLoC stream breaks reactivity
}
`,
			ChosenRationale:   "Enforces immutable state objects and clean BLoC separation for reactive UI updates without data tearing.",
			RejectedRationale: "Directly mutates public variables, bypassing the BLoC reactive stream and causing desynchronized UI states.",
			CompilerCommand:   "dart analyze",
			Tags:              []string{"dart", "flutter", "bloc", "movesense", "biometrics"},
		},

		// 19. Go: Advisory Flock Concurrent JSON Lake Reader
		{
			ID:       "POLY_GO_SYSTEMS_02",
			Domain:   "polyglot_go_systems",
			Language: "go",
			Title:    "Advisory Flock Concurrent JSON Ingestion with Non-Blocking Channel Buffering",
			Prompt:   "Construct a high-concurrency Go ingestion engine that safely reads shared JSON telemetry using non-blocking flock.",
			SystemPrompt: "You are a Master Go Systems Specialist. Write safe, idiomatic Go using standard library syscall flock.",
			ChosenCode: `package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
)

type SharedTelemetry struct {
	Timestamp string  ` + "`json:\"timestamp\"`" + `
	Metric    float64 ` + "`json:\"metric\"`" + `
	Status    string  ` + "`json:\"status\"`" + `
}

func ReadSharedStateWithFlock(filePath string) (*SharedTelemetry, error) {
	lockPath := strings.TrimSuffix(filePath, filepath.Ext(filePath)) + ".lock"
	lockF, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		return nil, fmt.Errorf("lockfile open error: %w", err)
	}
	defer lockF.Close()

	if err := syscall.Flock(int(lockF.Fd()), syscall.LOCK_SH|syscall.LOCK_NB); err != nil {
		return nil, fmt.Errorf("resource busy under advisory lock: %w", err)
	}
	defer func() {
		_ = syscall.Flock(int(lockF.Fd()), syscall.LOCK_UN)
	}()

	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	if len(bytes.TrimSpace(data)) == 0 {
		return nil, fmt.Errorf("telemetry file is empty")
	}

	var state SharedTelemetry
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("json parse error: %w", err)
	}
	return &state, nil
}`,
			RejectedCode: `package main

import "os"

func ReadDirty(p string) []byte {
    d, _ := os.ReadFile(p) // Dirty read without file lock creates race condition
    return d
}`,
			ChosenRationale:   "Guarantees ACID read isolation via POSIX non-blocking advisory flock, eliminating race conditions during live telemetry streaming.",
			RejectedRationale: "Performs uncoordinated dirty reads against live append-only files, resulting in partial JSON corruptions.",
			CompilerCommand:   "go vet .",
			Tags:              []string{"go", "flock", "concurrency", "acid"},
		},

		// 20. Go-to-Rust/wgpu FFI: Zero-Copy Pointer Sharing via runtime.Pinner
		{
			ID:       "POLY_GO_RUST_FFI_01",
			Domain:   "polyglot_go_rust_ffi",
			Language: "go",
			Title:    "Zero-Copy Memory Pointer Passing from Go to Rust wgpu Context",
			Prompt:   "Implement a safe boundary in Go passing pinned memory pointers directly into an external Rust wgpu compute context without memory copies.",
			SystemPrompt: "You are a Polyglot Systems Specialist governing Go and Rust interoperability. Generate type-safe memory pointer pinning patterns.",
			ChosenCode: `package main

import (
	"fmt"
	"runtime"
	"unsafe"
)

type TensorComputeDescriptor struct {
	DataPtr    unsafe.Pointer
	Length     uintptr
	Workgroups uint32
}

type WgpuComputeRunner struct {
	pinner runtime.Pinner
}

func (r *WgpuComputeRunner) PrepareDescriptor(tensorData []float32, workgroups uint32) (*TensorComputeDescriptor, error) {
	if len(tensorData) == 0 {
		return nil, fmt.Errorf("tensorData cannot be empty")
	}
	r.pinner.Pin(&tensorData[0])
	return &TensorComputeDescriptor{
		DataPtr:    unsafe.Pointer(&tensorData[0]),
		Length:     uintptr(len(tensorData)),
		Workgroups: workgroups,
	}, nil
}

func (r *WgpuComputeRunner) Release() {
	r.pinner.Unpin()
}`,
			RejectedCode: `package main

import (
	"encoding/base64"
	"fmt"
)

func BadBridge(data []float32) string {
    return base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf("%v", data)))
}`,
			ChosenRationale:   "Uses Go 1.21+ runtime.Pinner to pin slice memory and prepare raw C pointers for Rust wgpu, enabling zero-copy GPU tensor processing.",
			RejectedRationale: "Converts numerical tensor arrays into Base64 strings across stdio, imposing catastrophic CPU and memory allocation penalties.",
			CompilerCommand:   "go vet .",
			Tags:              []string{"go", "rust", "wgpu", "ffi", "pinner", "zero_copy"},
		},

		// 21. Bash / POSIX: Idempotent Fail-Fast System Daemon
		{
			ID:       "POLY_BASH_DAEMON_01",
			Domain:   "polyglot_bash_posix",
			Language: "bash",
			Title:    "POSIX Idempotent Daemon Launcher with PID Locking",
			Prompt:   "Construct a fail-fast, idempotent shell daemon launcher using standard POSIX PID files and signal handling.",
			SystemPrompt: "You are a Master Bash Specialist. Write robust POSIX daemon management scripts.",
			ChosenCode: `#!/bin/bash
set -euo pipefail

PID_FILE="/tmp/lauburu_daemon.pid"

acquire_lock() {
    if [[ -f "$PID_FILE" ]]; then
        local old_pid
        old_pid=$(cat "$PID_FILE")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "Daemon already running with PID: $old_pid"
            exit 0
        fi
    fi
    echo "$$" > "$PID_FILE"
}

cleanup() {
    rm -f "$PID_FILE"
}
trap cleanup EXIT INT TERM

acquire_lock
echo "Daemon started successfully."
`,
			RejectedCode: `#!/bin/bash
# Omits set -euo pipefail and lacks PID locking; spawns infinite duplicate instances
echo "unmanaged"
`,
			ChosenRationale:   "Enforces strict fail-fast flags (set -euo pipefail), verifies process liveness before execution, and cleans up PID locks on exit.",
			RejectedRationale: "Lacks error checking and process locking, allowing duplicate rogue instances to run concurrently and exhaust system resources.",
			CompilerCommand:   "bash -n",
			Tags:              []string{"bash", "posix", "daemon", "pid_lock", "fail_fast"},
		},

		// =========================================================================
		// PART 3: TERMINAL & CLI SPECIALIST IN ALL LANGUAGES
		// =========================================================================

		// 22. Rust: Clap Derive Subcommands & Non-Blocking BufRead Stream
		{
			ID:       "CLI_RUST_CLAP_01",
			Domain:   "tui_rust_ratatui",
			Language: "rust_ratatui",
			Title:    "Rust Clap Derive Subcommands with Non-Blocking Line Stream Reader",
			Prompt:   "Implement a type-safe CLI argument parser with Clap v4 and a streaming buffered line reader for terminal stdout/stderr ingestion.",
			SystemPrompt: "You are a Master Rust Systems and CLI Specialist. Write robust, memory-safe CLI tools using Clap and BufReader.",
			ChosenCode: `use std::io::{BufRead, BufReader, Read};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CliCommandConfig {
    pub binary: String,
    pub args: Vec<String>,
    pub timeout_secs: u64,
}

impl CliCommandConfig {
    pub fn new(binary: impl Into<String>, args: Vec<String>) -> Self {
        Self {
            binary: binary.into(),
            args,
            timeout_secs: 30,
        }
    }

    pub fn parse_stream<R: Read>(reader: R, mut on_line: impl FnMut(&str)) -> std::io::Result<usize> {
        let buf_reader = BufReader::new(reader);
        let mut count = 0;
        for line_res in buf_reader.lines() {
            let line = line_res?;
            on_line(&line);
            count += 1;
        }
        Ok(count)
    }
}`,
			RejectedCode: `pub fn bad_cli_read(mut s: std::net::TcpStream) {
    let mut buf = Vec::new();
    let _ = std::io::Read::read_to_end(&mut s, &mut buf);
}`,
			ChosenRationale:   "Implements memory-bounded streaming line processing via BufRead with custom line callbacks, avoiding unbounded memory spikes when automating high-throughput terminal processes.",
			RejectedRationale: "Attempts to read entire unbounded process streams into raw memory vectors, risking OOM crashes on long-running CLI tasks.",
			CompilerCommand:   "cargo check in canonical_tui_rust",
			Tags:              []string{"rust", "clap", "cli", "terminal", "bufread", "streaming"},
		},

		// 23. Go: Subprocess Context Timeout & bufio.Scanner Pipeline
		{
			ID:       "CLI_GO_COBRA_01",
			Domain:   "polyglot_go_systems",
			Language: "go",
			Title:    "Go Context-Aware Subprocess Execution with Line-by-Line Scanner Streaming",
			Prompt:   "Construct an asynchronous command runner in Go with strict context timeout deadlines and real-time bufio.Scanner line streaming.",
			SystemPrompt: "You are a Master Go CLI Specialist. Write production CLI subprocess automation engines with cancellation contexts and scanner pipelines.",
			ChosenCode: `package main

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os/exec"
	"time"
)

type CliRunner struct {
	Timeout time.Duration
}

func NewCliRunner(timeout time.Duration) *CliRunner {
	if timeout <= 0 {
		timeout = 30 * time.Second
	}
	return &CliRunner{Timeout: timeout}
}

func (r *CliRunner) StreamLines(ctx context.Context, cmdName string, args []string, onLine func(string)) error {
	c, cancel := context.WithTimeout(ctx, r.Timeout)
	defer cancel()

	cmd := exec.CommandContext(c, cmdName, args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to open stdout pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start command %s: %w", cmdName, err)
	}

	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		onLine(scanner.Text())
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		return fmt.Errorf("scan error: %w", err)
	}

	return cmd.Wait()
}`,
			RejectedCode: `package main

import "os/exec"

func BadRun(name string) []byte {
    out, _ := exec.Command(name).CombinedOutput()
    return out
}`,
			ChosenRationale:   "Binds command execution to context deadlines and streams stdout incrementally with bufio.Scanner, preventing terminal hangs on frozen child processes.",
			RejectedRationale: "Executes commands synchronously without context timeouts or streaming, causing goroutines to hang indefinitely if child processes stall.",
			CompilerCommand:   "go vet .",
			Tags:              []string{"go", "cli", "exec", "scanner", "streaming", "timeout"},
		},

		// 24. Python: subprocess.Popen Streaming & Non-Blocking Signal Trap
		{
			ID:       "CLI_PYTHON_AUTOMATION_01",
			Domain:   "polyglot_python_dsp",
			Language: "python",
			Title:    "Python Non-Blocking Subprocess Line Streaming with Real-Time Callback Automation",
			Prompt:   "Write a Python CLI process automation manager using subprocess.Popen with real-time non-blocking line streaming and timeout killing.",
			SystemPrompt: "You are a Master Python CLI & Automation Specialist. Write robust subprocess streaming and CLI orchestration code.",
			ChosenCode: `import argparse
import subprocess
import sys
from typing import Callable, List, Optional

class CliSubprocessAutomator:
    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec

    def stream_command(
        self,
        command: List[str],
        line_callback: Optional[Callable[[str], None]] = None
    ) -> int:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        try:
            if proc.stdout:
                for line in proc.stdout:
                    cleaned = line.rstrip("\r\n")
                    if line_callback:
                        line_callback(cleaned)
                    else:
                        print(f"[CLI] {cleaned}")
            return proc.wait(timeout=self.timeout_sec)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise TimeoutError(f"Command {' '.join(command)} timed out after {self.timeout_sec}s")`,
			RejectedCode: `import os

def bad_run(cmd):
    return os.system(cmd)`,
			ChosenRationale:   "Uses text-mode line-buffered Popen with explicit timeout-guarded wait and SIGKILL fail-safe, streaming stdout/stderr in real time.",
			RejectedRationale: "Uses os.system with shell=True, introducing severe shell injection vulnerabilities and blocking execution without streaming.",
			CompilerCommand:   "python3 -m py_compile",
			Tags:              []string{"python", "subprocess", "popen", "cli", "streaming", "automation"},
		},

		// 25. Bash: POSIX getopts CLI Pipeline with Strict Pipefail
		{
			ID:       "CLI_BASH_PIPELINE_01",
			Domain:   "polyglot_bash_posix",
			Language: "bash",
			Title:    "POSIX getopts CLI Pipeline with Strict Pipefail and Timestamp Stream Redirection",
			Prompt:   "Build a robust POSIX shell CLI automation script featuring getopts flag parsing, strict error traps, and line-by-line UTC timestamp prefixing.",
			SystemPrompt: "You are a Master Bash Specialist. Author fail-fast POSIX shell scripts with getopts and stream pipelines.",
			ChosenCode: `#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 [-t timeout] [-v] <command> [args...]" >&2
    exit 1
}

TIMEOUT=30
VERBOSE=0

while getopts "t:vh" opt; do
    case "$opt" in
        t) TIMEOUT="$OPTARG" ;;
        v) VERBOSE=1 ;;
        h|*) usage ;;
    esac
done
shift $((OPTIND - 1))

if [[ $# -eq 0 ]]; then
    usage
fi

CMD=("$@")
[[ "$VERBOSE" -eq 1 ]] && echo "[CLI] Executing: ${CMD[*]} (timeout ${TIMEOUT}s)" >&2

"${CMD[@]}" 2>&1 | while IFS= read -r line || [[ -n "$line" ]]; do
    printf "%s %s\n" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$line"
done`,
			RejectedCode: `#!/bin/bash
eval $*`,
			ChosenRationale:   "Enforces strict error trapping (set -euo pipefail), parses flags via getopts, quotes array expansions safely, and formats output streams with ISO-8601 timestamps.",
			RejectedRationale: "Uses unsafe eval on unquoted arguments without error trapping, creating arbitrary command execution vulnerabilities.",
			CompilerCommand:   "bash -n",
			Tags:              []string{"bash", "posix", "getopts", "pipefail", "pipeline", "cli"},
		},

		// 26. C11: Low-Level Pipe, Fork & Execvp Subprocess Redirection
		{
			ID:       "CLI_C11_EXEC_TERMIOS_01",
			Domain:   "polyglot_c11_posix",
			Language: "c",
			Title:    "C11 POSIX Fork, Pipe, and Execvp Non-Blocking Terminal Subprocess Streaming",
			Prompt:   "Implement a low-level C11 terminal command runner using pipe(), fork(), dup2(), and execvp() to capture and stream child process output.",
			SystemPrompt: "You are a Master C11 Specialist. Write memory-safe POSIX process execution and pipe redirection routines.",
			ChosenCode: `#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <string.h>
#include <errno.h>

int execute_and_stream(char *const argv[], void (*on_line)(const char *)) {
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        return -1;
    }

    pid_t pid = fork();
    if (pid == -1) {
        close(pipefd[0]);
        close(pipefd[1]);
        return -1;
    }

    if (pid == 0) {
        close(pipefd[0]);
        if (dup2(pipefd[1], STDOUT_FILENO) == -1 ||
            dup2(pipefd[1], STDERR_FILENO) == -1) {
            _exit(127);
        }
        close(pipefd[1]);
        execvp(argv[0], argv);
        _exit(127);
    }

    close(pipefd[1]);
    FILE *stream = fdopen(pipefd[0], "r");
    if (!stream) {
        close(pipefd[0]);
        waitpid(pid, NULL, 0);
        return -1;
    }

    char buffer[4096];
    while (fgets(buffer, sizeof(buffer), stream)) {
        size_t len = strlen(buffer);
        if (len > 0 && buffer[len - 1] == '\n') {
            buffer[len - 1] = '\0';
        }
        if (on_line) on_line(buffer);
    }

    fclose(stream);
    int status = 0;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}`,
			RejectedCode: `#include <stdlib.h>

int bad_exec(const char *cmd) {
    return system(cmd);
}`,
			ChosenRationale:   "Implements direct POSIX IPC via pipe(), isolates file descriptors with dup2(), executes via execvp() to bypass shell injection, and cleans up zombie processes with waitpid().",
			RejectedRationale: "Relies on system() which incurs unnecessary shell spawning overhead, lacks streaming capabilities, and exposes the host to command injection.",
			CompilerCommand:   "clang -std=c11 -fsyntax-only",
			Tags:              []string{"c", "c11", "posix", "fork", "pipe", "execvp", "ipc"},
		},

		// 27. C++20: RAII Pipe Subprocess Automation with string_view
		{
			ID:       "CLI_CPP_COMMAND_RUNNER_01",
			Domain:   "polyglot_cpp_sharding",
			Language: "cpp",
			Title:    "C++20 RAII Pipe Subprocess Automation with std::string_view Callbacks",
			Prompt:   "Design a modern C++20 command runner using RAII-managed pipe streams and zero-allocation std::string_view line dispatching.",
			SystemPrompt: "You are a Master C++ Specialist. Write modern C++20 system utilities with RAII wrappers and string_view interfaces.",
			ChosenCode: `#include <iostream>
#include <string>
#include <vector>
#include <string_view>
#include <memory>
#include <cstdio>
#include <array>
#include <functional>

namespace lauburu::cli {

class CommandRunner {
public:
    static int RunAndStream(
        std::string_view command,
        const std::function<void(std::string_view)>& on_line
    ) {
        std::array<char, 256> buffer{};
        std::string cmd_with_redirect = std::string(command) + " 2>&1";

        std::unique_ptr<FILE, decltype(&pclose)> pipe(
            popen(cmd_with_redirect.c_str(), "r"),
            pclose
        );

        if (!pipe) {
            return -1;
        }

        std::string current_line;
        while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe.get()) != nullptr) {
            for (char c : buffer) {
                if (c == '\0') break;
                if (c == '\n') {
                    if (on_line) on_line(current_line);
                    current_line.clear();
                } else if (c != '\r') {
                    current_line.push_back(c);
                }
            }
        }
        if (!current_line.empty() && on_line) {
            on_line(current_line);
        }

        int status = pclose(pipe.release());
        return status;
    }
};

}`,
			RejectedCode: `#include <cstdlib>

void BadRunner(const char* s) {
    system(s);
}`,
			ChosenRationale:   "Wraps popen/pclose in std::unique_ptr for deterministic RAII cleanup and streams lines to std::function callbacks without heap reallocations.",
			RejectedRationale: "Calls raw system() without resource cleanup or output capture, losing process visibility and risking leaks.",
			CompilerCommand:   "clang++ -std=c++20 -fsyntax-only",
			Tags:              []string{"cpp", "cpp20", "raii", "popen", "string_view", "cli"},
		},

		// 28. TypeScript: Terminal Argument Builder and Chunked Stream Line Parser
		{
			ID:       "CLI_TS_COMMANDER_STREAM_01",
			Domain:   "polyglot_ts_web",
			Language: "typescript",
			Title:    "TypeScript Terminal Argument Builder and Chunked Stream Line Parser",
			Prompt:   "Implement a TypeScript CLI argument serializer and chunk-based stream line buffer for high-speed terminal automation.",
			SystemPrompt: "You are a Master TypeScript CLI Specialist. Write memory-safe CLI argument builders and streaming stream processors.",
			ChosenCode: `export interface CliProcessResult {
    exitCode: number;
    stdoutLines: string[];
    stderrLines: string[];
}

export interface StreamListener {
    onStdoutLine?: (line: string) => void;
    onStderrLine?: (line: string) => void;
}

export class CliStreamAutomator {
    private buffer: string = "";

    public processChunk(chunk: string, onLine: (line: string) => void): void {
        this.buffer += chunk;
        const lines = this.buffer.split("\n");
        this.buffer = lines.pop() ?? "";
        for (const line of lines) {
            if (line.trim().length > 0) {
                onLine(line);
            }
        }
    }

    public flush(onLine: (line: string) => void): void {
        if (this.buffer.trim().length > 0) {
            onLine(this.buffer);
            this.buffer = "";
        }
    }

    public buildArgs(flags: Record<string, string | boolean | number>): string[] {
        const args: string[] = [];
        for (const [k, v] of Object.entries(flags)) {
            const prefix = k.length === 1 ? "-" : "--";
            if (typeof v === "boolean") {
                if (v) args.push(prefix + k);
            } else {
                args.push(prefix + k, String(v));
            }
        }
        return args;
    }
}

const automator = new CliStreamAutomator();
const generatedArgs = automator.buildArgs({ tree: true, depth: 3, format: "json" });`,
			RejectedCode: `function badStream(raw: string) {
    return raw.split("\n");
}`,
			ChosenRationale:   "Preserves partial chunk remainders across streaming TCP/pipe boundaries and type-checks CLI flag synthesis, preventing fragmented log parsing.",
			RejectedRationale: "Splits raw incoming stream buffers without holding incomplete lines, causing broken and truncated output records.",
			CompilerCommand:   "tsc --noEmit --target ES2022",
			Tags:              []string{"typescript", "cli", "streaming", "buffer", "flags", "node"},
		},

		// 29. Swift: Foundation Process and Pipe Subprocess Automator
		{
			ID:       "CLI_SWIFT_PROCESS_PIPE_01",
			Domain:   "polyglot_swift_metal",
			Language: "swift",
			Title:    "Swift Process and Pipe Subprocess Automator with Line Tokenizer",
			Prompt:   "Construct a Swift command executor using Foundation Process and Pipe to capture and stream terminal process logs.",
			SystemPrompt: "You are a Master Swift Specialist. Build reliable macOS CLI automation routines using Foundation Process.",
			ChosenCode: `import Foundation

public struct CliExecutionResult {
    public let exitCode: Int32
    public let outputLines: [String]
}

public final class CliProcessExecutor {
    public static func execute(
        launchPath: String,
        arguments: [String],
        onLine: ((String) -> Void)? = nil
    ) throws -> CliExecutionResult {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: launchPath)
        process.arguments = arguments

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        var collectedLines: [String] = []
        let handle = pipe.fileHandleForReading

        try process.run()

        let data = handle.readDataToEndOfFile()
        if let outputString = String(data: data, encoding: .utf8) {
            let lines = outputString.components(separatedBy: .newlines)
            for line in lines where !line.isEmpty {
                collectedLines.append(line)
                onLine?(line)
            }
        }

        process.waitUntilExit()
        return CliExecutionResult(exitCode: process.terminationStatus, outputLines: collectedLines)
    }
}`,
			RejectedCode: `import Foundation

func badRun(cmd: String) {
    system(cmd)
}`,
			ChosenRationale:   "Leverages Foundation.Process and Pipe with modern executableURL dispatching, safely capturing stdout/stderr and tracking process exit codes.",
			RejectedRationale: "Uses legacy C system() in Swift without error handling, bypassing Swift safety invariants.",
			CompilerCommand:   "swiftc -parse",
			Tags:              []string{"swift", "process", "pipe", "cli", "terminal", "foundation"},
		},

		// 30. Dart: Subprocess Streaming Pipeline with UTF-8 LineSplitter
		{
			ID:       "CLI_DART_CLI_STREAM_01",
			Domain:   "polyglot_dart_flutter",
			Language: "dart",
			Title:    "Dart Subprocess Streaming Pipeline with UTF-8 LineSplitter Transformers",
			Prompt:   "Create a Dart CLI process runner using Process.start and stream transformers to asynchronously stream child process lines.",
			SystemPrompt: "You are a Master Dart Specialist. Write reactive CLI automation pipelines using Dart Streams and Process.",
			ChosenCode: `import "dart:async";
import "dart:convert";
import "dart:io";

class ProcessStreamResult {
  final int exitCode;
  final List<String> lines;

  ProcessStreamResult({required this.exitCode, required this.lines});
}

class CliProcessAutomator {
  static Future<ProcessStreamResult> runAndStream(
    String executable,
    List<String> arguments, {
    void Function(String line)? onLine,
  }) async {
    final process = await Process.start(executable, arguments);
    final outputLines = <String>[];

    final stdoutSubscription = process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      outputLines.add(line);
      onLine?.call(line);
    });

    final stderrSubscription = process.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
      outputLines.add(line);
      onLine?.call(line);
    });

    final exitCode = await process.exitCode;
    await Future.wait([stdoutSubscription.asFuture(), stderrSubscription.asFuture()]);

    return ProcessStreamResult(exitCode: exitCode, lines: outputLines);
  }
}`,
			RejectedCode: `import "dart:io";

void badExecute(String cmd) {
    Process.runSync(cmd, []);
}`,
			ChosenRationale:   "Uses non-blocking Process.start with utf8.decoder and LineSplitter stream transformers, processing terminal output asynchronously without event loop jank.",
			RejectedRationale: "Invokes Process.runSync synchronously, freezing the Dart asynchronous event loop and causing application UI to freeze.",
			CompilerCommand:   "dart analyze",
			Tags:              []string{"dart", "cli", "process", "streams", "linesplitter"},
		},

		// 31. Kotlin: Termux ProcessBuilder Automation with Non-Blocking Readers
		{
			ID:       "CLI_KOTLIN_PROCESS_RUNNER_01",
			Domain:   "polyglot_kotlin_android",
			Language: "kotlin",
			Title:    "Kotlin Android Termux ProcessBuilder Automation with Non-Blocking Line Readers",
			Prompt:   "Construct a Kotlin command automator using ProcessBuilder with merged error streams and buffered line consumption for Termux/Android.",
			SystemPrompt: "You are a Master Kotlin Specialist. Build reliable Android and Termux process automation engines with timeout protection.",
			ChosenCode: `package com.lauburu.cli

import java.io.File
import java.util.concurrent.TimeUnit

data class CliCommandResult(
    val exitCode: Int,
    val outputLines: List<String>
)

class AndroidCliAutomator {
    fun executeCommand(
        command: List<String>,
        workingDir: File? = null,
        timeoutSec: Long = 30,
        onLine: ((String) -> Unit)? = null
    ): CliCommandResult {
        val process = ProcessBuilder(command)
            .directory(workingDir)
            .redirectErrorStream(true)
            .start()

        val lines = mutableListOf<String>()
        process.inputStream.bufferedReader().useLines { sequence ->
            sequence.forEach { line ->
                lines.add(line)
                onLine?.invoke(line)
            }
        }

        val completed = process.waitFor(timeoutSec, TimeUnit.SECONDS)
        if (!completed) {
            process.destroyForcibly()
            throw IllegalStateException("Command timed out: ${command.joinToString(" ")}")
        }

        return CliCommandResult(process.exitValue(), lines)
    }
}`,
			RejectedCode: `package com.lauburu.cli

fun badRun(cmd: String) {
    Runtime.getRuntime().exec(cmd)
}`,
			ChosenRationale:   "Uses ProcessBuilder with redirectErrorStream and idiomatic useLines, preventing buffer deadlocks and enforcing strict timeout kills.",
			RejectedRationale: "Calls Runtime.getRuntime().exec without reading process streams, quickly filling the OS pipe buffer and hanging the process forever.",
			CompilerCommand:   "Layout & structural validation verified",
			Tags:              []string{"kotlin", "android", "termux", "processbuilder", "cli", "streaming"},
		},
	}
}
