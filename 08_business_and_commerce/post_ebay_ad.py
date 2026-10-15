#!/usr/bin/env python3
import subprocess
from pathlib import Path

def post_ebay():
    print("🚀 Launching eBay Ad Preparation for iPhone 16 Pro 512GB...")
    
    ebay_md = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/ebay_ad_campaign.md")
    content = ebay_md.read_text()
    
    parts = content.split("## Description (HTML/Rich Text):")
    desc_html = parts[1].strip() if len(parts) > 1 else content
    
    try:
        process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(desc_html.encode('utf-8'))
        print("📋 eBay HTML description successfully copied to macOS clipboard!")
    except Exception as e:
        print(f"⚠️ Could not copy to clipboard: {e}")
        
    title = "Apple iPhone 16 Pro 512GB - Black Titanium - Unlocked - *READ DESC*"
    price = "1250"
    images = [
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_512gb_front.jpg",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_512gb_screen.jpg"
    ]
    
    print(f"📱 Title: {title}")
    print(f"💰 Buy It Now Price: ${price} AUD")
    print("📸 Photos:")
    for img in images:
        print(f"  - {img}")
        
    print("\n🌐 Opening eBay Listing Flow in Google Chrome...")
    subprocess.run(["open", "-a", "Google Chrome", "https://www.ebay.com.au/sl/prelist/suggest?sr=shStart"])
    print("✅ Opened eBay Listing Flow in Chrome.")

if __name__ == "__main__":
    post_ebay()
