import os
import glob
import re

SCREEN_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/screens"
VIEW_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/views"

os.makedirs(VIEW_DIR, exist_ok=True)

# 1. Convert Screen classes to Container classes
def convert_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    view_filename = filename.replace("_screen.py", "_view.py")
    
    # Imports
    content = content.replace("from textual.screen import Screen", "from textual.containers import Container")
    
    # Class signature
    content = re.sub(r"class (\w+)Screen\(Screen\):", r"class \1View(Container):", content)
    
    # Remove yields of layout components that are now app-level
    content = re.sub(r"^\s*yield Header\(\).*?\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^\s*yield Footer\(\).*?\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^\s*yield PinnedTabNavBar\(.*?\).*?\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^\s*yield DockedShortcutsLegend\(.*?\).*?\n", "", content, flags=re.MULTILINE)
    
    # Fix self.app.push_screen to self.app.switch_tab or similar if present
    content = re.sub(r"self\.app\.push_screen\((.*?)\)", r"self.app.switch_tab(\1)", content)
    
    out_path = os.path.join(VIEW_DIR, view_filename)
    with open(out_path, "w") as f:
        f.write(content)
    print(f"Refactored {filename} -> {view_filename}")

for py_file in glob.glob(os.path.join(SCREEN_DIR, "*_screen.py")):
    convert_file(py_file)
