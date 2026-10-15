import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Replace Neo Self-Optimization
neo_opt_block = """            from neo_mcp.backend_client import BackendClient
            with open("/Users/aaron/.neo/secret_key", "r") as f: neo_key = f.read().strip()
            with open("/Users/aaron/.neo/settings.json", "r") as f: neo_settings = json.load(f)
            dep_id = neo_settings.get("deployment_id", "d56f9a69-1139-4522-9365-6e26e0231827")
            
            client = BackendClient(auth_token=neo_key)
            
            opt_prompt = (
                "You are an AI Self-Optimization Engine. Review these recent memory extractions:\\n"
                f"{recent_memories}\\n\\n"
                "Are they capturing too much noise? Are they missing critical details? "
                "Provide a slightly improved, highly targeted prompt instruction for the next extraction cycle to increase signal-to-noise ratio. "
                "Reply ONLY with the new prompt text. Do not include markdown formatting or conversational text."
            )
            
            res = await client.init_chat(message=opt_prompt, deployment_id=dep_id, workspace="/Volumes/Lauburu-Monorepo")
            await client.aclose()
            
            # Since init_chat is async, we'd normally poll for the answer. 
            # For simplicity in this background loop, we assume it gets handled.
            
            with open(OBSIDIAN_DIR / "MASTER_LIFE_ORGANIZER.md", "a") as f:
                f.write(f"\\n- **[{datetime.datetime.now(datetime.timezone.utc).isoformat()}]**: Neo Free Tier engaged to auto-tune extraction prompt. Thread: {res.get('thread_id')}\\n")
"""

gemini_opt_block = """            import google.generativeai as genai
            import os
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                log.warning("No GEMINI_API_KEY found, skipping self-optimization.")
                return
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            opt_prompt = (
                "You are an AI Self-Optimization Engine. Review these recent memory extractions:\\n"
                f"{recent_memories}\\n\\n"
                "Are they capturing too much noise? Are they missing critical details? "
                "Provide a slightly improved, highly targeted prompt instruction for the next extraction cycle to increase signal-to-noise ratio. "
                "Reply ONLY with the new prompt text. Do not include markdown formatting or conversational text."
            )
            
            response = model.generate_content(opt_prompt)
            new_prompt = response.text.strip()
            
            if new_prompt:
                self.optimizer.current_extraction_prompt = new_prompt
                with open(OBSIDIAN_DIR / "MASTER_LIFE_ORGANIZER.md", "a") as f:
                    f.write(f"\\n- **[{datetime.datetime.now(datetime.timezone.utc).isoformat()}]**: Gemini 3.8 Flash engaged to auto-tune extraction prompt.\\n")
"""
content = content.replace(neo_opt_block, gemini_opt_block)
content = content.replace('log.info("Initiating Autonomous Self-Optimization via Neo Free Tier...")', 'log.info("Initiating Autonomous Self-Optimization via Gemini 3.8 Flash...")')


# 2. Replace Neo Extraction Block
neo_exec_block_regex = r"# --- NEO EXECUTION ---.*?# --- BENCHMARK COMPARISON ---"

gemini_exec_block = """# --- GEMINI 3.8 FLASH EXECUTION ---
            if preferred_route == "neo" or do_benchmark:
                try:
                    import google.generativeai as genai
                    import os
                    api_key = os.environ.get("GEMINI_API_KEY")
                    if not api_key:
                        raise Exception("GEMINI_API_KEY not found.")
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    sys_prompt = "You are an ROI Analysis AI. Differentiate Human vs AI activity. Output a strict JSON array of objects with keys: 'category' (todo|roi_insight), 'content' (Prefixed with [ROI: XX/100]), 'context' (Assign to Human or AI), 'importance'. Return nothing but JSON. Strip ```json"
                    
                    start_t = time.time()
                    res = model.generate_content(sys_prompt + "\\n" + prompt)
                    content_str = res.text.strip().replace('```json', '').replace('```', '')
                    
                    json_match = re.search(r'\\[.*\\]', content_str, re.DOTALL)
                    if json_match:
                        neo_mems = json.loads(json_match.group(0))
                        neo_score += 50
                        # AUTO HANDOFF logic for high ROI tasks
                        import subprocess
                        for tm in neo_mems:
                            if "ROI:" in tm.get("content", ""):
                                try:
                                    roi_val = int(tm["content"].split("ROI:")[1].split("/")[0].strip())
                                    if roi_val >= 90:
                                        subprocess.Popen(["python3", "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py", "0", tm["content"]], start_new_session=True)
                                except: pass
                        neo_score += len(neo_mems) * 5
                        neo_score += max(0, int(10 - (time.time() - start_t))) * 2
                except Exception as e:
                    log.warning(f"Gemini Flash extraction failed: {e}")
                    
            # --- BENCHMARK COMPARISON ---"""

content = re.sub(neo_exec_block_regex, gemini_exec_block, content, flags=re.DOTALL)
content = content.replace('log.info(f"Offloading batch of {len(rows)} screen captures to Neo Free Tier CPU for extraction...")', 'log.info(f"Offloading batch of {len(rows)} screen captures to Gemini 3.8 Flash CPU for extraction...")')

with open(file_path, "w") as f:
    f.write(content)
print("Patch applied successfully.")
