import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    lines = f.readlines()

out = []
in_bad_block = False
for i, line in enumerate(lines):
    if "def run_extraction_batch(self):" in line:
        in_bad_block = True
        
        # Write our clean, exact replacement block
        out.append(line)
        out.append("""        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT id, timestamp_iso, app_name, window_title, ocr_text FROM screen_captures WHERE id > ? ORDER BY id ASC LIMIT 5", (self.last_capture_id,))
            rows = c.fetchall()
            
            if not rows: return []
            
            batch_text = ""
            for r in rows:
                cap_id, ts, app, win, text = r
                self.last_capture_id = max(self.last_capture_id, cap_id)
                app, win, text = app or "Unknown", win or "Unknown", text or ""
                self.update_focus_telemetry(app, win)
                batch_text += f"[{ts}] APP: {app} WIN: {win} TEXT: {text}\\n"
                
            log.info(f"Extracting batch of {len(rows)} screen captures via Local AI Mesh...")
            
            prompt = (
                "Analyze these screen captures. Track and differentiate between HUMAN activity (manual typing, UI clicking) "
                "and AI activity (terminal swarms, code generation, background tasks).\\n"
                "Based on this telemetry, determine actionable 'things to do' and structure them as an ROI (Return on Investment) list.\\n"
                f"Data:\\n{batch_text}\\n"
                "Output a strict JSON array of objects with keys: 'category' (todo|roi_insight), "
                "'content' (The actionable task, MUST be prefixed with [ROI: XX/100]), "
                "'context', 'importance' (urgent|high|normal)."
            )
            
            local_mems = []
            
            # --- LOCAL MESH EXECUTION (WITH L2 CIRCUIT BREAKER) ---
            import psutil
            import json
            import re
            import time
            mem = psutil.virtual_memory()
            free_ram_gb = mem.available / (1024**3)
            
            target_url = "http://127.0.0.1:8081/v1/chat/completions"
            if free_ram_gb < 10.5:
                log.warning(f"⚠️ RAM CIRCUIT BREAKER: Free RAM ({free_ram_gb:.1f} GB) too close to Sanctuary limit. Routing to L2 Mesh Node (MacBook Pro).")
                target_url = "http://100.103.212.21:8081/v1/chat/completions"
                
            import asyncio
            async def _run_local_extract():
                try:
                    import httpx
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
                            
                            json_match = re.search(r'\\[.*\\]', content_str, re.DOTALL)
                            if json_match:
                                import subprocess
                                _mems = json.loads(json_match.group(0))
                                for tm in _mems:
                                    if "ROI:" in tm.get("content", ""):
                                        try:
                                            roi_val = int(tm["content"].split("ROI:")[1].split("/")[0].strip())
                                            if roi_val >= 90:
                                                subprocess.Popen(["python3", "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py", "0", tm["content"]], start_new_session=True)
                                        except: pass
                                return _mems
                except Exception as local_e:
                    log.warning(f"Local mesh failed on {target_url}: {local_e}")
                return []
            
            local_mems = asyncio.run(_run_local_extract())
            
            # --- SAVE WINNING MEMORIES ---
            if local_mems:
                for mem in local_mems:
                    cat = mem.get("category", "roi_insight")
                    cont = mem.get("content", "")
                    ctx = mem.get("context", "")
                    imp = mem.get("importance", "normal")
                    c.execute("INSERT INTO life_memories (timestamp_iso, category, content, context, importance) VALUES (?, ?, ?, ?, ?)",
                              (datetime.datetime.now(datetime.timezone.utc).isoformat(), cat, cont, ctx, imp))
                conn.commit()
                log.info(f"💾 Committed {len(local_mems)} ROI memories via Local AI to Obsidian Tri-Vault.")
            conn.close()
            return local_mems
""")
    
    if in_bad_block and "    def start(self):" in line:
        in_bad_block = False
        out.append(line)
        continue
        
    if not in_bad_block:
        out.append(line)

# Since __init__ was broken by the previous patch, let's fix CompanionSelfOptimizer.__init__ 
out2 = []
skip2 = False
for line in out:
    if "class CompanionSelfOptimizer:" in line:
        out2.append(line)
        out2.append("    def __init__(self):\n")
        out2.append("        self.optimization_count = 0\n")
        out2.append("        self.current_extraction_prompt = \"\"\"Analyze these screen captures.\\nData:\\n{batch_text}\"\"\"\n")
        skip2 = True
    elif skip2 and "def _async_run_optimization_loop(self):" in line:
        skip2 = False
        out2.append(line)
    elif not skip2:
        out2.append(line)

with open(file_path, "w") as f:
    f.writelines(out2)
