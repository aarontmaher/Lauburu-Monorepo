import asyncio
from canonical_tui import CanonicalPortApp

async def run_test():
    app = CanonicalPortApp()
    async with app.run_test(size=(140, 40)) as pilot:
        # Wait for mount and initial render
        await pilot.pause(0.5)
        
        # Verify active screen
        assert app.screen is not None, "App screen not mounted!"
        
        # Test navigation across all screens in the 9-Screen Stability Hierarchy
async def run_test():
    app = CanonicalPortApp()
    async with app.run_test(size=(140, 40)) as pilot:
        # Wait for mount and initial render
        await pilot.pause(0.5)
        
        # Verify active screen
        assert app.screen is not None, "App screen not mounted!"
        
        # Test navigation across all screens in the 9-Screen Stability Hierarchy
        screens_to_test = [
            "agi_terminal",
            "network",
            "hardware",
            "biometrics",
            "ai_inference",
            "training",
            "governance",
            "tooling",
            "optimization",
            "all_tabs",
            "commercialization"
        ]
        
        for scr in screens_to_test:
            app.switch_screen(scr)
            await pilot.pause(0.2)
            assert app.current_screen_id == scr, f"Failed switching to screen: {scr}"
        
        # Test cycling screens
        app.cycle_screen(1, force=True)
        await pilot.pause(0.2)
        app.cycle_screen(-1, force=True)
        await pilot.pause(0.2)
        
        print("TUI Audit Passed: Application boots and screens navigate without crashing.")

if __name__ == "__main__":
    asyncio.run(run_test())
