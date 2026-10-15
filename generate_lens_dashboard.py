import nbformat as nbf

nb = nbf.v4.new_notebook()

nb['cells'] = [
    nbf.v4.new_markdown_cell("""# 👁️ Sovereign Screen Lens Global Orchestrator Dashboard
Governed by **Notebook Specialist** and **Screen Lens Sovereign** skills.
Displays real-time OCR telemetry, MJPEG HUD, and integrated Lens apps (Life Companion)."""),
    
    nbf.v4.new_code_cell("""import sys, os
for path in ["/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "/Users/aaronmaher/teamwork_projects"]:
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

import requests
import ipywidgets as widgets
from IPython.display import display, HTML
import time"""),
    
    nbf.v4.new_code_cell("""# ==============================================================================
# CSS Styling (Dark/Glassmorphic)
# ==============================================================================
display(HTML(\"\"\"
<style>
  html, body, .jp-Notebook, div.cell, div#notebook, .rendered_html {
    background-color: #020617 !important;
    color: #f8fafc !important;
    font-family: 'Inter', sans-serif !important;
  }
  .jupyter-widgets.p-TabBar {
    background: #090d16 !important;
    border-bottom: 1px solid #1e293b !important;
  }
  .p-TabBar-tab {
    background: #0f172a !important;
    color: #94a3b8 !important;
    border: 1px solid #1e293b !important;
    border-bottom: none !important;
    border-radius: 6px 6px 0 0 !important;
  }
  .p-TabBar-tab.p-mod-current {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border-top: 2px solid #3b82f6 !important;
  }
</style>
\"\"\"))"""),
    
    nbf.v4.new_code_cell("""# ==============================================================================
# Iframe Generators for Lens Apps
# ==============================================================================
def create_iframe_tab(url, height=800):
    out = widgets.Output()
    iframe_html = f\"\"\"
    <div style="height: {height}px; width: 100%; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; background: #020617;">
        <iframe src="{url}" width="100%" height="100%" frameborder="0" style="background: transparent;"></iframe>
    </div>
    \"\"\"
    with out:
        display(HTML(iframe_html))
    return out

tab_life_companion = create_iframe_tab("http://127.0.0.1:3036")
tab_mjpeg_hud = create_iframe_tab("http://127.0.0.1:4003")"""),

    nbf.v4.new_code_cell("""# ==============================================================================
# Orchestrator Telemetry (Port 3037)
# ==============================================================================
out_telemetry = widgets.Output()
with out_telemetry:
    display(HTML("<h3 style='color: #38bdf8;'>Global Orchestrator State (Port 3037)</h3>"))
    try:
        response = requests.get('http://127.0.0.1:3037/api/orchestrator/state', timeout=2)
        import json
        display(HTML(f"<pre style='color: #a3e635; font-size: 14px;'>{json.dumps(response.json(), indent=2)}</pre>"))
    except Exception as e:
        display(HTML(f"<p style='color: #ef4444;'>Orchestrator unreachable: {e}</p>"))"""),
        
    nbf.v4.new_code_cell("""# ==============================================================================
# Global Orchestrator Master Tab Assembly
# ==============================================================================
master_tab = widgets.Tab(children=[
    out_telemetry,
    tab_life_companion,
    tab_mjpeg_hud,
])

master_tab.set_title(0, "🧠 Global Orchestrator")
master_tab.set_title(1, "📓 Life Companion")
master_tab.set_title(2, "👁️ MJPEG HUD")

display(master_tab)""")
]

nbf.write(nb, '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/09_sovereign_screen_lens_dashboard.ipynb')
print("Notebook updated.")
