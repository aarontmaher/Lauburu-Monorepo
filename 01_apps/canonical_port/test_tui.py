import asyncio
from textual.app import App
import sys
sys.path.insert(0, '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui')
from tui.canonical_tui import CanonicalPortApp

async def run_test():
    app = CanonicalPortApp()
    async with app.run_test() as pilot:
        print(f"Active screen: {app.screen}")
        print("Screen mounted.")
        
asyncio.run(run_test())
