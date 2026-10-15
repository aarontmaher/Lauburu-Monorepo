#!/usr/bin/env python3
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def post_ad():
    ad_content_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/facebook_ad_campaign.md")
    ad_content = ad_content_path.read_text()
    
    title = "Apple iPhone 16 Pro - 512GB - Black Titanium"
    price = "1150"
    parts = ad_content.split("## 📝 Marketplace Description:")
    body = parts[1].strip() if len(parts) > 1 else ad_content
    
    images = [
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_512gb_front.jpg",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_512gb_screen.jpg"
    ]
    
    # Also copy body to clipboard for 1-click paste
    import subprocess
    try:
        process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(body.encode('utf-8'))
        print("📋 Facebook Marketplace ad description copied to macOS clipboard!")
    except Exception as e:
        print(f"⚠️ Clipboard error: {e}")

    print("🚀 Opening Facebook Marketplace Create flow in Google Chrome...")
    subprocess.run(["open", "-a", "Google Chrome", "https://www.facebook.com/marketplace/create/item"])
    print("✅ Opened Facebook Marketplace in Chrome.")
    print("💡 The listing description is on your clipboard. Images:")
    for img in images:
        print(f"  📸 {img}")

if __name__ == "__main__":
    post_ad()
