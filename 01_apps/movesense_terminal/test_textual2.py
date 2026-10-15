import asyncio
from app import MovesenseTerminal

async def run_test():
    app = MovesenseTerminal()
    async with app.run_test() as pilot:
        print("App started.")
        await pilot.pause()
        print("App paused.")

if __name__ == "__main__":
    asyncio.run(run_test())
