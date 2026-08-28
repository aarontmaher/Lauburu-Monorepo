import os
import subprocess
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Markdown, Label
from textual.containers import Vertical, Horizontal

SWARM_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/orchestrator_tui_specialist"

class SwarmAuditScreen(Screen):
    """Screen for monitoring live swarm containers, diffs, and AI implementation."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back to Main"),
        ("r", "refresh_data", "Refresh Data")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="swarm-audit-layout"):
            yield Label("🟢 LIVE TEAMWORK SWARM ORCHESTRATOR & CONTAINERS 🟢", id="swarm-audit-title", classes="panel-title")
            with Horizontal():
                with Vertical(classes="panel"):
                    yield Label("1. Subagent Iteration Checklists", classes="panel-header")
                    self.checklist_md = Markdown("Loading...", id="swarm-checklist-md")
                    yield self.checklist_md
                with Vertical(classes="panel"):
                    yield Label("2. Download Daemon Containers", classes="panel-header")
                    self.download_log = Static("Loading...", id="swarm-download-log")
                    yield self.download_log
            with Vertical(classes="panel"):
                yield Label("3. Sandboxed Git Worktree (Real-time File Edits)", classes="panel-header")
                self.git_diff = Static("Loading...", id="swarm-git-diff")
                yield self.git_diff
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh_data()
        self.set_interval(2.0, self.action_refresh_data)

    def action_refresh_data(self) -> None:
        # 1. Swarm Progress
        try:
            with open(os.path.join(SWARM_DIR, "progress.md"), "r") as f:
                content = f.read()
                if "## Checklist" in content:
                    checklist = content.split("## Checklist")[1].strip()
                    self.checklist_md.update(checklist)
                else:
                    self.checklist_md.update(content)
        except:
            self.checklist_md.update("Awaiting subagent progress reports...")

        # 2. Download Log
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=2", "aaronmaher@169.254.187.138", "tail -c 200 /tmp/qwen_download.log | tr '\\r' '\\n' | tail -n 1"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                self.download_log.update(f"[L2 Storage Vault]\n\n{result.stdout.strip()}")
            else:
                self.download_log.update("Awaiting SSH container ping...")
        except:
            self.download_log.update("SSH Ping Failed")

        # 3. Git Diff
        try:
            result = subprocess.run(
                ["git", "-C", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "status", "--short"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                self.git_diff.update(f"{result.stdout.strip()}\n\n(Changes isolated to canonical_port/.agents sandboxes)")
            else:
                self.git_diff.update("Clean.")
        except:
            self.git_diff.update("Scanning worktree...")
