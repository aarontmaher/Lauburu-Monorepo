#!/usr/bin/env python3
"""
Lauburu Local AI Router & Skill Dispatcher
==========================================
Unified CLI routing natural language prompts or short commands
to local models, Jules agent, free AI CLIs, VS Code, and JupyterLab.
"""

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
DEBATE_SCRIPT = REPO_ROOT / "05_agents_and_swarms/ai_debate/bilateral_swarm_debater.py"
VOICE_SCRIPT = REPO_ROOT / "01_apps/automotive/voice_coder_router.py"
LENS_DB = Path(os.path.expanduser("~/.lauburu/screen_lens.sqlite"))

SUBSYSTEM_MAP = {
    "infra": "00_core_infrastructure",
    "apps": "01_apps",
    "ai": "02_ai_models_and_inference",
    "inference": "02_ai_models_and_inference",
    "biometrics": "03_biometrics_and_telemetry",
    "data": "04_data_and_memory",
    "swarms": "05_agents_and_swarms",
    "agents": "05_agents_and_swarms",
    "tooling": "06_scripts_and_tooling",
    "docs": "07_docs_and_architecture"
}


def print_banner():
    print("⚡ \033[1;36mLauburu Local AI Router\033[0m (Mesh Port 8081-8084 | 82.8 GB VRAM)")


def run_debate(topic: str):
    print(f"\n⚖️ \033[1;33mRouting to Bilateral Swarm AI Debate...\033[0m")
    subprocess.run([sys.executable, str(DEBATE_SCRIPT), "--topic", topic])


def run_jules(prompt: str):
    print(f"\n🤖 \033[1;35mSpawning Google Jules Autonomous Coding Agent...\033[0m")
    jules_bin = os.path.expanduser("~/.local/bin/jules")
    if prompt:
        subprocess.run([jules_bin, "new", prompt])
    else:
        subprocess.run([jules_bin])


def run_free_ai(prompt: str):
    print(f"\n✨ \033[1;32mQuerying Free Keyless AI (tgpt)...\033[0m")
    tgpt_bin = os.path.expanduser("~/.local/bin/tgpt")
    subprocess.run([tgpt_bin, prompt])


def run_notebook():
    print(f"\n📓 \033[1;32mLaunching Lauburu JupyterLab Native Standalone App...\033[0m")
    app_path = "/Applications/Lauburu JupyterLab.app"
    if os.path.exists(app_path):
        subprocess.Popen(["/Users/aaron/.local/share/uv/tools/jupyterlab/bin/python", "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/lauburu_jupyter_native_window.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["open", "http://localhost:8890/lab/tree/01_apps/notebooks/00_lauburu_global_master_project.ipynb"])


def run_vscode():
    print(f"\n💻 \033[1;34mOpening Full Embedded VS Code (Port 8090)...\033[0m")
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    r = s.connect_ex(('127.0.0.1', 8090))
    s.close()
    if r != 0:
        subprocess.Popen([
            os.path.expanduser("~/.local/bin/code-server"),
            "--config", os.path.expanduser("~/.config/code-server/config.yaml"),
            "/Volumes/Lauburu-Monorepo"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
    
    # Open in default browser tab without creating duplicate dock instances
    subprocess.run(["open", "http://localhost:8090"])


def run_tui():
    tui_bin = os.path.expanduser("~/.local/bin/lauburu-tui")
    if os.path.exists(tui_bin):
        os.execv(tui_bin, [tui_bin])
    else:
        print("⚠️ lauburu-tui binary not found in ~/.local/bin")


def run_lens_query(query: str):
    import sqlite3
    if not LENS_DB.exists():
        print("⚠️ Screen Lens DB not found at ~/.lauburu/screen_lens.sqlite")
        return
    conn = sqlite3.connect(f"file:{LENS_DB}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, active_app_name, active_window_title, substr(raw_text_summary, 1, 100)
        FROM captures
        WHERE raw_text_summary LIKE ? OR active_app_name LIKE ?
        ORDER BY id DESC LIMIT 10
    """, (f"%{query}%", f"%{query}%"))
    rows = c.fetchall()
    conn.close()
    print(f"\n👁️ \033[1;35mScreen Lens Search Results for '{query}':\033[0m")
    for r in rows:
        print(f"  • [{r[0]}] \033[1;34m{r[1]}\033[0m | {r[2]}")
        print(f"    ↳ {r[3]}...\n")


def run_tests(target: str = ""):
    target = target.strip("[]'\" ").lower()
    if target in ("", "all", "subsystem"):
        print(f"\n🧪 \033[1;32mRunning Pytest Suite across Monorepo...\033[0m")
        cmd = [sys.executable, "-m", "pytest", "02_ai_models_and_inference/tests/test_halda_scheduler.py"]
    elif target in SUBSYSTEM_MAP:
        mapped = SUBSYSTEM_MAP[target]
        print(f"\n🧪 \033[1;32mRunning Pytest Suite for Subsystem '{mapped}'...\033[0m")
        cmd = [sys.executable, "-m", "pytest", mapped]
    else:
        print(f"\n🧪 \033[1;32mRunning Pytest for '{target}'...\033[0m")
        cmd = [sys.executable, "-m", "pytest", target]
    
    subprocess.run(cmd, cwd=str(REPO_ROOT))


def run_mesh_health():
    import urllib.request
    ports = {
        "8081 (llama.cpp / prima)": 8081,
        "8082 (Ray / prima shard)": 8082,
        "8083 (Devil's Advocate)": 8083,
        "8090 (Embedded VS Code)": 8090,
        "8890 (JupyterLab Server)": 8890,
        "3035 (Screen Lens API)": 3035
    }
    print("\n🌐 \033[1;36mChecking Mesh Port & Service Health:\033[0m")
    for name, port in ports.items():
        try:
            url = f"http://127.0.0.1:{port}/health" if port not in (8890, 8090) else (f"http://127.0.0.1:{port}/lab" if port == 8890 else f"http://127.0.0.1:{port}/")
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                print(f"  ✅ \033[1;32m{name:<25}\033[0m : LIVE (HTTP {resp.status})")
        except Exception:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            r = s.connect_ex(('127.0.0.1', port))
            s.close()
            if r == 0:
                print(f"  ✅ \033[1;32m{name:<25}\033[0m : ACTIVE (Port Open)")
            else:
                print(f"  ❌ \033[1;31m{name:<25}\033[0m : STANDBY / OFFLINE")


def main():
    if len(sys.argv) < 2:
        print_banner()
        print("""
Commands:
  router jules "<task>"     -> Spawn Google Jules Autonomous Coding Agent
  router free "<query>"     -> Query 100% Free Keyless AI (tgpt)
  router vscode             -> Launch Full Embedded VS Code IDE (Port 8090)
  router voila              -> Launch Standalone Interactive App (Voila Port 8866)
  router notebook           -> Launch Master Global Project Notebook
  router debate "<topic>"   -> Trigger Bilateral Swarm AI Debate
  router voice "<prompt>"   -> Synthesize code from spoken prompt
  router tui                -> Launch Ratatui Mesh Terminal
  router lens "<query>"     -> Search live Screen Lens OCR & events
  router test [subsystem]   -> Run pytest suite
  router mic                -> Launch Mac Mini Studio Mic Receiver for Pixel
  router auto               -> Prepare & Launch Android Auto In-Car Voice Coder
  router loop               -> Run Autonomous Continuous Self-Optimization Cycle
  router mesh               -> Inspect 7-layer mesh ports & services
""")
        return

    cmd = sys.argv[1].lower().strip()
    args = " ".join(sys.argv[2:]).strip()

    if cmd in ("jules", "julien"):
        run_jules(args)
    elif cmd in ("free", "tgpt", "ask"):
        run_free_ai(args if args else "Explain the benefits of decentralized local AI mesh")
    elif cmd in ("vscode", "code", "ide", "editor"):
        run_vscode()
    elif cmd in ("voila", "app", "dashboard", "viola"):
        import subprocess
        subprocess.run(["open", "http://localhost:8866"])
    elif cmd in ("notebook", "nb", "jupyter", "j"):
        run_notebook()
    elif cmd in ("debate", "/ai-debate", "d"):
        topic = args if args else "Should we shard all local LLM weights via Thunderbolt 4 PRP Ring?"
        run_debate(topic)
    elif cmd in ("voice", "speak", "v", "coder"):
        subprocess.run([sys.executable, str(VOICE_SCRIPT), args])
    elif cmd in ("tui", "ratatui", "mesh-ui"):
        run_tui()
    elif cmd in ("lens", "search", "ocr"):
        run_lens_query(args if args else "python")
    elif cmd in ("test", "pytest", "tests"):
        run_tests(args)
    elif cmd in ("mic", "pixel-mic", "audio"):
        import subprocess
        subprocess.run([sys.executable, "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/mac_mini_mic_receiver.py"])
    elif cmd in ("auto", "car", "android-auto"):
        import subprocess
        subprocess.run([sys.executable, "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/in_car_voice_coder.py", "--demo"])
    elif cmd in ("loop", "optimize", "cycle"):
        run_debate("Continuous Autonomous Closed-Loop Self-Optimization & Benchmark Cycle")
    elif cmd in ("mesh", "health", "status"):
        run_mesh_health()
    else:
        full_query = " ".join(sys.argv[1:])
        if any(w in full_query.lower() for w in ["jules", "julien"]):
            run_jules(full_query)
        elif any(w in full_query.lower() for w in ["vscode", "ide", "editor", "code"]):
            run_vscode()
        elif any(w in full_query.lower() for w in ["notebook", "jupyter", "explore"]):
            run_notebook()
        elif any(w in full_query.lower() for w in ["voice", "speak", "write a function"]):
            subprocess.run([sys.executable, str(VOICE_SCRIPT), full_query])
        elif any(w in full_query.lower() for w in ["debate", "should we", "versus", "vs"]):
            run_debate(full_query)
        elif any(w in full_query.lower() for w in ["tui", "dashboard"]):
            run_tui()
        elif any(w in full_query.lower() for w in ["lens", "screen"]):
            run_lens_query(full_query)
        elif any(w in full_query.lower() for w in ["test", "verify"]):
            run_tests()
        else:
            run_debate(full_query)


if __name__ == "__main__":
    main()
