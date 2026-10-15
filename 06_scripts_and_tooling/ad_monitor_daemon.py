import asyncio
import re
import datetime
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACT_PATH = "/Users/aaron/.gemini/antigravity/brain/cdca10c9-e3ec-4303-aabd-7860383dd9a8/ad_metrics.md"

async def extract_ebay_metrics(page):
    try:
        text = await page.evaluate('''() => {
            const titleEl = Array.from(document.querySelectorAll('a')).find(a => a.innerText.includes('iPhone 16 Pro'));
            if (titleEl) {
                let parent = titleEl;
                for(let i=0; i<5; i++) { if (parent.parentElement) parent = parent.parentElement; }
                return parent.innerText;
            }
            return "";
        }''')
        
        views = "0"
        watchers = "0"
        
        # Looking for "X\\nviews" and "Y\\nwatchers"
        views_match = re.search(r'(\\d+)\\nviews', text, re.IGNORECASE)
        watchers_match = re.search(r'(\\d+)\\nwatchers', text, re.IGNORECASE)
        
        if views_match: views = views_match.group(1)
        if watchers_match: watchers = watchers_match.group(1)
            
        return {"views": views, "watchers": watchers, "status": "Active" if text else "Not Found"}
    except Exception as e:
        return {"error": str(e)}

async def extract_fb_metrics(page):
    try:
        text = await page.evaluate('''() => {
            const elements = Array.from(document.querySelectorAll('span[dir="auto"]')).map(s => s.innerText);
            const targetIdx = elements.findIndex(e => e.includes('iPhone 16 Pro Max'));
            if (targetIdx !== -1) {
                return elements.slice(targetIdx, targetIdx + 10).join(' | ');
            }
            return "";
        }''')
        
        clicks = "0"
        clicks_match = re.search(r'(\\d+)\\s+clicks on listing', text, re.IGNORECASE)
        if clicks_match: clicks = clicks_match.group(1)
            
        return {"clicks": clicks, "status": "Active" if text else "Not Found"}
    except Exception as e:
        return {"error": str(e)}

async def main():
    print("Starting Ad Monitor Daemon...")
    while True:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                
                ebay_metrics = {"status": "Page not open"}
                fb_metrics = {"status": "Page not open"}
                
                for page in context.pages:
                    url = page.url
                    if "ebay.com.au/mys/active" in url:
                        await page.reload()
                        await page.wait_for_timeout(3000)
                        ebay_metrics = await extract_ebay_metrics(page)
                    elif "facebook.com/marketplace/you/selling" in url:
                        await page.reload()
                        await page.wait_for_timeout(3000)
                        fb_metrics = await extract_fb_metrics(page)
                
                # Write to artifact
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                md_content = f"""# 📊 Live Ad Campaign Metrics
*Last Updated: {now}*

> [!NOTE]
> This artifact is updated automatically by the continuous background daemon. Do not edit manually.

### 🔵 Facebook Marketplace (iPhone 16 Pro Max)
* **Status:** {fb_metrics.get("status", "Unknown")}
* **Listing Clicks:** {fb_metrics.get("clicks", "N/A")}

### 🟡 eBay Australia (iPhone 16 Pro)
* **Status:** {ebay_metrics.get("status", "Unknown")}
* **Views:** {ebay_metrics.get("views", "N/A")}
* **Watchers:** {ebay_metrics.get("watchers", "N/A")}
"""
                with open(ARTIFACT_PATH, "w") as f:
                    f.write(md_content)
                
                print(f"[{now}] Metrics updated.")
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            
        await asyncio.sleep(300) # Sleep for 5 minutes

if __name__ == "__main__":
    asyncio.run(main())
