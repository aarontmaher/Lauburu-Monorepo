import asyncio
import os
import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container
from rich.text import Text

class RustBridgeApp(App):
    """A Textual app to demonstrate piping Ratatui output."""
    
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="bridge-container"):
            # We use a Static widget to render the exact grid produced by Rust
            yield Static("Waiting for Rust TUI...", id="rust-tui")
        yield Footer()

    def on_mount(self) -> None:
        self.tui_static = self.query_one("#rust-tui", Static)
        
        # Determine paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        rust_binary = os.path.join(base_dir, "rust_bridge", "target", "debug", "rust_bridge")
        
        if not os.path.exists(rust_binary):
            self.tui_static.update(f"Binary not found at {rust_binary}. Please compile first.")
            return

        # Start the Rust process
        asyncio.create_task(self.run_rust_bridge(rust_binary))

    async def run_rust_bridge(self, binary_path: str) -> None:
        process = await asyncio.create_subprocess_exec(
            binary_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        
        frame_lines = []
        
        while True:
            if process.stdout is None:
                break
            line = await process.stdout.readline()
            if not line:
                break
                
            decoded = line.decode('utf-8', errors='replace').rstrip("\r\n")
            
            if decoded == "---FRAME---":
                # We finished collecting a frame, render it
                if frame_lines:
                    # Combine all lines with newlines, parse ANSI, and update the Static
                    joined = "\n".join(frame_lines)
                    self.tui_static.update(Text.from_ansi(joined))
                    frame_lines = []
            else:
                frame_lines.append(decoded)
        
        await process.wait()
        self.tui_static.update("Rust process exited.")
        self.exit()

if __name__ == "__main__":
    app = RustBridgeApp()
    app.run()
