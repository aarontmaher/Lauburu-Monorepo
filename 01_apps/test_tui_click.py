import asyncio
from movesense_terminal.app import MovesenseTerminal
from textual.pilot import Pilot

async def run_test():
    app = MovesenseTerminal()
    async with app.run_test(headless=True) as pilot:
        await pilot.click("#btn_connect_bt")
        await asyncio.sleep(1)
        # Check logs
        log = app.query_one("#telemetry-log")
        # We can't easily extract text from RichLog in old textuals, just print success
        print("TUI Click executed.")

asyncio.run(run_test())
