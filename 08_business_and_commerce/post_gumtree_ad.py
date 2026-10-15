#!/usr/bin/env python3
import subprocess
from pathlib import Path

def post_gumtree():
    ad_content_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/gumtree_ad_campaign.md")
    ad_content = ad_content_path.read_text()
    
    title = "Apple iPhone 16 Pro - 512GB - Black Titanium (Massive Discount!)"
    price = "1150"
    
    # Extract description
    parts = ad_content.split("## Ad Description:")
    body = parts[1].strip() if len(parts) > 1 else ad_content
    
    images = [
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_512gb_front.jpg",
        "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets/iphone_16_pro_512gb_screen.jpg"
    ]
    
    try:
        process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(body.encode('utf-8'))
        print("📋 Gumtree description copied to macOS clipboard!")
    except Exception as e:
        print(f"⚠️ Clipboard error: {e}")
        
    print(f"📱 Title: {title}")
    print(f"💰 Price: ${price}")
    print(f"📸 Images ready:")
    for img in images:
        print(f"  - {img}")
        
    print("🚀 Opening Gumtree Post-an-Ad flow in Google Chrome...")
    subprocess.run(["open", "-a", "Google Chrome", "https://www.gumtree.com.au/web/syi"])
    print("✅ Opened https://www.gumtree.com.au/web/syi in Chrome.")

if __name__ == "__main__":
    post_gumtree()
