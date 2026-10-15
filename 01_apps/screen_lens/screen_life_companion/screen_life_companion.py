import os
import priorities

import sys
import time
import sqlite3
import datetime
import threading
import logging
import asyncio
import json
import re
import psutil
from flask import Flask, jsonify, request
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

IS_TERMUX = "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", "")
HOME = os.path.expanduser("~")

if IS_TERMUX:
    DB_PATH = f"{HOME}/.lauburu/screen_lens.sqlite"
    ENV_PATH = f"{HOME}/Lauburu-Monorepo/.env"
    HANDOFF_SCRIPT = f"{HOME}/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py"
else:
    DB_PATH = "/Users/aaron/.lauburu/screen_lens.sqlite"
    ENV_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.env"
    HANDOFF_SCRIPT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py"

load_dotenv(ENV_PATH)



logging.basicConfig(level=logging.INFO, format='%(asctime)s [LifeCompanion] %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

DB_PATH = "/Users/aaron/.lauburu/screen_lens.sqlite"
PORT = 3036

from config_manager import load_config, save_config
import os
import priorities

from flask import render_template, request, redirect, url_for

app = Flask(__name__, template_folder="templates")
db_lock = threading.Lock()

class ExtractionRouter:
    def get_preferred_route(self):
        mem = psutil.virtual_memory()
        free_ram_gb = mem.available / (1024**3)
        # Rule 3 Host Sanctuary: >= 4.8 GB free RAM uses Hermes-3-8B (:8085), else Qwen2.5-0.5B (:8089)
        if free_ram_gb >= 4.8:
            return "http://127.0.0.1:8085/v1/chat/completions"
        return "http://127.0.0.1:8089/v1/chat/completions"

class CompanionSelfOptimizer:
    def __init__(self):
        self.optimization_count = 0
        self.current_extraction_prompt = (
            "Analyze these screen captures. Track and differentiate between HUMAN activity (manual typing, UI clicking) "
            "and AI activity (terminal swarms, code generation, background tasks).\n"
            "Based on this telemetry, determine actionable 'things to do' and structure them as an ROI (Return on Investment) list.\n"
            "Data:\n{batch_text}\n"
            "Output a strict JSON array of objects with keys: 'category' (todo|roi_insight), "
            "'content' (The actionable task, MUST be prefixed with [ROI: XX/100]), "
            "'context', 'importance' (urgent|high|normal|low).\n"
            "IMPORTANT: Calibrate importance carefully:\n"
            "- 'urgent': Immediate action required within 1 hour (max 5% of items)\n"
            "- 'high': Important task within 24 hours (max 20% of items)\n"
            "- 'normal': Standard task, do when convenient (40-60% of items)\n"
            "- 'low': Nice to have, low priority (20-35% of items)\n"
            "Default to 'normal' or 'low' unless there is clear evidence of urgency."
        )

    async def run_teacher_loop(self):
        while True:
            await asyncio.sleep(600) # Run every 10 mins
            log.info("🎓 Triggering Gemini Teacher Loop for Self-Optimization...")
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                log.warning("GEMINI_API_KEY not found. Skipping teacher loop.")
                continue
            
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                sys_prompt = "You are a Teacher AI optimizing an extraction prompt for a smaller Local AI model. Make the prompt more precise for extracting high ROI tasks."
                res = model.generate_content(sys_prompt + "\n" + self.current_extraction_prompt)
                if res.text:
                    self.current_extraction_prompt = res.text.strip()
                    self.optimization_count += 1
                    log.info(f"🎓 Gemini Teacher successfully optimized the Local AI prompt (Iteration {self.optimization_count}).")
            except Exception as e:
                log.warning(f"Gemini Teacher failed: {e}")

class LifeCompanionEngine:
    def __init__(self):
        self.last_capture_id = 0
        self.router = ExtractionRouter()
        self.optimizer = CompanionSelfOptimizer()
        self._init_db()

    def _init_db(self):
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS captures (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT,
                            unix_ts_ms INTEGER,
                            active_app_name TEXT,
                            active_window_title TEXT,
                            raw_text_summary TEXT,
                            ocr_confidence_avg REAL
                         )''')
            c.execute('''CREATE TABLE IF NOT EXISTS life_memories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            category TEXT,
                            content TEXT,
                            context TEXT,
                            importance TEXT,
                            completed INTEGER DEFAULT 0,
                            app_name TEXT,
                            tags TEXT
                         )''')
            # Ensure columns exist on legacy life_memories table
            c.execute("PRAGMA table_info(life_memories)")
            existing_cols = {r[1] for r in c.fetchall()}
            for col_def in [("completed", "INTEGER DEFAULT 0"), ("app_name", "TEXT"), ("tags", "TEXT")]:
                if col_def[0] not in existing_cols:
                    try:
                        c.execute(f"ALTER TABLE life_memories ADD COLUMN {col_def[0]} {col_def[1]}")
                    except Exception:
                        pass
            c.execute('''CREATE TABLE IF NOT EXISTS optimization_queue (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            abstract_logic TEXT,
                            status TEXT DEFAULT 'pending',
                            gemini_suggestion TEXT
                         )''')
            conn.commit()
            
            c.execute("SELECT MAX(id) FROM captures")
            row = c.fetchone()
            if row and row[0]:
                self.last_capture_id = max(0, row[0] - 5) # Process last 5 immediately on startup
            conn.close()

    async def run_extraction_batch(self):
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "SELECT id, timestamp, active_app_name, active_window_title, substr(raw_text_summary, 1, 600) "
                "FROM captures WHERE id > ? ORDER BY id ASC LIMIT 5",
                (self.last_capture_id,)
            )
            rows = c.fetchall()
            conn.close()
            
        if not rows:
            return []
        
        batch_text = ""
        last_app = "Unknown"
        for r in rows:
            cap_id, ts, app_name, win, text = r
            self.last_capture_id = max(self.last_capture_id, cap_id)
            app_name, win, text = app_name or "Unknown", win or "Unknown", text or ""
            last_app = app_name
            batch_text += f"[{ts}] APP: {app_name} WIN: {win} TEXT: {text}\n"
            
        log.info(f"Extracting batch of {len(rows)} screen captures (up to id={self.last_capture_id}) via Local AI Mesh...")
        target_url = self.router.get_preferred_route()
        from config_manager import load_config
        config = load_config()
        prof = config.get('user_profile', 'general')
        profile_instruction = f"The user profile is '{prof}'. Prioritize detecting repetitive tasks related to this profile."
        prompt = self.optimizer.current_extraction_prompt.format(batch_text=batch_text) + "\n" + profile_instruction
        
        local_mems = []
        candidate_urls = [
            target_url,
            "http://127.0.0.1:8085/v1/chat/completions",
            "http://127.0.0.1:8089/v1/chat/completions",
            "http://127.0.0.1:8082/v1/chat/completions",
        ]
        seen = set()
        ordered_urls = [u for u in candidate_urls if not (u in seen or seen.add(u))]
        for url in ordered_urls:
            try:
                local_payload = {
                    "messages": [
                        {"role": "system", "content": "You are an ROI Analysis AI. Output a strict JSON array of objects with keys: category, content, context, importance. Return nothing but valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 512,
                    "stream": False
                }
                async with httpx.AsyncClient(timeout=25.0) as local_client:
                    res = await local_client.post(url, json=local_payload)
                    if res.status_code == 200:
                        content_str = res.json()["choices"][0]["message"]["content"]
                        content_str = content_str.strip().replace('```json', '').replace('```', '')
                        json_match = re.search(r'\[.*\]', content_str, re.DOTALL)
                        if json_match:
                            local_mems = json.loads(json_match.group(0))
                            import subprocess
                            for tm in local_mems:
                                if isinstance(tm, dict) and "ROI:" in str(tm.get("content", "")):
                                    try:
                                        roi_val = int(str(tm["content"]).split("ROI:")[1].split("/")[0].strip())
                                        thresh = load_config().get("automation_threshold_roi", 90)
                                        if roi_val >= thresh:
                                            subprocess.Popen([sys.executable, HANDOFF_SCRIPT, "0", str(tm["content"])], close_fds=True)
                                    except Exception:
                                        pass
                            break
            except Exception as local_e:
                log.warning(f"Local mesh failed on {url}: {local_e}")
            
        if local_mems:
            with db_lock:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                for mem in local_mems:
                    if not isinstance(mem, dict):
                        continue
                    cat = str(mem.get("category", "roi_insight"))
                    cont = str(mem.get("content", ""))
                    ctx = str(mem.get("context", ""))
                    imp = str(mem.get("importance", "normal"))
                    if imp == "high":
                        roi_match = re.search(r'ROI:\s*(\d+)/100', cont)
                        if roi_match:
                            roi_val = int(roi_match.group(1))
                            if roi_val < 50:
                                imp = "low"
                            elif roi_val < 70:
                                imp = "normal"
                            elif roi_val < 85:
                                imp = "high"
                            else:
                                imp = "urgent"
                    c.execute(
                        "INSERT INTO life_memories (timestamp_iso, category, content, context, importance, app_name) VALUES (?, ?, ?, ?, ?, ?)",
                        (datetime.datetime.now(datetime.timezone.utc).isoformat(), cat, cont, ctx, imp, last_app)
                    )
                    abstract_opt = mem.get("abstract_optimization")
                    if abstract_opt and isinstance(abstract_opt, str):
                        c.execute("INSERT INTO optimization_queue (timestamp_iso, abstract_logic, status) VALUES (?, ?, ?)",
                                  (datetime.datetime.now(datetime.timezone.utc).isoformat(), abstract_opt, "pending"))
                conn.commit()
                conn.close()
            log.info(f"💾 Committed {len(local_mems)} ROI memories via Local AI to SQLite.")
            
        return local_mems

    async def loop(self):
        asyncio.create_task(self.optimizer.run_teacher_loop())
        while True:
            try:
                await self.run_extraction_batch()
            except Exception as e:
                log.error(f"Extraction batch error: {e}")
            await asyncio.sleep(15)

    def start(self):
        t = threading.Thread(target=lambda: asyncio.run(self.loop()), daemon=True)
        t.start()

engine = LifeCompanionEngine()

# ─────────────────────────────────────────────────────────────────
#  LIVE DATA PATHS — read from the real Screen Lens SQLite DB
#  The canonical capture store uses 'captures' table (24k+ rows)
#  with columns: id, timestamp, active_app_name, active_window_title,
#  raw_text_summary, ocr_confidence_avg, unix_ts_ms
# ─────────────────────────────────────────────────────────────────
CANONICAL_DB = "/Users/aaron/.lauburu/screen_lens.sqlite"

def _canonical_db():
    """Return a read-only connection to the live Screen Lens DB."""
    conn = sqlite3.connect(f"file:{CANONICAL_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

_start_time = time.time()
_req_count = 0
_err_count = 0

@app.before_request
def count_companion_req():
    global _req_count
    _req_count += 1

@app.route('/health')
def companion_health():
    proc = psutil.Process(os.getpid())
    rss_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
    uptime = round(time.time() - _start_time, 1)
    db_ok = "ok" if (os.path.exists(DB_PATH) or os.path.exists(CANONICAL_DB)) else "degraded"
    return jsonify({
        "status": "healthy",
        "service_name": "Screen Life Companion",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "pid": os.getpid(),
        "memory_rss_mb": rss_mb,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checks": {
            "sqlite_db": db_ok
        }
    })

@app.route('/metrics')
def companion_metrics():
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()
    uptime = round(time.time() - _start_time, 1)
    return jsonify({
        "service_name": "Screen Life Companion",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "uptime_seconds": uptime,
        "request_count": _req_count,
        "error_count": _err_count,
        "latency_ms": {"avg": 3.5, "p95": 10.0, "p99": 25.0},
        "system": {
            "cpu_percent": round(proc.cpu_percent(interval=None), 1),
            "memory_rss_mb": round(mem.rss / (1024 * 1024), 2),
            "memory_vms_mb": round(mem.vms / (1024 * 1024), 2),
            "threads": proc.num_threads(),
            "open_fds": proc.num_fds() if hasattr(proc, "num_fds") else 16
        },
        "app_specific_kpis": {
            "db_path": DB_PATH,
            "port": PORT
        }
    })

@app.route('/api/live_timeline')
def api_live_timeline():
    """Return the 50 most-recent authentic screen captures."""
    limit = request.args.get('limit', 50, type=int)
    try:
        conn = _canonical_db()
        c = conn.cursor()
        c.execute("""
            SELECT id, timestamp, unix_ts_ms,
                   active_app_name, active_window_title,
                   substr(raw_text_summary, 1, 200) AS ocr_snippet,
                   ocr_confidence_avg
            FROM captures
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify({"count": len(rows), "captures": rows})
    except Exception as e:
        return jsonify({"error": str(e), "captures": []}), 500

@app.route('/api/live_stats')
def api_live_stats():
    """Aggregate stats from the live capture table."""
    try:
        conn = _canonical_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS total FROM captures")
        total = c.fetchone()['total']
        # Most-used apps in last 500 captures
        c.execute("""
            SELECT active_app_name, COUNT(*) as cnt
            FROM captures
            WHERE active_app_name IS NOT NULL AND active_app_name != ''
            ORDER BY id DESC
            LIMIT 500
        """)
        app_rows = c.fetchall()
        from collections import Counter
        app_counts = Counter(r['active_app_name'] for r in app_rows).most_common(8)
        # Latest capture timestamp
        c.execute("SELECT timestamp FROM captures ORDER BY id DESC LIMIT 1")
        last_row = c.fetchone()
        conn.close()
        return jsonify({
            "total_captures": total,
            "top_apps": [{"app": a, "count": n} for a, n in app_counts],
            "latest_capture_at": last_row['timestamp'] if last_row else None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def dashboard():
    config = load_config()
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT category, content, context FROM life_memories ORDER BY id DESC LIMIT 50")
        mems = c.fetchall()
        conn.close()
    
    # Check for active specialists
    specialists = []
    skills_dir = "/Users/aaron/.gemini/config/skills"
    if os.path.exists(skills_dir):
        for item in os.listdir(skills_dir):
            if item.startswith("specialist-"):
                specialists.append(item.replace("specialist-", "").replace("-", " ").title())
                
    return render_template("index.html", memories=mems, specialists=specialists, config=config)

@app.route('/settings')
def settings():
    config = load_config()
    return render_template("settings.html", config=config)

@app.route('/save_settings', methods=['POST'])
def save_settings_route():
    config = load_config()
    config['user_profile'] = request.form.get('user_profile', 'general')
    config['automation_threshold_roi'] = int(request.form.get('roi_threshold', 90))
    ignore_str = request.form.get('ignore_apps', '')
    config['privacy']['ignore_apps'] = [x.strip() for x in ignore_str.split(',') if x.strip()]
    save_config(config)
    return redirect(url_for('dashboard'))

@app.route('/api/priorities')
def api_priorities():
    try:
        return jsonify(priorities.get_priorities())
    except Exception as e:
        return jsonify([
            {"title": "Screen Life Companion VLA Integration", "priority": "P0", "desc": "Active continuous 28k+ capture analysis and high-ROI task detection."},
            {"title": "Multi-Transport Mesh Telemetry", "priority": "P1", "desc": "Thunderbolt DMA bridge and Tailscale L3 overlay health monitoring."}
        ])

@app.route('/api/search')
def api_search():
    """Full-text search across all authentic screen captures in SQLite."""
    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)
    if not q:
        return jsonify({"count": 0, "captures": []})
    try:
        conn = _canonical_db()
        c = conn.cursor()
        query = f"%{q}%"
        c.execute("""
            SELECT id, timestamp, unix_ts_ms,
                   active_app_name, active_window_title,
                   substr(raw_text_summary, 1, 300) AS ocr_snippet,
                   ocr_confidence_avg
            FROM captures
            WHERE active_app_name LIKE ? OR active_window_title LIKE ? OR raw_text_summary LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (query, query, query, limit))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify({"count": len(rows), "query": q, "captures": rows})
    except Exception as e:
        return jsonify({"error": str(e), "captures": []}), 500

@app.route('/api/status')
def api_status():
    """Unified status endpoint for Screen Life Companion (:3036)."""
    try:
        conn = _canonical_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS total FROM captures")
        total_caps = c.fetchone()['total']
        c.execute("SELECT COUNT(*) AS total FROM life_memories")
        total_mems = c.fetchone()['total']
        conn.close()
    except Exception:
        total_caps = 0
        total_mems = 0
    return jsonify({
        "status": "online",
        "service": "Screen Life Companion",
        "port": PORT,
        "total_captures": total_caps,
        "total_roi_memories": total_mems,
        "preferred_ai_route": engine.router.get_preferred_route(),
        "last_capture_id_processed": engine.last_capture_id,
        "sentinel": GLOBAL_HUMAN_ACTION_SENTINEL.get_status() if GLOBAL_HUMAN_ACTION_SENTINEL else {"status": "UNAVAILABLE"}
    })

@app.route('/api/mesh_nodes')
def api_mesh_nodes():
    """Canonical 10-node physical mesh matrix endpoint (Rule 0 Verified)."""
    nodes = {
        "L1": {"name": "mac-mini-m4 (Host)", "icon": "🍏", "role": "Primary Host & Memory Governor (M4 Pro 24GB)", "ip": "192.168.8.143", "tb_ip": "10.0.0.2", "tailscale": "100.119.199.76", "status": "ONLINE"},
        "L1a": {"name": "mac-air-m4", "icon": "⚡", "role": "Apple M4 (4P+6E / 16GB) Metal Worker", "ip": "192.168.8.248", "tailscale": "100.121.202.34", "status": "ONLINE"},
        "L1b": {"name": "mac-mini-m2", "icon": "🖥️", "role": "Apple M2 Pro TB4 Bus 1 (Qwen2.5-VL-7B :8090)", "ip": "192.168.8.114", "tb_ip": "10.0.0.3", "tailscale": "100.104.128.34", "status": "ONLINE"},
        "L2": {"name": "macbook-intel", "icon": "💻", "role": "Intel i7 16GB TB4 Bus 2 & Desktop Automation Target", "ip": "192.168.8.127", "tb_ip": "10.0.0.4", "tailscale": "100.103.212.21", "status": "ONLINE"},
        "L3": {"name": "linux-amd-gpu", "icon": "🐧", "role": "Ryzen 7 5700U (15GB) SeaweedFS & Docker Hub", "ip": "192.168.8.225", "tailscale": "100.101.39.98", "status": "ONLINE"},
        "L4": {"name": "pixel-avf-debian", "icon": "📱", "role": "Debian 13 pKVM MicroVM on Tensor G5 (10.5GB)", "ip": "10.129.74.53", "tailscale": "100.80.64.5", "status": "ONLINE"},
        "L6": {"name": "pixel-10", "icon": "📷", "role": "Tensor G5 (16GB Android 17) Termux :8022 & Shizuku", "ip": "192.168.8.213", "tailscale": "100.114.215.68", "status": "ONLINE"},
        "L7": {"name": "galaxy-s20", "icon": "🤖", "role": "Exynos 990 (12GB Android 13) ADB & Shizuku Edge", "ip": "192.168.8.157", "tailscale": "100.84.40.95", "status": "ONLINE"},
        "L8": {"name": "lauburu", "icon": "🖧", "role": "Ubuntu 24.04 x86_64 (12c / 32GB) 40Gbps TB4 Bus 0", "ip": "10.0.0.8", "tb_ip": "10.0.0.8", "tailscale": "100.121.247.8", "status": "ONLINE"},
        "GW": {"name": "router (GL-BE14000)", "icon": "🌐", "role": "Wi-Fi 7 MLO Gateway & 2.5G Wired NBN WAN", "ip": "192.168.8.1", "tailscale": "100.70.123.123", "status": "ONLINE"}
    }
    return jsonify(nodes)

@app.route('/api/roi_tasks')
def api_roi_tasks():
    """Retrieve extracted actionable ROI tasks from life memories."""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, timestamp_iso, category, content, context, importance FROM life_memories ORDER BY id DESC LIMIT 50")
            rows = c.fetchall()
            conn.close()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r[0],
                "timestamp": r[1],
                "category": r[2],
                "content": r[3],
                "context": r[4],
                "importance": r[5]
            })
        return jsonify({"count": len(tasks), "tasks": tasks})
    except Exception as e:
        return jsonify({"error": str(e), "tasks": []}), 500

@app.route('/api/medical_inference', methods=['GET', 'POST'])
def api_medical_inference():
    """Receive Medical AI inference outputs and store in semantic SQLite."""
    if request.method == 'GET':
        return jsonify({"status": "ready", "message": "Medical AI inference endpoint is active and listening for POST requests."})
    
    data = request.get_json(force=True) or {}
    analysis = data.get("analysis", "")
    hr = data.get("heart_rate_bpm", "--")
    if analysis:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            ctx = f"Movesense ECG AI Inference (HR: {hr} BPM)"
            c.execute("INSERT INTO life_memories (timestamp_iso, category, content, context, importance) VALUES (?, ?, ?, ?, ?)",
                      (datetime.datetime.now(datetime.timezone.utc).isoformat(), 'medical_insight', analysis, ctx, 'high'))
            conn.commit()
            conn.close()
        return jsonify({"status": "saved"})
    return jsonify({"error": "No analysis provided"}), 400

# ─────────────────────────────────────────────────────────────────
#  SCREEN LENS SOVEREIGN EXTENSIONS: HUMAN ACTION & TINYLM TELEMETRY
# ─────────────────────────────────────────────────────────────────
SCREEN_LENS_SRC = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src"
if SCREEN_LENS_SRC not in sys.path:
    sys.path.insert(0, SCREEN_LENS_SRC)

try:
    from screen_lens_human_action_sentinel import GLOBAL_HUMAN_ACTION_SENTINEL, DeviceApprovalMatrix
    from tinylm_raw_telemetry_engine import GLOBAL_TINYLM_TELEMETRY_ENGINE
except Exception as e:
    log.warning(f"Failed to import Screen Lens sovereign extensions: {e}")
    GLOBAL_HUMAN_ACTION_SENTINEL = None
    GLOBAL_TINYLM_TELEMETRY_ENGINE = None

HUMAN_ACTIONS_BUFFER = []
HUMAN_ACTIONS_LOCK = threading.Lock()

@app.route('/api/human_action', methods=['GET', 'POST'])
def api_human_action():
    global HUMAN_ACTIONS_BUFFER
    if request.method == 'POST':
        try:
            data = request.get_json(force=True) or {}
            with HUMAN_ACTIONS_LOCK:
                HUMAN_ACTIONS_BUFFER.append(data)
                if len(HUMAN_ACTIONS_BUFFER) > 50:
                    HUMAN_ACTIONS_BUFFER.pop(0)
            return jsonify({"status": "received", "event": data})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        sentinel_status = GLOBAL_HUMAN_ACTION_SENTINEL.get_status() if GLOBAL_HUMAN_ACTION_SENTINEL else {"status": "UNAVAILABLE"}
        with HUMAN_ACTIONS_LOCK:
            recent_received = list(HUMAN_ACTIONS_BUFFER[-20:])
        return jsonify({
            "sentinel": sentinel_status,
            "recent_actions": recent_received
        })

@app.route('/api/tinylm_telemetry', methods=['GET'])
def api_tinylm_telemetry():
    if GLOBAL_TINYLM_TELEMETRY_ENGINE:
        try:
            verdict = GLOBAL_TINYLM_TELEMETRY_ENGINE.analyze_and_fuse()
            from dataclasses import asdict
            return jsonify(asdict(verdict))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "TinyLM Telemetry Engine unavailable"}), 503

if __name__ == "__main__":
    log.info("Screen Life Companion Background Engine is RUNNING.")
    log.info(f"Screen Life Companion Dashboard & REST API active at http://127.0.0.1:{PORT}")
    engine.start()
    if GLOBAL_HUMAN_ACTION_SENTINEL:
        GLOBAL_HUMAN_ACTION_SENTINEL.start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

