import asyncio
from textual.app import App
from tui.views.agi_coding_terminal_view import AgiCodingTerminalView

class TestApp(App):
    def compose(self):
        yield AgiCodingTerminalView()
    
    async def on_mount(self):
        # Allow it to mount
        self.set_timer(0.5, self.simulate_actions)

    async def simulate_actions(self):
        try:
            view = self.query_one(AgiCodingTerminalView)
            # Click feature buttons
            view.query_one("#btn-feat-boost").press()
            view.query_one("#btn-feat-deep-research").press()
            
            # Click toggle keyboard
            view.query_one("#btn-toggle-keyboard").press()
            
            # Press voice code
            view.query_one("#btn-voice-code").press()
            
            print("Actions simulated successfully")
        except Exception as e:
            print("Error simulating:", e)
        finally:
            self.exit()

if __name__ == "__main__":
    app = TestApp()
    app.run(headless=True)
