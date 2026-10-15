import os
import glob
import time
import json
import asyncio
from datetime import datetime
from collections import deque

from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

# Transcripts location
BRAIN_DIR = "/Users/aaron/.gemini/antigravity/brain"

class UnifiedSwarmTerminal:
    def __init__(self):
        self.layout = Layout()
        self.log_stream = deque(maxlen=20)
        self.pending_questions = deque(maxlen=10)
        self.speculative_summary = "Initializing Speculative AI Swarm Observer..."
        self.last_positions = {}
        
        self.setup_layout()

    def setup_layout(self):
        self.layout.split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        self.layout["right"].split_column(
            Layout(name="top_right", ratio=1),
            Layout(name="bottom_right", ratio=2)
        )

    def tail_transcripts(self):
        transcript_files = glob.glob(f"{BRAIN_DIR}/*/.system_generated/logs/transcript.jsonl")
        new_content = False
        
        for file in transcript_files:
            if file not in self.last_positions:
                # Initialize to end of file to only catch new things
                self.last_positions[file] = os.path.getsize(file)
                continue
                
            current_size = os.path.getsize(file)
            if current_size > self.last_positions[file]:
                with open(file, 'r') as f:
                    f.seek(self.last_positions[file])
                    lines = f.readlines()
                    self.last_positions[file] = current_size
                    
                    for line in lines:
                        try:
                            data = json.loads(line)
                            if 'content' in data and data.get('source') != 'SYSTEM':
                                msg = data['content'][:100].replace('\n', ' ')
                                agent = data.get('source', 'Unknown')
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                
                                formatted_log = f"[{timestamp}] [{agent}]: {msg}..."
                                self.log_stream.appendleft(formatted_log)
                                new_content = True
                                
                                # Detect questions or blockers for the backlog
                                if '?' in msg or 'USER_INPUT' in msg or 'error' in msg.lower():
                                    self.pending_questions.appendleft(f"[{agent}] needs input: {msg}")
                                    
                        except json.JSONDecodeError:
                            continue
                            
        return new_content

    def generate_speculative_summary(self):
        # In production, this would make an async HTTP call to Qwen 3.8 Max (Port 8082)
        # feeding it self.log_stream to get a live summarization.
        if len(self.log_stream) > 0:
            self.speculative_summary = (
                f"Speculative Swarm Assessment (Live):\n"
                f"The swarm is actively executing {len(self.log_stream)} concurrent threads. "
                f"Agents are focusing on code generation and file indexing. "
                f"Blockers detected: {len(self.pending_questions)} pending inputs."
            )

    def generate_ui(self):
        # Panel 1: Live Logs
        log_text = Text("\n".join(self.log_stream), style="green")
        log_panel = Panel(log_text, title="🌐 Unified Swarm Multiplexer Stream", border_style="cyan")
        
        # Panel 2: Speculative Summary
        summary_panel = Panel(Text(self.speculative_summary, style="bold magenta"), title="🧠 Speculative AI Real-Time Synthesis", border_style="magenta")
        
        # Panel 3: Action Backlog
        backlog_text = Text("\n".join(self.pending_questions) if self.pending_questions else "No pending questions. Swarm is autonomous.", style="yellow")
        input_prompt = Text("\n\n> Type your response here (Press Enter to dispatch to all pending):", style="bold white")
        backlog_group = Group(backlog_text, input_prompt)
        backlog_panel = Panel(backlog_group, title="📥 AI Request Backlog & Single-Frame Dispatch", border_style="yellow")

        self.layout["left"].update(log_panel)
        self.layout["top_right"].update(summary_panel)
        self.layout["bottom_right"].update(backlog_panel)
        
        return self.layout

async def main():
    terminal = UnifiedSwarmTerminal()
    with Live(terminal.generate_ui(), refresh_per_second=4) as live:
        while True:
            updated = terminal.tail_transcripts()
            if updated:
                terminal.generate_speculative_summary()
            live.update(terminal.generate_ui())
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
