import asyncio
from textual.app import App, ComposeResult
from tui.components.keyboard.virtual_keyboard import VirtualKeyboard

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield VirtualKeyboard()
    def on_mount(self) -> None:
        self.query_one(VirtualKeyboard).toggle_visibility()
        # Exit after a short delay to allow layout
        self.set_timer(0.5, self.exit)

if __name__ == "__main__":
    app = TestApp()
    try:
        app.run(headless=True)
        print("Run successful")
    except Exception as e:
        print("Run failed:", e)
