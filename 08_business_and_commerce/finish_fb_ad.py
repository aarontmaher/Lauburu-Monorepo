import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = None
        for p in context.pages:
            if "marketplace/create/item" in p.url:
                page = p
                break
        
        if not page:
            print("Could not find the Facebook Marketplace page.")
            return

        print(f"Connected to {page.url}")
        await page.bring_to_front()

        # Fill Title
        await page.get_by_label("Title", exact=True).fill("Apple iPhone 16 Pro Max - 512GB - Black (Fully Functional)")
        print("Filled title")

        # Fill Price
        await page.get_by_label("Price").fill("1150")
        print("Filled price")

        # Fill Category
        category_dropdown = page.get_by_label("Category")
        if category_dropdown:
            await category_dropdown.click()
            await page.get_by_text("Mobile Phones", exact=False).nth(0).click()
            print("Selected category")

        # Fill Description
        description_text = """Selling my Apple iPhone 16 Pro Max with a massive 512GB of storage. I purchased this brand new directly from the Apple Store last year. 

Condition:
* Front Glass & Display: The actual front glass is completely flawless (the previous cracks were just a screen protector, which has been removed). However, there is a small black "burn" spot (dead pixels) on the right edge of the OLED display panel. The rest of the screen works perfectly, turns on fine, and the touch screen is 100% fully responsive.
* Back Glass & Cameras: The back of the phone and the rear camera lenses are in pristine condition with no visible damage. 
* Software: The phone has been completely factory wiped. iCloud and Activation Lock have been 100% removed. It boots straight to the "Hello" screen and is ready for you to insert your SIM and set up as a brand-new device. 

Details:
* Model: iPhone 16 Pro Max
* Storage: 512GB
* Serial Number: G0WR66YPCQ
* Network: Unlocked (purchased outright from Apple)

Trades:
I am open to trades! Let me know what you have. 

This is a massive discount on a 512GB Pro Max. Perfect for someone who wants flagship specs without paying the $1,800+ retail price.

Phone only (no box or charger included). 

Message me if you are interested or have any questions! Cash or trade on pickup only."""

        # Wait for description box
        try:
            await page.get_by_label("Description").fill(description_text)
            print("Filled description")
        except Exception as e:
            print(f"Description fill failed: {e}")
            
        print("Done filling out the basic details!")
        
asyncio.run(main())
