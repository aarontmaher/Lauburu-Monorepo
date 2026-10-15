import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace the Flask App initialization to use templates and import config
old_flask_init = """app = Flask(__name__)
db_lock = threading.Lock()"""

new_flask_init = """from config_manager import load_config, save_config
import os
from flask import render_template, request, redirect, url_for

app = Flask(__name__, template_folder="templates")
db_lock = threading.Lock()"""
if old_flask_init in content:
    content = content.replace(old_flask_init, new_flask_init)
else:
    print("WARNING: Flask init not found.")

# Replace the dashboard route completely
dashboard_start = "@app.route('/')"
dashboard_end_marker = "return html"

import re
pattern = re.compile(r"@app\.route\('/'\).*?return html", re.DOTALL)

new_dashboard = """@app.route('/')
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
"""

content = pattern.sub(new_dashboard, content)

with open(file_path, "w") as f:
    f.write(content)
