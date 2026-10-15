import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace the extraction block in run_extraction_batch
regex_pattern = r"log\.info\(f\"Offloading batch of \{len\(rows\)\} screen captures to Gemini 3\.8 Flash CPU for extraction\.\.\.\"\).*?# --- SAVE WINNING MEMORIES ---"

replacement = """log.info(f"Extracting batch of {len(rows)} screen captures via Local AI Mesh...")
            
            opt_prompt = getattr(self, 'optimizer', None)
            if opt_prompt:
                prompt = opt_prompt.current_extraction_prompt.format(batch_text=batch_text)
            else:
                prompt = (
                    "Analyze these screen captures. Track and differentiate between HUMAN activity (manual typing, UI clicking) "
                    "and AI activity (terminal swarms, code generation, background tasks). \\n"
                    "Based on this telemetry, determine actionable 'things to do' and structure them as an ROI (Return on Investment) list. "
                    "High ROI tasks are those where AI can automate a tedious human task, or where human intervention unblocks a stalled AI swarm.\\n"
                    f"Data:\\n{batch_text}\\n"
                    "Output a strict JSON array of objects with keys: 'category' (todo|roi_insight), "
                    "'content' (The actionable task, MUST be prefixed with [ROI: XX/100]), "
                    "'context' (Explain why this has high/low ROI and assign to Human or AI), "
                    "'importance' (urgent|high|normal)."
                )

            local_mems = []
            
            # --- LOCAL MESH EXECUTION (WITH CIRCUIT BREAKER ROUTING) ---
            import psutil
            mem = psutil.virtual_memory()
            free_ram_gb = mem.available / (1024**3)
            
            target_url = "http://127.0.0.1:8081/v1/chat/completions"
            if free_ram_gb < 10.5:
                log.warning(f"⚠️ RAM CIRCUIT BREAKER: Free RAM ({free_ram_gb:.1f} GB) too close to Sanctuary limit. Routing to L2 Mesh Node (MacBook Pro).")
                target_url = "http://100.103.212.21:8081/v1/chat/completions"
                
            try:
                import httpx
                local_payload = {
                    "messages": [
                        {"role": "system", "content": "You are an ROI Analysis AI. Output a strict JSON array of objects with keys: 'category', 'content' (Prefixed with [ROI: XX/100]), 'context', 'importance'. Return nothing but JSON. Strip ```json"},
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
                            local_mems = json.loads(json_match.group(0))
                            import subprocess
                            for tm in local_mems:
                                if "ROI:" in tm.get("content", ""):
                                    try:
                                        roi_val = int(tm["content"].split("ROI:")[1].split("/")[0].strip())
                                        if roi_val >= 90:
                                            subprocess.Popen(["python3", "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py", "0", tm["content"]], start_new_session=True)
                                    except: pass
            except Exception as local_e:
                log.warning(f"Local mesh failed on {target_url}: {local_e}")
                    
            winning_mems = local_mems
            
            # --- SAVE WINNING MEMORIES ---"""

content = re.sub(regex_pattern, replacement, content, flags=re.DOTALL)

with open(file_path, "w") as f:
    f.write(content)

print("Patch applied to enforce Local AI Mesh!")
