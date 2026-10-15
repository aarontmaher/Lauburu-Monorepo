#!/usr/bin/env python3
"""
Sync Canonical Lauburu Combat Apparel (Option B) to Shopify via Admin API
- Short Sleeve Compression Rashguard
- No-Gi Pro Fight Shorts
- Combat Uniform Set Bundle
Uses authentic high-res renders from assets/products/bjj_apparel/
"""

import os
import base64
import requests
from pathlib import Path

SHOPIFY_STORE = "lauburu-grappling.myshopify.com"
ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")
ASSETS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/assets/products/bjj_apparel")

HEADERS = {
    "X-Shopify-Access-Token": ADMIN_TOKEN,
    "Content-Type": "application/json"
}
URL = f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json"

RANKS = ["White", "Blue", "Purple", "Brown", "Black"]
SIZES = ["XS", "S", "M", "L", "XL", "2XL"]

def encode_img(filename):
    p = ASSETS_DIR / filename
    if not p.exists():
        print(f"⚠️ Warning: Missing {filename}")
        return None
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_images_payload(filenames):
    images = []
    for fn in filenames:
        b64 = encode_img(fn)
        if b64:
            images.append({"attachment": b64, "filename": fn})
    return images

def create_product(title, product_type, body_html, price, sku_prefix, image_filenames):
    print(f"\n========================================================")
    print(f"🚀 Creating Product: {title} ({product_type})")
    print(f"========================================================")
    
    print(f"📸 Encoding {len(image_filenames)} canonical Option B artwork files...")
    images = build_images_payload(image_filenames)
    
    variants = []
    for rank in RANKS:
        for size in SIZES:
            variants.append({
                "option1": rank,
                "option2": size,
                "price": str(price),
                "sku": f"{sku_prefix}-{rank[:3].upper()}-{size}",
                "requires_shipping": True
            })
            
    payload = {
        "product": {
            "title": title,
            "product_type": product_type,
            "vendor": "Lauburu Athletics",
            "body_html": body_html,
            "status": "draft",
            "options": [
                {"name": "Belt Rank", "values": RANKS},
                {"name": "Size", "values": SIZES}
            ],
            "variants": variants,
            "images": images
        }
    }
    
    resp = requests.post(URL, headers=HEADERS, json=payload)
    if resp.status_code == 201:
        prod = resp.json()["product"]
        pid = prod["id"]
        print(f"✅ Created successfully!")
        print(f"🔗 Product ID: {pid}")
        print(f"   Variants: {len(prod.get('variants', []))}")
        print(f"   Images Attached: {len(prod.get('images', []))}")
        return pid
    else:
        print(f"❌ Failed: HTTP {resp.status_code}")
        print(resp.text)
        return None

def main():
    # 1. Canonical Rashguard
    rg_images = [
        "lauburu_master_5belt_color_sym_collection.png",
        "lauburu_rashguard_color_sym_black.png",
        "lauburu_rashguard_color_sym_white.png",
        "lauburu_rashguard_color_sym_blue.png",
        "lauburu_rashguard_color_sym_purple.png",
        "lauburu_rashguard_color_sym_brown.png",
        "lauburu_set_black_color_sym_showcase.png",
        "lauburu_set_white_color_sym_showcase.png",
        "lauburu_set_blue_color_sym_showcase.png",
        "lauburu_set_purple_color_sym_showcase.png",
        "lauburu_set_brown_color_sym_showcase.png"
    ]
    rg_html = """<h3>Lauburu Canonical Short Sleeve Compression Rashguard</h3>
<p><strong>Design: Option B (Belt-Rank Coloured Emblems Edition)</strong></p>
<p>Engineered to the official <em>Lauburu Optimal Delta Architecture</em> (Tech Pack TECHPACK-LBR-BJJ-2026-V1) based on digitized Absolute MMA competition pattern blocks.</p>
<ul>
  <li><strong>Custom Bicep Taper:</strong> -2.5 cm sleeve length eliminates elbow bunching and fabric snagging during wrist control and arm drags.</li>
  <li><strong>Drop-Tail Lumbar Coverage:</strong> +2.0 cm curved posterior hem ensures full coverage during deep guard inversion and berimbolos.</li>
  <li><strong>Anti-Ride Silicone Grip:</strong> Continuous 25mm medical-grade silicone micro-ribbed band heat-fused inside the bottom hem.</li>
  <li><strong>Low-Profile Collar:</strong> 1.2 cm crew neckband lined with soft 10mm black herringbone twill tape across the cervical spine.</li>
  <li><strong>Material:</strong> 250 GSM Heavyweight Competition Grade (82% Polyester, 18% Spandex), UPF 50+, 4-needle 6-thread flatlock stitching in 100% tone-on-tone stealth black thread.</li>
  <li><strong>Branding:</strong> IBJJF-compliant 80px sternum-centered dyed Lauburu rank emblem.</li>
</ul>"""
    rg_id = create_product(
        title="Lauburu Canonical Short Sleeve Compression Rashguard",
        product_type="Rashguard",
        body_html=rg_html,
        price="85.00",
        sku_prefix="LAU-RG-OPTB",
        image_filenames=rg_images
    )

    # 2. Canonical Fight Shorts
    shorts_images = [
        "lauburu_master_5belt_color_sym_collection.png",
        "lauburu_shorts_color_sym_black.png",
        "lauburu_shorts_color_sym_white.png",
        "lauburu_shorts_color_sym_blue.png",
        "lauburu_shorts_color_sym_purple.png",
        "lauburu_shorts_color_sym_brown.png",
        "lauburu_set_black_color_sym_showcase.png",
        "lauburu_set_white_color_sym_showcase.png",
        "lauburu_set_blue_color_sym_showcase.png",
        "lauburu_set_purple_color_sym_showcase.png",
        "lauburu_set_brown_color_sym_showcase.png"
    ]
    shorts_html = """<h3>Lauburu Canonical No-Gi Pro Fight Shorts</h3>
<p><strong>Design: Option B (Belt-Rank Coloured Emblems Edition)</strong></p>
<p>Engineered for high-intensity submission grappling and modern leg lock entanglements (saddle, 50/50, 411).</p>
<ul>
  <li><strong>High-Cut Athletic Inseam:</strong> 5.5" (14.5 cm) modern cut rests 2.5" above the patella for zero knee joint friction.</li>
  <li><strong>Scalloped Mobility Vents:</strong> 3.5" (9.0 cm) curved side slits reinforced with heavy-duty bar-tack stitching.</li>
  <li><strong>Hybrid Waistband:</strong> Craig Jones-inspired 50mm quad-stitched elastic waistband + flat recessed internal drawstring + non-abrasive 25mm micro-velcro tab (no bulky scratching front flap).</li>
  <li><strong>Anatomical Diamond Gusset:</strong> 250 GSM 4-way stretch poly-spandex crotch panel enabling full 180° leg splay.</li>
  <li><strong>Fabric:</strong> 165 GSM 4-way stretch micro-ripstop woven polyester with DWR water-repellent finish.</li>
  <li><strong>Branding:</strong> 90px dyed Lauburu rank emblem on lower right quad.</li>
</ul>"""
    shorts_id = create_product(
        title="Lauburu Canonical No-Gi Pro Fight Shorts",
        product_type="Fight Shorts",
        body_html=shorts_html,
        price="75.00",
        sku_prefix="LAU-SH-OPTB",
        image_filenames=shorts_images
    )

    # 3. Canonical Uniform Set Bundle
    bundle_images = [
        "lauburu_master_5belt_color_sym_collection.png",
        "lauburu_set_black_color_sym_showcase.png",
        "lauburu_set_white_color_sym_showcase.png",
        "lauburu_set_blue_color_sym_showcase.png",
        "lauburu_set_purple_color_sym_showcase.png",
        "lauburu_set_brown_color_sym_showcase.png"
    ]
    bundle_html = """<h3>Lauburu Canonical Combat Uniform Set (Bundle)</h3>
<p><strong>Includes: 1x Short Sleeve Compression Rashguard + 1x No-Gi Pro Fight Shorts</strong></p>
<p>The complete official Option B BJJ competition uniform. Unified stealth black (#141414) base fabric with dyed rank-specific Lauburu emblems.</p>
<p>Save $15 AUD when purchased as a complete uniform set.</p>"""
    bundle_id = create_product(
        title="Lauburu Canonical Combat Uniform Set",
        product_type="Combat Uniform Set",
        body_html=bundle_html,
        price="145.00",
        sku_prefix="LAU-SET-OPTB",
        image_filenames=bundle_images
    )

    print("\n🎉 All 3 Canonical Option B Products synced to Shopify Admin successfully!")

if __name__ == "__main__":
    main()
