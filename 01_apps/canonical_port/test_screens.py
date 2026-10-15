import asyncio
from textual.app import App
import sys
import traceback
sys.path.insert(0, '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui')
from tui.canonical_tui import CanonicalPortApp

async def run_test():
    app = CanonicalPortApp()
    async with app.run_test() as pilot:
        print("Screen mounted.")
        for screen_name in app.SCREENS:
            try:
                app.switch_screen(screen_name)
                await pilot.pause()
                print(f"Switched to {screen_name} successfully.")
            except Exception as e:
                print(f"Failed on {screen_name}: {e}")
                traceback.print_exc()
        
asyncio.run(run_test())
