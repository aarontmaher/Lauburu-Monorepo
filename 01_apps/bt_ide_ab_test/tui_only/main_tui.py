import urllib.request
import json
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TextArea, RichLog, Input, Label
from textual.containers import Horizontal, Vertical
from textual import work

class LauburuAgentIDE(App):
    """
    Stateful Agent-First IDE Prototype.
    Maintains a continuous conversational context loop with the Sovereign Planner.
    """
    CSS = """
    Screen { layout: horizontal; }
    #left_pane { width: 40%; border: solid green; }
    #center_pane { width: 40%; border: solid cyan; }
    #right_pane { width: 20%; border: solid yellow; }
    Input { dock: bottom; }
    RichLog { height: 1fr; }
    TextArea { height: 1fr; }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 🧠 Initialize stateful conversation history with the Planner Persona
        self.chat_history = [
            {
                "role": "system", 
                "content": "You are the Lauburu Lead Architect and Planning Model. You engage in interactive, stateful chat with the user to plan features, request clarification, and architect solutions before delegating the raw syntax to the Coder model. You have access to the RAG Vector DB conceptually."
            }
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            # Left: Interactive Planner Chat
            with Vertical(id="left_pane"):
                yield Label("🤖 Interactive Sovereign Planner", classes="pane_title")
                yield RichLog(id="chat_log", markup=True)
                yield Input(placeholder="Discuss architecture or features... (CMD+K)", id="chat_input")
            
            # Center: Code / Diff Viewer
            with Vertical(id="center_pane"):
                yield Label("📝 Active Blueprint / Code Diff", classes="pane_title")
                yield TextArea(text="# Awaiting Architecture Plan...\n", language="python", id="code_area")
            
            # Right: Lens & Mesh Telemetry
            with Vertical(id="right_pane"):
                yield Label("👁️ Lens VLA Telemetry", classes="pane_title")
                yield RichLog(id="mesh_log", markup=True)
                
        yield Footer()

    def on_mount(self) -> None:
        mesh = self.query_one("#mesh_log", RichLog)
        chat = self.query_one("#chat_log", RichLog)
        mesh.write("[bold green]Gateway:[/bold green] localhost:8085")
        mesh.write("[bold green]Router:[/bold green] MCTS Planning Engine")
        mesh.write("[bold yellow]Context State:[/bold yellow] Stateful Loop Active")
        chat.write("[bold magenta]Lead Architect Online.[/bold magenta]")
        chat.write("Memory initialized. Let's plan the architecture.")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value
        if not user_text.strip():
            return
        event.input.value = ""
        
        chat = self.query_one("#chat_log", RichLog)
        chat.write(f"\n[bold blue]You:[/bold blue] {user_text}")
        chat.write("[dim]Synthesizing conversational context...[/dim]")
        
        # 🧠 Append the user's input to the ongoing stateful history
        self.chat_history.append({"role": "user", "content": user_text})
        
        # Fire async worker to prevent UI freeze during LLM generation
        self.fetch_agent_response()

    @work(thread=True)
    def fetch_agent_response(self):
        req_data = json.dumps({
            "model": "dynamic-mcts-chat",
            "messages": self.chat_history
        }).encode('utf-8')
        
        req = urllib.request.Request(
            "http://localhost:8085/v1/chat/completions",
            data=req_data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            response = urllib.request.urlopen(req, timeout=30)
            res_data = json.loads(response.read().decode('utf-8'))
            reply = res_data["choices"][0]["message"]["content"]
            
            # 🧠 Append the Planner's reply to the ongoing history
            self.chat_history.append({"role": "assistant", "content": reply})
            
            # Update UI safely from the worker thread
            self.call_from_thread(self.update_ui_with_reply, reply)
        except Exception as e:
            self.call_from_thread(self.update_ui_with_error, str(e))

    def update_ui_with_reply(self, reply: str):
        chat = self.query_one("#chat_log", RichLog)
        code_area = self.query_one("#code_area", TextArea)
        mesh = self.query_one("#mesh_log", RichLog)
        
        chat.write(f"[bold magenta]Planner:[/bold magenta] {reply}")
        # The center pane acts as a scratchpad for the planner's thoughts/code
        code_area.text = f"# Planner Context Size: {len(self.chat_history)} messages in memory\n\n# {reply}"
        mesh.write(f"[bold cyan]Memory Synced[/bold cyan] (Tokens expanding)")

    def update_ui_with_error(self, error: str):
        chat = self.query_one("#chat_log", RichLog)
        chat.write(f"[bold red]Gateway Error:[/bold red] {error}")

if __name__ == "__main__":
    app = LauburuAgentIDE()
    app.run()
