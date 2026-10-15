#!/usr/bin/env python3
import os
import re

DESIGN_FILE = "DESIGN.MD"
OUTPUT_FILE = "scaffolded_app.py"

def sanitize_identifier(name):
    sanitized = re.sub(r'\W|^(?=\d)', '', name)
    return sanitized if sanitized else "DefaultName"

def parse_design_md(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        content = f.read()

    app_name = "GeneratedApp"
    name_match = re.search(r"# App Name:\s*(.*)", content)
    if name_match:
        app_name = sanitize_identifier(name_match.group(1))

    screens = []
    screen_blocks = re.findall(r"### Screen:\s*`?([^`\n]+)`?(.*?)(?=### Screen|\Z)", content, re.DOTALL)
    for screen_name, screen_body in screen_blocks:
        screens.append({
            "name": sanitize_identifier(screen_name.strip()),
            "details": screen_body.strip()
        })

    return {"app_name": app_name, "screens": screens}

def generate_textual_app(design_data):
    if not design_data:
        return ""

    app_name = design_data["app_name"]
    screens = design_data["screens"]

    imports = """import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Label
from textual.screen import Screen
"""
    
    screen_classes = ""
    for screen in screens:
        class_name = screen["name"]
        screen_classes += f"""
class {class_name}(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Static(f"--- Scaffolded {class_name} ---", classes="screen-title"),
                Static("Content generated from DESIGN.MD specifications.", classes="screen-content")
            )
        )
        yield Footer()
"""
    
    app_class = f"""
class {app_name}App(App):
    CSS = \"\"\"
    Screen {{
        align: center middle;
    }}
    .screen-title {{
        text-align: center;
        text-style: bold;
        color: $accent;
    }}
    .screen-content {{
        text-align: center;
        margin-top: 2;
    }}
    \"\"\"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def on_mount(self) -> None:
"""
    if screens:
        app_class += f"        self.push_screen({screens[0]['name']}())"
    else:
        app_class += "        pass"

    run_block = f"""

if __name__ == "__main__":
    app = {app_name}App()
    app.run()
"""

    return imports + screen_classes + app_class + run_block

def main():
    if not os.path.exists(DESIGN_FILE):
        print(f"File {DESIGN_FILE} not found.")
        return
        
    design_data = parse_design_md(DESIGN_FILE)
    if not design_data:
        return
        
    code = generate_textual_app(design_data)
    with open(OUTPUT_FILE, "w") as f:
        f.write(code)
    print(f"Successfully scaffolded {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
