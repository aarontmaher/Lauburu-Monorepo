#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  Lauburu C++ TUI Bench Automator                                     ║
║  Watches .cpp sources → auto-recompiles → re-executes notebook       ║
║  Zero-mock: all timing from real clang++ builds on M4 Mac Mini       ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import os, sys, time, json, hashlib, subprocess, logging, signal, threading
from pathlib import Path
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────
MONOREPO   = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NB_PATH    = MONOREPO / "01_apps/notebooks/07_cpp_tui_canonical_recreation_studio.ipynb"
VENV_PY    = MONOREPO / "01_apps/notebooks/.venv/bin"
FTXUI      = Path("/Users/aaron/.homebrew/Cellar/ftxui/7.0.3")
RESULTS_DB = Path("/tmp/lauburu_tui_bench_history.jsonl")
LOG_PATH   = Path("/tmp/lauburu_tui_bench_automator.log")
POLL_SEC   = 3       # file change poll interval
DEBOUNCE   = 2.0     # seconds to wait after last change before triggering

SOURCES = {
    "ftxui": Path("/tmp/lauburu_ftxui_demo.cpp"),
    "ncurses": Path("/tmp/lauburu_ncurses_demo.cpp"),
}
OUTPUTS = {
    "ftxui": Path("/tmp/lauburu_ftxui"),
    "ncurses": Path("/tmp/lauburu_ncurses"),
}

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TUI-AUTO] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────
def file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ""

def get_sdk() -> str:
    r = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True)
    return r.stdout.strip()

def compile_ftxui(src: Path, out: Path, sdk: str) -> dict:
    t0 = time.perf_counter()
    r = subprocess.run(
        ["xcrun", "clang++", "-std=c++20", "-O2",
         f"-isysroot", sdk,
         f"-I{FTXUI}/include",
         f"-L{FTXUI}/lib",
         str(src),
         "-lftxui-component", "-lftxui-dom", "-lftxui-screen",
         "-o", str(out)],
        capture_output=True, text=True
    )
    elapsed = round(time.perf_counter() - t0, 2)
    ok = r.returncode == 0
    sz = out.stat().st_size // 1024 if ok else 0
    syms = 0
    if ok:
        nm = subprocess.run(["nm", str(out)], capture_output=True)
        syms = len(nm.stdout.splitlines())
    return {"ok": ok, "compile_s": elapsed, "binary_kb": sz, "symbols": syms,
            "stderr": r.stderr[-300:] if not ok else ""}

def compile_ncurses(src: Path, out: Path, sdk: str) -> dict:
    t0 = time.perf_counter()
    r = subprocess.run(
        ["xcrun", "clang++", "-std=c++20", "-O2",
         f"-isysroot", sdk, str(src),
         "-lncurses", "-o", str(out)],
        capture_output=True, text=True
    )
    elapsed = round(time.perf_counter() - t0, 2)
    ok = r.returncode == 0
    sz = out.stat().st_size // 1024 if ok else 0
    syms = 0
    if ok:
        nm = subprocess.run(["nm", str(out)], capture_output=True)
        syms = len(nm.stdout.splitlines())
    return {"ok": ok, "compile_s": elapsed, "binary_kb": sz, "symbols": syms,
            "stderr": r.stderr[-300:] if not ok else ""}

def run_notebook() -> bool:
    """Execute notebook in-place via nbconvert."""
    nb_jupyter = VENV_PY / "jupyter"
    log.info("Executing notebook...")
    r = subprocess.run(
        [str(nb_jupyter), "nbconvert",
         "--to", "notebook",
         "--execute",
         "--ExecutePreprocessor.kernel_name=lauburu-notebooks",
         "--ExecutePreprocessor.timeout=180",
         "--inplace",
         str(NB_PATH)],
        capture_output=True, text=True,
        cwd=str(MONOREPO)
    )
    if r.returncode == 0:
        log.info("Notebook executed OK")
    else:
        log.error(f"Notebook failed: {r.stderr[-200:]}")
    return r.returncode == 0

def record_result(ftxui_result: dict, ncurses_result: dict):
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "ftxui": ftxui_result,
        "ncurses": ncurses_result,
    }
    with open(RESULTS_DB, "a") as f:
        f.write(json.dumps(entry) + "\n")
    log.info(f"Bench: FTXUI={ftxui_result['compile_s']}s/{ftxui_result['binary_kb']}KB "
             f"ncurses={ncurses_result['compile_s']}s/{ncurses_result['binary_kb']}KB")

def print_summary(history_path: Path):
    """Print last 5 benchmark runs as ASCII table."""
    if not history_path.exists():
        return
    lines = history_path.read_text().strip().splitlines()[-5:]
    print(f"\n{'─'*70}")
    print(f"{'Timestamp':<24} {'FTXUI compile':>14} {'FTXUI KB':>10} {'ncurses':>12} {'ncurses KB':>11}")
    print(f"{'─'*70}")
    for line in lines:
        try:
            e = json.loads(line)
            ts = e['ts'][:19]
            fv = e['ftxui']
            nv = e['ncurses']
            print(f"{ts:<24} {fv['compile_s']:>12.2f}s {fv['binary_kb']:>9}KB "
                  f"{nv['compile_s']:>10.2f}s {nv['binary_kb']:>9}KB")
        except Exception:
            pass
    print(f"{'─'*70}\n")

# ── Main watch loop ───────────────────────────────────────────────────────
def main():
    log.info("═══════════════════════════════════════════════════════")
    log.info(" Lauburu TUI Bench Automator starting")
    log.info(f" Watching: {list(SOURCES.values())}")
    log.info(f" Notebook: {NB_PATH}")
    log.info(f" Poll interval: {POLL_SEC}s | Debounce: {DEBOUNCE}s")
    log.info("═══════════════════════════════════════════════════════")

    sdk = get_sdk()
    last_hashes = {k: file_hash(v) for k, v in SOURCES.items()}
    last_change_time: float = 0
    pending = False

    # Initial build on startup
    log.info("Initial build on startup...")
    sdk_val = get_sdk()
    fr = compile_ftxui(SOURCES["ftxui"], OUTPUTS["ftxui"], sdk_val)
    nr = compile_ncurses(SOURCES["ncurses"], OUTPUTS["ncurses"], sdk_val)
    record_result(fr, nr)
    print_summary(RESULTS_DB)

    while True:
        time.sleep(POLL_SEC)

        # Check for source changes
        changed = False
        for name, src in SOURCES.items():
            h = file_hash(src)
            if h and h != last_hashes.get(name, ""):
                log.info(f"Change detected: {src.name}")
                last_hashes[name] = h
                changed = True

        if changed:
            last_change_time = time.time()
            pending = True

        # Debounce: only trigger if no new changes for DEBOUNCE seconds
        if pending and (time.time() - last_change_time) >= DEBOUNCE:
            pending = False
            log.info("⚡ Building...")
            sdk_val = get_sdk()
            fr = compile_ftxui(SOURCES["ftxui"], OUTPUTS["ftxui"], sdk_val)
            nr = compile_ncurses(SOURCES["ncurses"], OUTPUTS["ncurses"], sdk_val)
            record_result(fr, nr)
            print_summary(RESULTS_DB)
            # Re-execute notebook with fresh data
            run_notebook()

if __name__ == "__main__":
    # Graceful shutdown
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    main()
