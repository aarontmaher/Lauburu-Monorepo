import asyncio
from src.bluetooth_terminal_app import BluetoothTerminalApp

async def run_test():
    app = BluetoothTerminalApp()
    async with app.run_test() as pilot:
        print("App started.")
        await pilot.pause()
        print("App paused.")

if __name__ == "__main__":
    asyncio.run(run_test())
