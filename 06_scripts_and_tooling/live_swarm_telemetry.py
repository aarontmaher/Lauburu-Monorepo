# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich",
# ]
# ///
import time
import os
import subprocess
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from datetime import datetime

console = Console()

SWARM_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/orchestrator_tui_specialist"
DOWNLOAD_LOG = "/tmp/qwen_download.log"

def get_swarm_progress():
    try:
        with open(os.path.join(SWARM_DIR, "progress.md"), "r") as f:
            content = f.read()
            # Extract just the Checklist part
            if "## Checklist" in content:
                return content.split("## Checklist")[1].strip()
            return content
    except:
        return "Progress file not found or inaccessible yet."

def get_download_status():
    try:
        # Use ssh to check the L2 download log
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=2", "aaronmaher@169.254.187.138", "tail -c 200 /tmp/qwen_download.log | tr '\\r' '\\n' | tail -n 1"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "Download daemon active... fetching stats..."
    except:
        return "SSH connection to L2 pending..."

def get_git_diff():
    try:
        result = subprocess.run(
            ["git", "-C", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "status", "--short"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "No pending uncommitted changes in root repo."
    except:
        return "Checking git status..."

def generate_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="swarm", ratio=2),
        Layout(name="side", ratio=1)
    )
    layout["side"].split_column(
        Layout(name="download"),
        Layout(name="git")
    )

    header_text = Text(f"📡 LAUBURU AI MESH: LIVE TELEMETRY & SWARM OVERSIGHT 📡 - {datetime.now().strftime('%H:%M:%S')}", style="bold cyan", justify="center")
    layout["header"].update(Panel(header_text, style="blue"))

    swarm_md = Markdown(get_swarm_progress())
    layout["swarm"].update(Panel(swarm_md, title="[bold green]Swarm Progress (TUI Specialist Orchestrator)[/]", border_style="green"))

    download_text = Text(get_download_status(), style="yellow")
    layout["download"].update(Panel(download_text, title="[bold yellow]Qwen 3.8 GGUF Download (L2 Vault)[/]", border_style="yellow"))

    git_text = Text(get_git_diff(), style="magenta")
    layout["git"].update(Panel(git_text, title="[bold magenta]Git Changed Files[/]", border_style="magenta"))

    return layout

if __name__ == "__main__":
    with Live(generate_layout(), refresh_per_second=1, screen=True) as live:
        try:
            while True:
                time.sleep(2)
                live.update(generate_layout())
        except KeyboardInterrupt:
            pass
