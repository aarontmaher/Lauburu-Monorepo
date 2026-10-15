import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/notebooks/generate_glassmorphic_master_studio.py"
with open(file_path, "r") as f:
    content = f.read()

old_tab_titles = "titles = ['0. Main Dashboard', '1. Swarm State', '2. Live Network & Telemetry', '3. Model Routing', '4. Security & Audit', '5. Task Backlog', '6. Genetic UI', '7. Screen Lens Vision', '8. AI Debate Matrix', '9. Life Companion']"
new_tab_titles = "titles = ['0. Main Dashboard', '1. Swarm State', '2. Live Network & Telemetry', '3. Model Routing', '4. Security & Audit', '5. Task Backlog', '6. Genetic UI', '7. Screen Lens Vision', '8. AI Debate Matrix', '9. Life Companion', '10. Background Headless Actions']"
content = content.replace(old_tab_titles, new_tab_titles)

old_tabs = """# 10. Life Companion
companion_html = widgets.HTML(
    value="<iframe src='http://127.0.0.1:3036' width='100%' height='800px' style='border:none; border-radius:12px;'></iframe>"
)

tabs.children = [
    main_dashboard, swarm_html, network_html, model_html, security_html, task_html,
    genetic_html, lens_html, debate_html, companion_html
]"""

new_tabs = """# 10. Life Companion
companion_html = widgets.HTML(
    value="<iframe src='http://127.0.0.1:3036' width='100%' height='800px' style='border:none; border-radius:12px;'></iframe>"
)

# 11. Background Headless Actions
headless_actions_html = widgets.HTML(
    value="\"\"\"
    <div style='padding: 20px; color: white;'>
        <h2>🤖 Autonomous Background Actions</h2>
        <p>Live visualization of the headless browser and background app targeting actions executed by the AI Handoff Worker.</p>
        <div style='background: #1e1e1e; padding: 15px; border-radius: 8px; border: 1px solid #00ffcc;'>
            <h3>🔴 LIVE STREAM: Headless Playwright Sandbox</h3>
            <p><i>Streaming /Volumes/Lauburu-Monorepo/01_apps/screen_lens/data/headless_recording.mp4...</i></p>
            <video width="100%" height="500" controls autoplay loop>
              <source src="/files/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/data/headless_recording.mp4" type="video/mp4">
              Your browser does not support the video tag.
            </video>
        </div>
    </div>
    \"\"\""
)

tabs.children = [
    main_dashboard, swarm_html, network_html, model_html, security_html, task_html,
    genetic_html, lens_html, debate_html, companion_html, headless_actions_html
]"""

content = content.replace(old_tabs, new_tabs)

with open(file_path, "w") as f:
    f.write(content)

