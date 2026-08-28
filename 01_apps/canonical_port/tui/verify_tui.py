import asyncio
from canonical_tui import CanonicalPortApp

async def run_test():
    app = CanonicalPortApp()
    async with app.run_test(size=(140, 40)) as pilot:
        # Wait for mount and initial render
        await pilot.pause(1.0)
        
        # Verify active screen
        assert app.screen is not None, "App screen not mounted!"
        
        # Try switching screens to ensure no crash
        app.switch_screen("network")
        await pilot.pause(0.5)
        app.switch_screen("agi_terminal")
        await pilot.pause(0.5)
        app.switch_screen("training")
        await pilot.pause(0.5)
        
        print("TUI Audit Passed: Application boots and screens navigate without crashing.")

if __name__ == "__main__":
    asyncio.run(run_test())
