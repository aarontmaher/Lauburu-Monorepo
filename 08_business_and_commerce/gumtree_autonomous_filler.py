#!/usr/bin/env python3
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import traceback
import subprocess
import requests

def wait_for_unblock():
    print("⏳ Checking if Gumtree IP block is lifted...")
    while True:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            res = requests.get("https://www.gumtree.com.au/post.html", headers=headers, timeout=10)
            if "Access Denied" not in res.text and res.status_code == 200:
                print("✅ Gumtree IP block lifted!")
                return True
        except:
            pass
        time.sleep(60)

def run_filler():
    print("🤖 Gumtree Autonomous Filler Daemon Started...")
    
    # Wait for unblock first
    wait_for_unblock()
    
    ad_content_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/iphone_16_pro_max_listing.md")
    ad_content = ad_content_path.read_text()
    
    title = "Apple iPhone 16 Pro Max - 512GB - Black (Fully Functional)"
    price = "1150"
    
    parts = ad_content.split("**Description:**")
    body = parts[1].strip() if len(parts) > 1 else ad_content
    
    images = [
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_max_front.jpg",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_max_screen.jpg"
    ]

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            
            page = None
            for p_item in context.pages:
                if "gumtree" in p_item.url.lower():
                    page = p_item
                    break
            
            if not page:
                page = context.new_page()
                
            page.goto("https://www.gumtree.com.au/post.html")
            print("✅ Navigated to Gumtree Post Ad page.")
            
            filled = False
            while not filled:
                if "post.html" in page.url.lower():
                    print(f"🚀 Detected Gumtree Listing Page! Taking over...")
                    
                    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
                    time.sleep(2)
                    
                    try:
                        file_input = page.locator('input[type="file"]').first
                        file_input.set_input_files(images)
                        print("📸 Uploaded Photos.")
                    except:
                        pass
                        
                    try:
                        page.get_by_placeholder("What are you selling?").fill(title)
                        print("📝 Typed title.")
                    except:
                        pass
                        
                    try:
                        page.locator('input[name="price"]').fill(price)
                    except:
                        pass
                        
                    try:
                        page.locator('textarea[name="description"]').fill(body)
                    except:
                        pass
                        
                    print("✅ Form filled! AI is detaching. Please review and post.")
                    filled = True
                
                time.sleep(10)
                
            browser.disconnect()
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    run_filler()
