import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/notebooks/generate_glassmorphic_master_studio.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Update Header docs
content = content.replace(
    "- Tab 8: 📊 9. Real-Time Monorepo AST & Analytics Console (Live AST Scan & LOC Breakdown)",
    "- Tab 8: 📊 9. Real-Time Monorepo AST & Analytics Console (Live AST Scan & LOC Breakdown)\\n   - Tab 9: 📓 10. Life Companion (Project Management & Autonomous Logging)"
)

# 2. Add `create_life_companion_tab` function just before `master_tab = widgets.Tab`
life_companion_func = """def create_life_companion_tab():
    out = widgets.Output()
    iframe_html = '''
    <div style="height: 800px; width: 100%; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; background: #020617;">
        <iframe src="http://127.0.0.1:3036" width="100%" height="100%" frameborder="0" style="background: transparent;"></iframe>
    </div>
    '''
    with out:
        display(HTML(iframe_html))
    return out

tab_life_companion = create_life_companion_tab()
"""

# Find `tab_ast = create_ast_tab()` and insert the new tab after it
content = content.replace(
    "tab_ast = create_ast_tab()",
    "tab_ast = create_ast_tab()\\n" + life_companion_func
)

# 3. Add to widgets.Tab(children=[...])
content = content.replace(
    "tab_ast\n])",
    "tab_ast,\n    tab_life_companion\n])"
)

# 4. Set title
content = content.replace(
    'master_tab.set_title(8, "📊 9. Monorepo AST")',
    'master_tab.set_title(8, "📊 9. Monorepo AST")\\nmaster_tab.set_title(9, "📓 10. Life Companion")'
)

# 5. Fix the markdown list of tabs at the end of the file
content = content.replace(
    "- **Tab 8: 📊 9. Real-Time Monorepo AST & Analytics Console**",
    "- **Tab 8: 📊 9. Real-Time Monorepo AST & Analytics Console**\\n- **Tab 9: 📓 10. Life Companion (Project & Time Tracker)**"
)

with open(file_path, "w") as f:
    f.write(content)
print("Voila Studio patched successfully.")
