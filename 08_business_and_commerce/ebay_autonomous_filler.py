#!/usr/bin/env python3
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import traceback
import subprocess

def run_filler():
    print("🤖 eBay Autonomous Filler Daemon Started...")
    ebay_md = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/ebay_ad_campaign.md")
    content = ebay_md.read_text()
    
    parts = content.split("**Description (HTML/Rich Text):**")
    desc_html = parts[1].strip() if len(parts) > 1 else content
    
    try:
        process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(desc_html.encode('utf-8'))
    except:
        pass

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            
            filled = False
            while not filled:
                page = None
                for p_item in context.pages:
                    if "ebay" in p_item.url.lower() and "sl/list" in p_item.url.lower():
                        page = p_item
                        break
                
                if page:
                    print(f"🚀 Detected eBay Listing Page! Taking over...")
                    
                    # Bring Chrome to front
                    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
                    time.sleep(2)
                    
                    # Upload Photos
                    try:
                        file_inputs = page.locator('input[type="file"]')
                        if file_inputs.count() > 0:
                            file_inputs.first.set_input_files([
                                "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_max_front.jpg",
                                "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_max_screen.jpg"
                            ])
                            print("📸 Uploaded Photos.")
                    except Exception as e:
                        print("⚠️ Photo upload issue:", e)
                        
                    # Price
                    try:
                        price_input = page.locator('input[name="binPrice"]')
                        if price_input.count() > 0:
                            price_input.fill("1250")
                            print("💰 Set Buy It Now Price to 1250.")
                    except:
                        pass
                        
                    # Description (using AppleScript to paste since rich text editors in Playwright are tricky)
                    print("📝 Pasting Description...")
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'])
                    
                    print("✅ Form filled! AI is detaching. Please review and click 'List it'.")
                    filled = True
                
                time.sleep(5)
                
            browser.disconnect()
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    run_filler()
