from textual.app import App, ComposeResult
from textual.widgets import RichLog, Static
from rich.text import Text
import asyncio

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield RichLog(id="log", markup=False, highlight=False)

    async def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        # Test basic ANSI color
        ansi_str = "Hello \x1b[31mRed\x1b[0m \x1b[42m\x1b[30mGreenBg\x1b[0m"
        log.write(Text.from_ansi(ansi_str))
        
        # Another row
        log.write(Text.from_ansi("\x1b[34mBlue \x1b[1mBold\x1b[0m"))

if __name__ == "__main__":
    app = TestApp()
    app.run()
