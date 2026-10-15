import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Label
from textual.screen import Screen

class BiometricsDashboard(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Static(f"--- Scaffolded BiometricsDashboard ---", classes="screen-title"),
                Static("Content generated from DESIGN.MD specifications.", classes="screen-content")
            )
        )
        yield Footer()

class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Static(f"--- Scaffolded SettingsScreen ---", classes="screen-title"),
                Static("Content generated from DESIGN.MD specifications.", classes="screen-content")
            )
        )
        yield Footer()

class MovesenseBiometricsDashboardApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    .screen-title {
        text-align: center;
        text-style: bold;
        color: $accent;
    }
    .screen-content {
        text-align: center;
        margin-top: 2;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def on_mount(self) -> None:
        self.push_screen(BiometricsDashboard())

if __name__ == "__main__":
    app = MovesenseBiometricsDashboardApp()
    app.run()
