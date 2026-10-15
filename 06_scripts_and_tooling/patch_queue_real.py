import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Update _init_db
old_init_db = """            c.execute('''CREATE TABLE IF NOT EXISTS life_memories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            category TEXT,
                            content TEXT,
                            context TEXT,
                            importance TEXT
                         )''')"""

new_init_db = """            c.execute('''CREATE TABLE IF NOT EXISTS life_memories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            category TEXT,
                            content TEXT,
                            context TEXT,
                            importance TEXT
                         )''')
            c.execute('''CREATE TABLE IF NOT EXISTS optimization_queue (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp_iso TEXT,
                            abstract_logic TEXT,
                            status TEXT DEFAULT 'pending',
                            gemini_suggestion TEXT
                         )''')"""
content = content.replace(old_init_db, new_init_db)

# 2. Update CompanionSelfOptimizer init prompt
old_prompt = """Respond ONLY with a valid JSON array of objects. Each object must have:
- "category": e.g., "roi_insight", "task", "observation"
- "content": A summary of what is happening or the command to run. MUST include "ROI: [0-100]/100" if actionable.
- "context": Associated window/app info.
- "importance": "high", "normal", "low". Give "high" and ROI 90+ ONLY if this is a highly valuable, automatable task."""

new_prompt = """Respond ONLY with a valid JSON array of objects. Each object must have:
- "category": e.g., "roi_insight", "task", "observation"
- "content": A summary of what is happening or the command to run. MUST include "ROI: [0-100]/100" if actionable.
- "context": Associated window/app info.
- "importance": "high", "normal", "low". Give "high" and ROI 90+ ONLY if this is a highly valuable, automatable task.
- "abstract_optimization": If this workflow is repetitive or unoptimized, provide a completely anonymized, abstract description of the logic/code to be optimized. Otherwise, output null."""
content = content.replace(old_prompt, new_prompt)

# 3. Update the insert loop
old_insert = """                    c.execute("INSERT INTO life_memories (timestamp_iso, category, content, context, importance) VALUES (?, ?, ?, ?, ?)",
                              (datetime.datetime.now(datetime.timezone.utc).isoformat(), cat, cont, ctx, imp))"""
new_insert = """                    c.execute("INSERT INTO life_memories (timestamp_iso, category, content, context, importance) VALUES (?, ?, ?, ?, ?)",
                              (datetime.datetime.now(datetime.timezone.utc).isoformat(), cat, cont, ctx, imp))
                    abstract_opt = mem.get("abstract_optimization")
                    if abstract_opt and isinstance(abstract_opt, str):
                        c.execute("INSERT INTO optimization_queue (timestamp_iso, abstract_logic, status) VALUES (?, ?, ?)",
                                  (datetime.datetime.now(datetime.timezone.utc).isoformat(), abstract_opt, "pending"))"""
content = content.replace(old_insert, new_insert)

# 4. Update Teacher Loop
old_teacher = """                response = model.generate_content(prompt)
                logging.info(f"🎓 Gemini Teacher Auto-Tuned Prompt: {response.text[:100]}...")"""
new_teacher = """                response = model.generate_content(prompt)
                logging.info(f"🎓 Gemini Teacher Auto-Tuned Prompt: {response.text[:100]}...")
                
                # Process the Abstract Optimization Queue
                with db_lock:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, abstract_logic FROM optimization_queue WHERE status = 'pending' LIMIT 5")
                    pending_opts = cursor.fetchall()
                    for opt_id, logic in pending_opts:
                        opt_prompt = f"As the Gemini 3.8 Flash Optimization Teacher, review this anonymized abstract logic and provide a clean, highly optimized refactor (e.g. Python, Rust, or Bash):\\n{logic}"
                        opt_resp = model.generate_content(opt_prompt)
                        suggestion = opt_resp.text
                        cursor.execute("UPDATE optimization_queue SET status = 'completed', gemini_suggestion = ? WHERE id = ?", (suggestion, opt_id))
                        logging.info(f"💡 Gemini provided optimization for queue ID {opt_id}")
                    conn.commit()
                    conn.close()"""
content = content.replace(old_teacher, new_teacher)

with open(file_path, "w") as f:
    f.write(content)

