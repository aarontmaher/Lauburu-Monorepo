#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

# Load the listing
listing_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/iphone_16_pro_listing.md")
if not listing_path.exists():
    listing_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/iphone_16_pro_max_listing.md")
listing_content = listing_path.read_text()

# Query Local AI (Qwen 3.8 Max - Port 8082 - Sovereign Orchestrator)
prompt = f"""
You are an expert direct-response E-Commerce copywriter. Generate a high-converting Facebook Marketplace / Gumtree ad based on the following raw listing data.
The price has just been DROPPED to $990 AUD (under $1,000!) for an immediate quick sale today.
Make it engaging, trustworthy, and completely transparent about the flawless front glass and the isolated OLED bezel flaw.
Include:
1. A catchy high-urgency hook mentioning the price drop under $1K.
2. The main selling points (512GB, Black Titanium, unlocked, 100% working touch, Face ID, ProMotion).
3. A clear CTA (Call to Action) for local cash pickup in Altona North (3025) or Express insured shipping on eBay.
4. Suggested tags for SEO.

Raw Listing:
{listing_content}
"""

payload = {
    "model": "qwen_38_max_abliterated",
    "messages": [
        {"role": "system", "content": "You are a direct-response copywriter for consumer electronics."},
        {"role": "user", "content": prompt}
    ],
    "max_tokens": 800,
    "temperature": 0.3
}

endpoints = [
    "http://127.0.0.1:8082/v1/chat/completions",
    "http://127.0.0.1:8083/v1/chat/completions"
]

ad_copy = None
for ep in endpoints:
    try:
        req = urllib.request.Request(
            ep,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ad_copy = data["choices"][0]["message"]["content"]
            break
    except Exception as e:
        continue

if not ad_copy:
    ad_copy = f"""🔥 PRICE DROP: Apple iPhone 16 Pro - 512GB - Black Titanium (Unlocked) 🔥

⚡ **Special Price:** $990 AUD (Priced to sell today — Retail is $2,149 for the 512GB model!)

Selling my authentic Apple iPhone 16 Pro with massive 512GB storage. Purchased brand new outright from Apple Store.

**Condition & Features:**
• **Front Glass:** 100% pristine and scratch-free! (Older photos showed hairline marks on a glass protector, which is now removed).
• **Display:** Small black crescent dead pixel spot on the far right bezel border. 100% fully functional touch across the entire screen.
• **Performance:** Face ID, 120Hz ProMotion, Dynamic Island, and all three cameras (48MP) work perfectly.
• **iCloud:** 100% factory wiped and clean. Ready for your SIM/eSIM.

**Pickup & Payment:**
• Cash or instant PayID/OSKO on pickup in Altona North (Altona Gate Shopping Centre).
• Trades: Open to PS5 Slim + $450-$500 cash.
• Interstate: Available on eBay Buy It Now ($1,090 AUD with Express insured postage).

Message me on Gumtree to arrange pickup today!"""

output_path_pro = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/iphone_16_pro_ad_campaign.md")
output_path_max = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/iphone_16_pro_max_ad_campaign.md")
header = "# 📱 iPhone 16 Pro 512GB — Master Ad Campaign (Price Dropped to $990 AUD)\n\n"
output_path_pro.write_text(f"{header}{ad_copy}")
output_path_max.write_text(f"{header}{ad_copy}")
print(f"Ad campaigns successfully updated to $990 AUD at {output_path_pro.name} and {output_path_max.name}")
