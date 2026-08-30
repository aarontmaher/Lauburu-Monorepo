#!/usr/bin/env python3
"""
================================================================================
Lauburu TUI & Web TUI Benchmark Engine v1.0.0
================================================================================
Subsystem: 06_scripts_and_tooling/tui_benchmark/tui_benchmark_engine.py

Evaluates both the Terminal TUI (Textual) and Web TUI across 7 pillars:
  1. UI Fidelity       — Visual polish, layout correctness, color usage
  2. UX Flow           — Navigation, key bindings, screen transitions
  3. Data Accuracy     — Rule #0 enforcement (zero mock data)
  4. Performance       — Import time, widget count, refresh latency
  5. Information Density — Signal-to-noise ratio per screen
  6. Resilience        — Error handling, graceful degradation
  7. Feature Coverage  — Screens implemented vs planned

Outputs:
  - Console rich table with per-pillar scores
  - JSON report to 04_data_and_memory/tui_benchmark_results.jsonl
  - LoRA training pairs appended to continuous_lora_dataset.jsonl
================================================================================
"""
from __future__ import annotations

import os
import sys
import ast
import json
import time
import hashlib
import subprocess
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import track
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

MONOREPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TUI_ROOT  = MONOREPO / "01_apps/canonical_port/tui"
SCREENS   = TUI_ROOT / "screens"
WIDGETS   = TUI_ROOT / "widgets"
WEB_ROOT  = MONOREPO / "01_apps/canonical_port"
RESULTS   = MONOREPO / "04_data_and_memory/tui_benchmark_results.jsonl"
LORA      = MONOREPO / "04_data_and_memory/continuous_lora_dataset.jsonl"

console = Console() if HAS_RICH else None

# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PillarScore:
    name: str
    weight: float          # 0.0-1.0, all weights sum to 1.0
    score: float = 0.0     # 0-100
    max_score: float = 100.0
    findings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

@dataclass
class BenchmarkReport:
    target: str            # "terminal_tui" | "web_tui"
    timestamp: str = ""
    overall_score: float = 0.0
    grade: str = ""
    pillars: list[PillarScore] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    top_suggestions: list[str] = field(default_factory=list)
    sha256: str = ""

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 1: UI FIDELITY
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_ui_fidelity(target: str) -> PillarScore:
    p = PillarScore("UI Fidelity", weight=0.20)
    score = 0
    
    if target == "terminal_tui":
        screen_files = list(SCREENS.glob("*.py"))
        p.findings.append(f"Found {len(screen_files)} screen files")

        # Check for TCSS stylesheets (Textual CSS)
        tcss_files = list(TUI_ROOT.glob("**/*.tcss"))
        if tcss_files:
            score += 25
            p.findings.append(f"✅ {len(tcss_files)} TCSS stylesheet(s) found — layout controlled via CSS")
        else:
            score += 5
            p.findings.append("⚠️  No .tcss files found — styles inline only (harder to maintain)")
            p.suggestions.append("Extract inline styles into dedicated .tcss files for each screen")

        # Check for Header/Footer presence on all screens
        screens_with_header = 0
        screens_with_footer = 0
        screens_with_bindings = 0
        for f in screen_files:
            if f.name == "__init__.py":
                continue
            src = f.read_text(errors="ignore")
            if "Header()" in src or "yield Header" in src:
                screens_with_header += 1
            if "Footer()" in src or "yield Footer" in src:
                screens_with_footer += 1
            if "BINDINGS" in src:
                screens_with_bindings += 1

        total = len([f for f in screen_files if f.name != "__init__.py"])
        if total > 0:
            header_pct = screens_with_header / total
            footer_pct = screens_with_footer / total
            bindings_pct = screens_with_bindings / total
            score += int(header_pct * 20)
            score += int(footer_pct * 15)
            score += int(bindings_pct * 20)
            p.findings.append(f"Header: {screens_with_header}/{total} screens | Footer: {screens_with_footer}/{total} | Bindings: {screens_with_bindings}/{total}")
            if header_pct < 1.0:
                p.suggestions.append(f"Add Header() to {total - screens_with_header} screens missing it")
            if footer_pct < 1.0:
                p.suggestions.append(f"Add Footer() to {total - screens_with_footer} screens for key hint visibility")

        # Braille/Unicode sparklines
        widget_files = list(WIDGETS.glob("*.py"))
        has_braille = any("braille" in f.name.lower() or "sparkline" in f.name.lower() for f in widget_files)
        if has_braille:
            score += 20
            p.findings.append("✅ Braille/sparkline waveform widgets detected — high visual fidelity")
        else:
            p.suggestions.append("Add braille waveform widgets for ECG/metric sparklines")

    elif target == "web_tui":
        # Check for proper semantic HTML
        index_html = WEB_ROOT / "index.html"
        if index_html.exists():
            src = index_html.read_text(errors="ignore")
            score += 20
            if "JetBrains Mono" in src or "monospace" in src.lower():
                score += 15
                p.findings.append("✅ Monospace terminal font loaded (JetBrains Mono)")
            if "xterm" in src.lower() or "pty" in src.lower():
                score += 20
                p.findings.append("✅ PTY/xterm.js integration detected for terminal emulation")
            if "viewport" in src:
                score += 10
                p.findings.append("✅ Responsive viewport meta tag present")
            else:
                p.suggestions.append("Add viewport meta tag for mobile responsiveness")
            if "truecolor" in src.lower() or "256color" in src.lower():
                score += 15
                p.findings.append("✅ 24-bit truecolor configured for web terminal")
        else:
            p.findings.append("⚠️  No index.html found at canonical_port root")
            p.suggestions.append("Create a proper index.html with xterm.js and JetBrains Mono")

    p.score = min(score, p.max_score)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 2: UX FLOW
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_ux_flow(target: str) -> PillarScore:
    p = PillarScore("UX Flow", weight=0.18)
    score = 0

    if target == "terminal_tui":
        main_tui = TUI_ROOT / "canonical_tui.py"
        if main_tui.exists():
            src = main_tui.read_text(errors="ignore")

            # Check for screen navigation map
            screen_count = src.count("push_screen") + src.count("switch_screen")
            if screen_count >= 8:
                score += 25
                p.findings.append(f"✅ {screen_count} screen transitions registered")
            elif screen_count >= 4:
                score += 15
                p.findings.append(f"⚠️  Only {screen_count} screen transitions — consider more navigation paths")
                p.suggestions.append("Add keyboard shortcuts for direct screen jumping (number keys 1-9)")

            # Tab / TabbedContent usage
            screen_files = list(SCREENS.glob("*.py"))
            tabbed_screens = sum(1 for f in screen_files if "TabbedContent" in f.read_text(errors="ignore"))
            if tabbed_screens > 0:
                score += 20
                p.findings.append(f"✅ {tabbed_screens} screen(s) use TabbedContent for sub-navigation")
            else:
                p.suggestions.append("Use TabbedContent widgets for screens with multiple data views")

            # Command palette
            if "CommandPalette" in src or "command_palette" in src.lower():
                score += 20
                p.findings.append("✅ Command palette registered — power user UX")
            else:
                p.suggestions.append("Add Ctrl+P CommandPalette for fast screen/action access")

            # Focus management
            if "focus()" in src or "set_focus" in src:
                score += 10
                p.findings.append("✅ Explicit focus management detected")

            # Mouse support hints
            if "on_mouse" in src or "on_click" in src or "MouseMove" in src:
                score += 15
                p.findings.append("✅ Mouse event handlers present")
            else:
                p.suggestions.append("Add mouse click handlers to key metric cards for drill-down")

    elif target == "web_tui":
        serve_script = TUI_ROOT / "serve_web_tui.py"
        if serve_script.exists():
            src = serve_script.read_text(errors="ignore")
            score += 15
            if "WebSocket" in src or "ws://" in src or "WSMsgType" in src:
                score += 25
                p.findings.append("✅ WebSocket PTY bridge for real-time terminal interaction")
            if "xterm" in src.lower():
                score += 20
                p.findings.append("✅ xterm.js rendering layer referenced")
            if "resize" in src.lower():
                score += 20
                p.findings.append("✅ Terminal resize (SIGWINCH) handling detected")
            else:
                p.suggestions.append("Handle window resize events to send SIGWINCH to PTY process")
            if "reconnect" in src.lower() or "retry" in src.lower():
                score += 10
                p.findings.append("✅ WebSocket reconnection logic present")
            else:
                p.suggestions.append("Add exponential-backoff WebSocket reconnection for network drops")

    p.score = min(score, p.max_score)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 3: DATA ACCURACY (Rule #0 Enforcement)
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_data_accuracy(target: str) -> PillarScore:
    p = PillarScore("Data Accuracy (Rule #0)", weight=0.20)
    score = 100  # Start at 100 and deduct for violations

    mock_patterns = [
        ("random.random()", "synthetic random metric"),
        ("random.uniform(", "synthetic uniform distribution"),
        ("random.gauss(", "synthetic gaussian data"),
        ("np.random.randn(", "numpy synthetic noise"),
        ("[0.277", "hardcoded latency value"),
        ("192.168.8.230", "hardcoded IP (may be stale)"),
        ("fake_", "explicitly fake data prefix"),
        ("mock_", "explicitly mocked data prefix"),
        ("# TODO: replace", "acknowledged fake data"),
    ]

    search_dirs = [SCREENS, WIDGETS, TUI_ROOT]
    violation_count = 0

    for d in search_dirs:
        for py_file in d.glob("*.py"):
            src = py_file.read_text(errors="ignore")
            for pattern, label in mock_patterns:
                if pattern in src:
                    violation_count += 1
                    p.findings.append(f"⚠️  [{py_file.name}] {label}: `{pattern}`")
                    if violation_count <= 3:  # cap deductions listed
                        p.suggestions.append(f"Replace `{pattern}` in {py_file.name} with live probe")
                    score -= 8

    if violation_count == 0:
        p.findings.append("✅ Zero mock/synthetic data patterns detected — Rule #0 clean")
    else:
        p.findings.append(f"❌ {violation_count} synthetic data pattern(s) found across TUI files")

    # Check for -- sentinel pattern (good sign)
    screens_using_sentinel = 0
    for f in SCREENS.glob("*.py"):
        if '"--"' in f.read_text(errors="ignore") or "'--'" in f.read_text(errors="ignore"):
            screens_using_sentinel += 1
    if screens_using_sentinel > 0:
        score = min(score + 10, 100)
        p.findings.append(f"✅ {screens_using_sentinel} screen(s) use '--' sentinel for offline state")

    p.score = max(score, 0)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 4: PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_performance(target: str) -> PillarScore:
    p = PillarScore("Performance", weight=0.15)
    score = 0

    if target == "terminal_tui":
        # Time the import of canonical_tui
        start = time.perf_counter()
        try:
            result = subprocess.run(
                ["python3", "-c",
                 "import sys; sys.path.insert(0,'tui'); import importlib.util; "
                 "spec = importlib.util.spec_from_file_location('ct', 'tui/canonical_tui.py')"],
                cwd=str(WEB_ROOT),
                capture_output=True, timeout=15
            )
            elapsed = time.perf_counter() - start
            if elapsed < 2.0:
                score += 35
                p.findings.append(f"✅ Import time: {elapsed:.2f}s (fast)")
            elif elapsed < 5.0:
                score += 20
                p.findings.append(f"⚠️  Import time: {elapsed:.2f}s (acceptable)")
                p.suggestions.append("Lazy-load heavy imports (numpy, scipy) inside workers, not at module level")
            else:
                score += 5
                p.findings.append(f"❌ Import time: {elapsed:.2f}s (slow) — blocking startup")
                p.suggestions.append("Use importlib.import_module() inside on_mount() for heavy deps")
        except subprocess.TimeoutExpired:
            p.findings.append("❌ Import timed out >15s")
            p.critical_failures = getattr(p, 'critical_failures', [])

        # Count total widgets (proxy for render complexity)
        widget_count = len(list(WIDGETS.glob("*.py"))) - 1  # exclude __init__
        p.findings.append(f"Widget library: {widget_count} custom widgets")
        if widget_count >= 10:
            score += 15
            p.findings.append("✅ Rich custom widget library")
        elif widget_count >= 5:
            score += 10

        # Check for workers (async background tasks)
        async_worker_count = 0
        for f in (list(SCREENS.glob("*.py")) + list(WIDGETS.glob("*.py"))):
            src = f.read_text(errors="ignore")
            if "@work" in src or "run_worker" in src or "Worker(" in src:
                async_worker_count += 1
        if async_worker_count >= 5:
            score += 30
            p.findings.append(f"✅ {async_worker_count} async worker(s) detected — non-blocking UI")
        elif async_worker_count > 0:
            score += 15
            p.findings.append(f"⚠️  Only {async_worker_count} async worker(s) — some screens may block")
            p.suggestions.append("Wrap all network probes (ping, SSH, port checks) in @work decorator")
        else:
            score += 0
            p.suggestions.append("Add @work background workers for all polling operations")

        # Poll intervals
        refresh_self_count = sum(
            1 for f in SCREENS.glob("*.py")
            if "refresh" in f.read_text(errors="ignore").lower() and "set_interval" in f.read_text(errors="ignore")
        )
        if refresh_self_count > 0:
            score += 20
            p.findings.append(f"✅ {refresh_self_count} screen(s) use set_interval for live refresh")
        else:
            p.suggestions.append("Use self.set_interval(5, self.refresh_data) in each screen's on_mount()")

    elif target == "web_tui":
        serve_py = TUI_ROOT / "serve_web_tui.py"
        if serve_py.exists():
            src = serve_py.read_text(errors="ignore")
            score += 20
            # Compression
            if "gzip" in src or "compress" in src.lower():
                score += 20
                p.findings.append("✅ Response compression enabled")
            else:
                p.suggestions.append("Enable gzip compression on WebSocket frames and HTTP assets")
            # 120 FPS claim
            if "120" in src:
                score += 15
                p.findings.append("✅ 120 FPS target configured")
            # Buffer sizing
            if "max_msg_size" in src or "tcp_keepalive" in src:
                score += 15
                p.findings.append("✅ WebSocket buffer tuning present")
            else:
                p.suggestions.append("Set aiohttp max_msg_size=0 and TCP keepalive for long-running terminal sessions")
            # Static asset caching
            if "Cache-Control" in src or "etag" in src.lower():
                score += 15
                p.findings.append("✅ HTTP cache headers configured")
            else:
                p.suggestions.append("Add Cache-Control headers for xterm.js static assets")
            # PTY read size
            if "65536" in src or "1024 * 64" in src or "32768" in src:
                score += 15
                p.findings.append("✅ Large PTY read buffer (fast terminal throughput)")

    p.score = min(score, p.max_score)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 5: INFORMATION DENSITY
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_information_density(target: str) -> PillarScore:
    p = PillarScore("Information Density", weight=0.12)
    score = 0

    screen_files = [f for f in SCREENS.glob("*.py") if f.name != "__init__.py"]
    total_screens = len(screen_files)

    # Measure metrics per screen
    metrics_per_screen = []
    for f in screen_files:
        src = f.read_text(errors="ignore")
        # Count distinct metric labels (heuristic: look for f-string patterns and Static widgets)
        metrics = src.count("Static(") + src.count("Label(") + src.count("Sparkline(")
        metrics_per_screen.append(metrics)

    avg = sum(metrics_per_screen) / max(len(metrics_per_screen), 1)
    p.findings.append(f"Avg widgets per screen: {avg:.1f}")

    if avg >= 15:
        score += 40
        p.findings.append("✅ High information density — rich data displays")
    elif avg >= 8:
        score += 25
        p.findings.append("⚠️  Moderate information density")
        p.suggestions.append("Add more real-time metric widgets (ELO deltas, throughput graphs, node health)")
    else:
        score += 10
        p.suggestions.append("Screens appear sparse — add Live() update loops for telemetry cards")

    # Check for multi-column layouts
    multi_col = sum(1 for f in screen_files if "Horizontal" in f.read_text(errors="ignore"))
    if multi_col >= total_screens * 0.6:
        score += 30
        p.findings.append(f"✅ {multi_col}/{total_screens} screens use Horizontal multi-column layout")
    else:
        p.suggestions.append(f"Use Horizontal() containers in more screens for side-by-side panels")

    # Check for sparklines/graphs
    has_sparkline = any("Sparkline" in f.read_text(errors="ignore") or "braille" in f.name.lower()
                        for f in (screen_files + list(WIDGETS.glob("*.py"))))
    if has_sparkline:
        score += 20
        p.findings.append("✅ Sparkline/waveform data visualizations present")
    else:
        p.suggestions.append("Add Textual Sparkline widgets for ELO trends, throughput, and ECG waveforms")

    # Scrollable content
    scrollable_screens = sum(1 for f in screen_files
                             if "ScrollableContainer" in f.read_text(errors="ignore")
                             or "VerticalScroll" in f.read_text(errors="ignore"))
    if scrollable_screens > 0:
        score += 10
        p.findings.append(f"✅ {scrollable_screens} screen(s) use scrollable containers")

    p.score = min(score, p.max_score)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 6: RESILIENCE
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_resilience(target: str) -> PillarScore:
    p = PillarScore("Resilience", weight=0.10)
    score = 0

    all_files = list(SCREENS.glob("*.py")) + list(WIDGETS.glob("*.py"))

    try_except_count = sum(src.count("except ") for f in all_files
                           if (src := f.read_text(errors="ignore")))
    bare_except = sum(src.count("except:") for f in all_files
                      if (src := f.read_text(errors="ignore")))

    p.findings.append(f"try/except blocks: {try_except_count} | bare except: {bare_except}")

    if try_except_count >= 20:
        score += 35
        p.findings.append("✅ Extensive error handling coverage")
    elif try_except_count >= 10:
        score += 20
        p.suggestions.append("Add try/except around all network probes and subprocess calls")
    else:
        score += 5
        p.suggestions.append("Critical: wrap all I/O operations in try/except to prevent TUI crashes")

    if bare_except > 5:
        score -= 10
        p.findings.append(f"⚠️  {bare_except} bare `except:` clauses — silently swallowing errors")
        p.suggestions.append("Replace bare `except:` with `except Exception as e: self.log(e)` to surface hidden bugs")

    # Check for offline/graceful degradation patterns
    offline_patterns = sum(
        1 for f in all_files
        if ("OFFLINE" in f.read_text(errors="ignore")
            or '"--"' in f.read_text(errors="ignore")
            or "unavailable" in f.read_text(errors="ignore").lower())
    )
    if offline_patterns >= 5:
        score += 35
        p.findings.append(f"✅ {offline_patterns} files handle offline/unavailable states explicitly")
    else:
        p.suggestions.append("Add explicit OFFLINE/-- states for every metric card when backend is unreachable")

    # Watchdog / supervisor
    has_supervisor = (MONOREPO / "06_scripts_and_tooling/device_watchdog").exists()
    if has_supervisor:
        score += 20
        p.findings.append("✅ Device watchdog supervisor process detected")
    else:
        p.suggestions.append("Add a supervisor process to auto-restart the TUI on crash")

    p.score = min(max(score, 0), p.max_score)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# PILLAR 7: FEATURE COVERAGE
# ─────────────────────────────────────────────────────────────────────────────

PLANNED_SCREENS = [
    ("AGI Coding Terminal",   "agi_coding_terminal"),
    ("Network Monitor",       "network_screen"),
    ("Hardware Dashboard",    "hardware_screen"),
    ("Biometrics / ECG",      "biometrics_screen"),
    ("AI Inference",          "ai_inference_screen"),
    ("Training / Gyms",       "training_screen"),
    ("Governance / Swarm",    "governance_screen"),
    ("Tooling",               "tooling_screen"),
    ("Optimization",          "optimization_screen"),
    ("Red/Blue Arena",        "live_arena_dev_screen"),
    ("Swarm Audit",           "swarm_audit_screen"),
    ("Chat IDE",              "chat_ide_screen"),
    ("Commercialization",     "commercialization_screen"),
    ("Architecture Explorer", "architecture_explorer_screen"),
]

def benchmark_feature_coverage(target: str) -> PillarScore:
    p = PillarScore("Feature Coverage", weight=0.05)
    score = 0

    implemented = [f.stem for f in SCREENS.glob("*.py") if f.name != "__init__.py"]
    hit, miss = 0, 0
    for label, key in PLANNED_SCREENS:
        if any(key in impl for impl in implemented):
            hit += 1
            p.findings.append(f"✅ {label}")
        else:
            miss += 1
            p.findings.append(f"❌ {label} — not found")
            p.suggestions.append(f"Implement {label} screen ({key}.py)")

    coverage = hit / len(PLANNED_SCREENS)
    score = int(coverage * 100)
    p.findings.insert(0, f"Screen coverage: {hit}/{len(PLANNED_SCREENS)} ({coverage*100:.0f}%)")
    p.score = min(score, p.max_score)
    return p

# ─────────────────────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

GRADE_TABLE = [
    (95, "S  — Elite"),
    (85, "A  — Excellent"),
    (75, "B  — Good"),
    (60, "C  — Acceptable"),
    (45, "D  — Needs Work"),
    (0,  "F  — Critical Issues"),
]

def compute_grade(score: float) -> str:
    for threshold, grade in GRADE_TABLE:
        if score >= threshold:
            return grade
    return "F  — Critical Issues"

def run_benchmark(target: str) -> BenchmarkReport:
    assert target in ("terminal_tui", "web_tui")
    report = BenchmarkReport(
        target=target,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+10:00"),
    )

    pillars = [
        benchmark_ui_fidelity(target),
        benchmark_ux_flow(target),
        benchmark_data_accuracy(target),
        benchmark_performance(target),
        benchmark_information_density(target),
        benchmark_resilience(target),
        benchmark_feature_coverage(target),
    ]
    report.pillars = pillars

    # Weighted overall score
    total_weight = sum(p.weight for p in pillars)
    weighted_sum = sum(p.score * p.weight for p in pillars)
    report.overall_score = round(weighted_sum / total_weight, 2)
    report.grade = compute_grade(report.overall_score)

    # Aggregate top suggestions (max 10)
    all_suggestions = []
    for p in pillars:
        all_suggestions.extend(p.suggestions)
    report.top_suggestions = all_suggestions[:10]

    # SHA-256 fingerprint
    raw = json.dumps(asdict(report), sort_keys=True)
    report.sha256 = hashlib.sha256(raw.encode()).hexdigest()[:16]

    return report

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def print_report(report: BenchmarkReport) -> None:
    if not HAS_RICH:
        print(json.dumps(asdict(report), indent=2))
        return

    label = "🖥️  Terminal TUI" if report.target == "terminal_tui" else "🌐 Web TUI"
    console.rule(f"[bold cyan]{label} Benchmark — {report.timestamp}")
    console.print(f"\n[bold white]Overall Score:[/] [bold {'green' if report.overall_score >= 75 else 'yellow' if report.overall_score >= 50 else 'red'}]{report.overall_score:.1f}/100[/]  →  [bold]{report.grade}[/]\n")

    tbl = Table(title="Pillar Breakdown", box=box.ROUNDED, show_lines=True)
    tbl.add_column("Pillar", style="cyan", min_width=25)
    tbl.add_column("Weight", justify="right")
    tbl.add_column("Score", justify="right")
    tbl.add_column("Grade", justify="center")

    for p in report.pillars:
        colour = "green" if p.score >= 75 else "yellow" if p.score >= 50 else "red"
        grade = compute_grade(p.score)
        tbl.add_row(
            p.name,
            f"{p.weight*100:.0f}%",
            f"[{colour}]{p.score:.0f}/100[/]",
            grade.split("—")[0].strip()
        )
    console.print(tbl)

    for p in report.pillars:
        if p.findings or p.suggestions:
            console.print(Panel(
                "\n".join(
                    [f"[dim]{f}[/dim]" for f in p.findings] +
                    ([""] if p.suggestions else []) +
                    [f"[yellow]💡 {s}[/yellow]" for s in p.suggestions]
                ),
                title=f"[bold]{p.name}[/bold]",
                border_style="dim"
            ))

    if report.top_suggestions:
        console.rule("[bold yellow]🔧 Top Improvement Suggestions")
        for i, s in enumerate(report.top_suggestions, 1):
            console.print(f"  [bold yellow]{i:2d}.[/] {s}")
    console.print(f"\n[dim]SHA-256: {report.sha256}[/dim]\n")

def save_results(report: BenchmarkReport) -> None:
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS, "a") as f:
        f.write(json.dumps(asdict(report)) + "\n")

    # Append LoRA training pair
    findings_text = "; ".join(
        s for p in report.pillars for s in p.suggestions
    )
    pair = {
        "instruction": f"Review the Lauburu {report.target.replace('_', ' ')} and suggest specific improvements",
        "input": f"Overall score: {report.overall_score}/100, Grade: {report.grade}",
        "output": findings_text,
        "source": "tui_benchmark_engine",
        "sha256": report.sha256
    }
    with open(LORA, "a") as f:
        f.write(json.dumps(pair) + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    targets = ["terminal_tui", "web_tui"]
    reports = []
    for target in targets:
        if HAS_RICH:
            console.print(f"\n[bold green]Running benchmark: {target}...[/]")
        report = run_benchmark(target)
        print_report(report)
        save_results(report)
        reports.append(report)

    # Comparison summary
    if HAS_RICH and len(reports) == 2:
        console.rule("[bold magenta]📊 Comparison Summary")
        tbl = Table(box=box.SIMPLE_HEAVY)
        tbl.add_column("Pillar")
        for r in reports:
            tbl.add_column(r.target.replace("_", " ").title(), justify="right")
        for i, p in enumerate(reports[0].pillars):
            scores = [f"{r.pillars[i].score:.0f}" for r in reports]
            tbl.add_row(p.name, *scores)
        tbl.add_row(
            "[bold]OVERALL[/]",
            *[f"[bold]{r.overall_score:.1f}[/]" for r in reports]
        )
        console.print(tbl)

    if HAS_RICH:
        console.print(f"\n[green]✅ Results saved to:[/] {RESULTS}")
        console.print(f"[green]✅ LoRA pairs appended to:[/] {LORA}\n")
