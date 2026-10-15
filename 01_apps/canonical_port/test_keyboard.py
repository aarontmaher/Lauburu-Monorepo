from textual.app import App, ComposeResult
from tui.components.keyboard.virtual_keyboard import VirtualKeyboard

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield VirtualKeyboard()
    def on_mount(self) -> None:
        self.query_one(VirtualKeyboard).toggle_visibility()

if __name__ == "__main__":
    app = TestApp()
    app.run(headless=True)
