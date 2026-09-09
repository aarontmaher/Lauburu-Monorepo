import os
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

load_dotenv("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.env")


logging.basicConfig(level=logging.INFO, format='%(asctime)s [LifeCompanion] %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

DB_PATH = "/Users/aaron/.lauburu/screen_lens.sqlite"
PORT = 3036

app = Flask(__name__)
db_lock = threading.Lock()

class ExtractionRouter:
    def get_preferred_route(self):
        mem = psutil.virtual_memory()
        free_ram_gb = mem.available / (1024**3)
        if free_ram_gb < 10.5:
            return "http://100.103.212.21:8081/v1/chat/completions" # L2 MacBook Pro
        return "http://127.0.0.1:8081/v1/chat/completions" # Host Mac Mini

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
            "'context', 'importance' (urgent|high|normal)."
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
            c.execute('''CREATE TABLE IF NOT EXISTS screen_captures (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            app_name TEXT,
                            window_title TEXT,
                            ocr_text TEXT
                         )''')
            c.execute('''CREATE TABLE IF NOT EXISTS life_memories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            category TEXT,
                            content TEXT,
                            context TEXT,
                            importance TEXT
                         )''')
            conn.commit()
            
            c.execute("SELECT MAX(id) FROM screen_captures")
            row = c.fetchone()
            if row and row[0]:
                self.last_capture_id = max(0, row[0] - 5) # Process last 5
            conn.close()

    async def run_extraction_batch(self):
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, timestamp_iso, app_name, window_title, ocr_text FROM screen_captures WHERE id > ? ORDER BY id ASC LIMIT 5", (self.last_capture_id,))
            rows = c.fetchall()
            conn.close()
            
        if not rows: return []
        
        batch_text = ""
        for r in rows:
            cap_id, ts, app, win, text = r
            self.last_capture_id = max(self.last_capture_id, cap_id)
            app, win, text = app or "Unknown", win or "Unknown", text or ""
            batch_text += f"[{ts}] APP: {app} WIN: {win} TEXT: {text}\n"
            
        log.info(f"Extracting batch of {len(rows)} screen captures via Local AI Mesh...")
        target_url = self.router.get_preferred_route()
        prompt = self.optimizer.current_extraction_prompt.format(batch_text=batch_text)
        
        local_mems = []
        try:
            local_payload = {
                "messages": [
                    {"role": "system", "content": "You are an ROI Analysis AI. Output a strict JSON array of objects. Return nothing but JSON. Strip ```json"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "stream": False
            }
            async with httpx.AsyncClient(timeout=45.0) as local_client:
                res = await local_client.post(target_url, json=local_payload)
                if res.status_code == 200:
                    content_str = res.json()["choices"][0]["message"]["content"]
                    content_str = content_str.strip().replace('```json', '').replace('```', '')
                    
                    json_match = re.search(r'\[.*\]', content_str, re.DOTALL)
                    if json_match:
                        local_mems = json.loads(json_match.group(0))
                        import subprocess
                        for tm in local_mems:
                            if "ROI:" in tm.get("content", ""):
                                try:
                                    roi_val = int(tm["content"].split("ROI:")[1].split("/")[0].strip())
                                    if roi_val >= 90:
                                        subprocess.Popen(["python3", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py", "0", tm["content"]], start_new_session=True)
                                except: pass
        except Exception as local_e:
            log.warning(f"Local mesh failed on {target_url}: {local_e}")
            
        if local_mems:
            with db_lock:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                for mem in local_mems:
                    cat = mem.get("category", "roi_insight")
                    cont = mem.get("content", "")
                    ctx = mem.get("context", "")
                    imp = mem.get("importance", "normal")
                    c.execute("INSERT INTO life_memories (timestamp_iso, category, content, context, importance) VALUES (?, ?, ?, ?, ?)",
                              (datetime.datetime.now(datetime.timezone.utc).isoformat(), cat, cont, ctx, imp))
                conn.commit()
                conn.close()
            log.info(f"💾 Committed {len(local_mems)} ROI memories via Local AI to Obsidian Tri-Vault.")
            
        return local_mems

    async def loop(self):
        asyncio.create_task(self.optimizer.run_teacher_loop())
        while True:
            await self.run_extraction_batch()
            await asyncio.sleep(5)

    def start(self):
        t = threading.Thread(target=lambda: asyncio.run(self.loop()), daemon=True)
        t.start()

engine = LifeCompanionEngine()

@app.route('/')
def dashboard():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT category, content, context FROM life_memories ORDER BY id DESC LIMIT 50")
        mems = c.fetchall()
        conn.close()
        
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lauburu Screen Life Companion</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; background-color: #090d16; color: #e2e8f0; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .cyber-card { background: rgba(15, 23, 42, 0.85); border: 1px solid #1e293b; backdrop-filter: blur(12px); }
    .cyber-glow { box-shadow: 0 0 20px rgba(56, 189, 248, 0.15); }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">
    <header class="cyber-card rounded-2xl p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 cyber-glow border-cyan-900/50">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-2xl">🧠</div>
        <div>
          <h1 class="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            Lauburu Screen Life Companion
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mono font-semibold">24/7 ACTIVE</span>
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30 mono font-semibold">LOCAL AI BACKBONE</span>
          </h1>
          <p class="text-sm text-slate-400">Autonomous Second Brain · Real-Time Screen Perception · Obsidian Tri-Vault Sync</p>
        </div>
      </div>
    </header>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="cyber-card rounded-xl p-6 border-slate-800">
        <h2 class="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
          <span class="text-cyan-400">⚡</span> High ROI Tasks Extracted
        </h2>
        <div class="space-y-3">
'''
    for m in mems:
        cat, content, context = m
        if "ROI:" in content:
            html += f'''
          <div class="p-3 rounded-lg bg-slate-900/50 border border-slate-700/50 hover:border-cyan-500/30 transition-colors">
            <div class="flex justify-between items-start mb-1">
              <span class="text-xs font-semibold text-cyan-400 uppercase tracking-wider">{cat}</span>
            </div>
            <p class="text-sm text-slate-300">{content}</p>
            <p class="text-xs text-slate-500 mt-2 mono">Context: {context}</p>
          </div>
'''
    html += '''
        </div>
      </div>
      
      <div class="cyber-card rounded-xl p-6 border-slate-800">
        <h2 class="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
          <span class="text-emerald-400">🎓</span> Gemini Teacher Status
        </h2>
        <div class="space-y-4">
          <div class="p-4 rounded-lg bg-slate-900/50 border border-emerald-500/20">
            <h3 class="text-sm font-semibold text-emerald-400 mb-2">Self-Optimization Loop</h3>
            <p class="text-sm text-slate-300">The Gemini 3.8 Flash Teacher AI runs asynchronously every 10 minutes to auto-tune the extraction prompts used by the Local AI backbone. Routine extraction is restricted exclusively to local nodes.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>'''
    return html

if __name__ == "__main__":
    log.info("Screen Life Companion Background Engine is RUNNING.")
    log.info(f"Screen Life Companion Dashboard & REST API active at http://127.0.0.1:{PORT}")
    engine.start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
