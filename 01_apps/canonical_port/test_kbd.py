import asyncio
from textual.app import App
import sys
sys.path.insert(0, '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui')
from tui.canonical_tui import CanonicalPortApp
from textual.widgets import Button, Input
from components.keyboard.virtual_keyboard import VirtualKeyboard

async def run_test():
    app = CanonicalPortApp()
    async with app.run_test() as pilot:
        print("Screen mounted.")
        
        screen = app.get_screen("agi_terminal")
        kbd = screen.query_one(VirtualKeyboard)
        keys = screen.query("KeyboardKey")
        key_a = None
        for k in keys:
            if getattr(k, 'key_val', None) == 'a':
                key_a = k
                break
        
        if key_a:
            print("Clicking a")
            key_a.press()
            await pilot.pause()
            
            inp = screen.query_one("#repl-input", Input)
            print(f"Input value: '{inp.value}'")
        else:
            print("Key 'a' not found")
        
asyncio.run(run_test())
