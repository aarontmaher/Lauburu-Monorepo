import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Update init_db
old_init_db = """def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS life_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            content TEXT,
            task_type TEXT,
            roi_score INTEGER,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()"""

new_init_db = """def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS life_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            content TEXT,
            task_type TEXT,
            roi_score INTEGER,
            status TEXT DEFAULT 'pending'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS optimization_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            abstract_logic TEXT,
            status TEXT DEFAULT 'pending',
            gemini_suggestion TEXT
        )
    ''')
    conn.commit()
    conn.close()"""
content = content.replace(old_init_db, new_init_db)

# 2. Update the prompt to look for optimizations
old_prompt = """Respond ONLY with a valid JSON array of objects, where each object has:
- "task_type": "Human Activity" or "AI Swarm"
- "content": A summary of what is happening or the command to run.
- "roi_score": 0-100 (Give 90+ ONLY if this is a highly valuable, automatable task that the AI should take over immediately)."""

new_prompt = """Respond ONLY with a valid JSON array of objects, where each object has:
- "task_type": "Human Activity" or "AI Swarm"
- "content": A summary of what is happening or the command to run.
- "roi_score": 0-100 (Give 90+ ONLY if this is a highly valuable, automatable task that the AI should take over immediately).
- "abstract_optimization": If this workflow is repetitive or unoptimized, provide a completely anonymized, abstract description of the logic/code to be optimized. Otherwise, output null."""
content = content.replace(old_prompt, new_prompt)

# 3. Update the insert loop
old_insert = """                    cursor.execute(
                        "INSERT INTO life_memories (timestamp, content, task_type, roi_score, status) VALUES (?, ?, ?, ?, ?)",
                        (timestamp, tm["content"], tm["task_type"], roi, "pending")
                    )"""
new_insert = """                    cursor.execute(
                        "INSERT INTO life_memories (timestamp, content, task_type, roi_score, status) VALUES (?, ?, ?, ?, ?)",
                        (timestamp, tm["content"], tm["task_type"], roi, "pending")
                    )
                    
                    abstract_opt = tm.get("abstract_optimization")
                    if abstract_opt and isinstance(abstract_opt, str):
                        cursor.execute(
                            "INSERT INTO optimization_queue (timestamp, abstract_logic, status) VALUES (?, ?, ?)",
                            (timestamp, abstract_opt, "pending")
                        )
                        logging.info(f"🧩 Queued Abstract Optimization: {abstract_opt[:50]}...")"""
content = content.replace(old_insert, new_insert)

# 4. Update run_teacher_loop to process the queue
old_teacher = """                response = model.generate_content(prompt)
                logging.info(f"Gemini Teacher Auto-Tuned Prompt: {response.text[:100]}...")"""
new_teacher = """                response = model.generate_content(prompt)
                logging.info(f"Gemini Teacher Auto-Tuned Prompt: {response.text[:100]}...")
                
                # Process the Abstract Optimization Queue
                cursor.execute("SELECT id, abstract_logic FROM optimization_queue WHERE status = 'pending' LIMIT 5")
                pending_opts = cursor.fetchall()
                for opt_id, logic in pending_opts:
                    opt_prompt = f"As the Gemini 3.8 Flash Optimization Teacher, review this anonymized abstract logic and provide a clean, highly optimized refactor (e.g. Python, Rust, or Bash):\\n{logic}"
                    opt_resp = model.generate_content(opt_prompt)
                    suggestion = opt_resp.text
                    cursor.execute("UPDATE optimization_queue SET status = 'completed', gemini_suggestion = ? WHERE id = ?", (suggestion, opt_id))
                    logging.info(f"💡 Gemini provided optimization for queue ID {opt_id}")
                
                conn.commit()"""
content = content.replace(old_teacher, new_teacher)

with open(file_path, "w") as f:
    f.write(content)
